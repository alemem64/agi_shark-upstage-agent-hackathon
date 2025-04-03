import streamlit as st
import asyncio
import os

from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent, Runner, ModelSettings, function_tool, set_default_openai_key, RunConfig, WebSearchTool
from tools.document_parser.document_parser import DocumentParser

def get_model_name(model_options):
    if model_options == "claude 3.7 sonnet":
        return "claude-3-7-sonnet-latest"
    elif model_options == "claude 3 haiku":
        return "claude-3-haiku-20240307"
    elif model_options == "gpt 4o mini":
        return "gpt-4o-mini"

# Agent 객체 생성 함수
def create_agent(model_options):
    """
    Agent 객체를 생성합니다.
    """
    # 세션 상태에서 API 키 설정
    if 'openai_key' in st.session_state and st.session_state.openai_key:
        set_default_openai_key(st.session_state.openai_key)
    else:
        st.error("OpenAI API 키가 설정되지 않았습니다. API 설정 페이지에서 키를 입력해주세요.")
        return None
    
    # 투자 성향 정보 가져오기
    user_requirement = st.session_state.get('user_requirement', '')
    risk_style = st.session_state.get('risk_style', '중립적')
    trading_period = st.session_state.get('trading_period', '스윙')

    pdf_files = [f for f in os.listdir("tools/web2pdf/always_see_doc_storage") if f.endswith('.pdf')]

    # 이전 메시지 가져오기
    previous_messages = st.session_state.get('messages', [])
    context = ""
    
    # 최근 대화 기록을 context에 추가 (최대 5개 메시지)
    if len(previous_messages) > 1:  # 첫 메시지는 AI 인사말이므로 건너뜀
        context = "이전 대화 내용:\n"
        for i, msg in enumerate(previous_messages[-6:-1]):  # 최근 5개 메시지만
            if msg["role"] == "user":
                context += f"사용자: {msg['content']}\n"
            elif msg["role"] == "assistant":
                context += f"AI: {msg['content']}\n"
        context += "\n"

    # Agent 생성
    agent = Agent(
        name="Crypto Trading Assistant",
        instructions=f"""
        암호화폐 거래에 관한 질문에 답변하는 AI 어시스턴트입니다.
        사용자의 투자 성향과 요구사항을 고려하여 도움을 제공합니다.
        
        {context}
        
        사용자 맞춤 지시: {user_requirement}
        위험 성향: {risk_style}
        거래 기간: {trading_period}

        참조 문서: "tools/web2pdf/always_see_doc_storage/{pdf_files}.pdf"
        """,
        model=get_model_name(model_options),
        tools=[WebSearchTool(search_context_size="high")],
    )
    
    return agent

async def stream_openai_response(prompt, model_options, conversation_id=None):
    """
    OpenAI Agent를 사용하여 응답을 스트리밍합니다.
    conversation_id를 사용하여 대화 기록을 유지합니다.
    """
    print(f"스트리밍 시작 - 모델: {model_options}, 프롬프트 길이: {len(prompt)}")
    
    # Agent 생성
    agent = create_agent(model_options)
    if not agent:
        print("API 키 없음 - 응답 생성 중단")
        yield "API 키 설정이 필요합니다."
        return
    
    try:
        # 대화 기록 유지를 위한 RunConfig 생성
        run_config = None
        if conversation_id:
            run_config = RunConfig(
                workflow_name="Crypto Trading Assistant",
                group_id=conversation_id,  # 대화 그룹 ID 설정
            )
            print(f"RunConfig 생성 - 대화ID: {conversation_id}")
        
        # 대화 기록이 있는 경우 full_prompt에 포함
        if len(st.session_state.get('messages', [])) > 1 and prompt:
            full_prompt = f"{prompt}"
        else:
            full_prompt = prompt
        
        print(f"Runner.run_streamed 호출 전")
        
        # 적절한 인자로 run_streamed 호출
        if run_config:
            result = Runner.run_streamed(
                agent, 
                input=full_prompt,
                run_config=run_config
            )
        else:
            result = Runner.run_streamed(
                agent, 
                input=full_prompt
            )
        
        print(f"스트리밍 시작")
        chunk_count = 0
        
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                chunk_count += 1
                if chunk_count % 10 == 0:  # 10개마다 로그 출력
                    print(f"청크 {chunk_count}개 수신 중")
                yield event.data.delta
        
        print(f"스트리밍 완료 - 총 {chunk_count}개 청크")
                
    except Exception as e:
        error_msg = f"응답 생성 중 오류 발생: {str(e)}"
        print(f"ERROR: {error_msg}")
        st.error(error_msg)
        yield error_msg

def stream_response(prompt, model_options):
    """
    비동기 스트리밍 함수를 Streamlit에서 사용할 수 있는 형태로 변환
    """
    async def process_stream():
        response_chunks = []
        async for chunk in stream_openai_response(prompt, model_options):
            response_chunks.append(chunk)
            yield chunk
    
    return process_stream()