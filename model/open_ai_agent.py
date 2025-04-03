import os
import openai
import streamlit as st
from langchain.agents import AgentExecutor, create_react_agent
from langchain.schema import SystemMessage
from langchain_openai import ChatOpenAI
from langchain_community.callbacks import get_openai_callback
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
import asyncio

# 분리된 모듈 임포트
from model.logging_utils import log_info, log_error, setup_logging
from model.upbit_api import get_upbit_instance, get_wallet_status, get_portfolio_coins
from model.agent_tools import create_tools, get_tool_descriptions
from model.trading_tools import (
    get_available_coins_func,
    get_coin_price_info_func,
    buy_coin_func,
    sell_coin_func,
    check_order_status_func
)

# OpenAI 스트리밍 응답 생성 함수
async def stream_openai_response(prompt: str, model_options: Dict[str, Any] = None, conversation_id: str = None) -> AsyncGenerator[str, None]:
    """
    OpenAI API를 사용하여 스트리밍 방식으로 응답을 생성합니다.
    
    Args:
        prompt: 사용자 입력 텍스트
        model_options: 모델 설정 옵션
        conversation_id: 대화 ID
        
    Yields:
        응답 텍스트의 각 조각
    """
    try:
        # API 키 확인
        api_key = st.session_state.get('openai_api_key', '')
        if not api_key:
            yield "OpenAI API 키가 설정되지 않았습니다. API 설정 탭에서 설정해주세요."
            return
            
        # 모델 선택
        model_name = get_model_name(model_options)
        log_info(f"스트리밍 응답 생성 시작", {"model": model_name, "conversation_id": conversation_id})
        
        # 시스템 메시지 설정
        system_message = """
        당신은 '샤크5'라는 암호화폐 트레이딩 AI 도우미입니다.
        사용자가 암호화폐 투자와 관련된 질문을 할 때 최대한 정확하고 유용한 정보를 제공하세요.
        
        지켜야 할 규칙:
        1. 사용자가 매도를 요청하면 반드시 현재 포트폴리오의 코인을 확인하고 해당 코인이 보유 중인지 확인하세요.
        2. 거래 가능한 코인 목록에 있더라도, 사용자가 매도하려는 코인은 실제 보유 중인지 확인하세요.
        3. 투자 추천이나 의견을 요청받으면 장단점과 위험성을 함께 설명하세요.
        4. 매수/매도 주문 전에 코인의 현재 가격과 시장 상황을 확인하고 사용자에게 정보를 제공하세요.
        5. 주문이 접수되면 거래 결과를 간결하게 전달하세요. '대기중' 대신 "주문이 접수되었습니다. 거래내역 탭에서 확인 가능합니다."라고 안내하세요.
        6. 사용자의 위험 성향에 맞는 투자 조언을 제공하세요.
        7. 응답은 항상 간결하고 명확하게 작성하세요.
        """
        
        # 채팅 기록 가져오기
        messages = [{"role": "system", "content": system_message}]
        
        # 세션 상태에서 이전 대화 내용 가져오기
        chat_history = st.session_state.get('messages', [])
        for msg in chat_history[-10:]:  # 최근 10개의 메시지만 사용
            if msg["role"] in ["user", "assistant"]:
                messages.append(msg)
                
        # 새 메시지 추가
        messages.append({"role": "user", "content": prompt})
        
        # OpenAI 클라이언트 생성
        client = create_openai_client(api_key)
        
        # 스트리밍 응답 생성
        response = await client.chat.completions.acreate(
            model=model_name,
            messages=messages,
            temperature=0.7,
            stream=True,
            max_tokens=2000
        )
        
        # 응답 스트림 처리
        collected_chunks = []
        collected_content = ""
        
        async for chunk in response:
            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                choice = chunk.choices[0]
                if hasattr(choice, 'delta') and hasattr(choice.delta, 'content'):
                    content = choice.delta.content
                    if content:
                        collected_chunks.append(content)
                        collected_content += content
                        yield content
        
        # 로깅
        log_info(f"스트리밍 응답 생성 완료", {
            "total_chunks": len(collected_chunks),
            "total_length": len(collected_content)
        })
        
    except Exception as e:
        error_msg = f"스트리밍 응답 생성 중 오류: {str(e)}"
        log_error(e, error_msg)
        yield error_msg

# OpenAI API 클라이언트 생성
def create_openai_client(api_key=None):
    """
    OpenAI API 클라이언트를 생성합니다.
    """
    if not api_key:
        api_key = st.session_state.get('openai_api_key', '')
    
    client = openai.OpenAI(api_key=api_key)
    return client

# 에이전트 생성
def create_agent(api_key=None, model=None, verbose=False, max_iterations=10):
    """
    LangChain 에이전트를 생성합니다.
    """
    if not api_key:
        api_key = st.session_state.get('openai_api_key', '')
    
    if not model:
        model = get_model_name()
    
    try:
        # ChatOpenAI 인스턴스 생성
        llm = ChatOpenAI(
            model=model,
            temperature=0.2,
            openai_api_key=api_key
        )
        
        # 시스템 메시지 (에이전트 역할과 지침)
        system_message = f"""
        당신은 '샤크5'라는 암호화폐 트레이딩 AI 도우미입니다.
        사용자가 암호화폐 투자와 관련된 질문을 할 때 최대한 정확하고 유용한 정보를 제공하세요.
        
        지켜야 할 규칙:
        1. 사용자가 매도를 요청하면 반드시 현재 포트폴리오의 코인을 확인하고 해당 코인이 보유 중인지 확인하세요.
           get_available_coins 도구에 'action_type': 'sell' 파라미터를 전달하여 보유 중인 코인 목록만 확인할 수 있습니다.
        2. 거래 가능한 코인 목록에 있더라도, 사용자가 매도하려는 코인은 실제 보유 중인지 확인하세요.
        3. 투자 추천이나 의견을 요청받으면 장단점과 위험성을 함께 설명하세요.
        4. 매수/매도 주문 전에 코인의 현재 가격과 시장 상황을 확인하고 사용자에게 정보를 제공하세요.
        5. 주문이 접수되면 거래 결과를 간결하게 전달하세요. '대기중' 대신 "주문이 접수되었습니다. 거래내역 탭에서 확인 가능합니다."라고 안내하세요.
        6. 사용자의 위험 성향에 맞는 투자 조언을 제공하세요.
        7. 응답은 항상 간결하고 명확하게 작성하세요.
        
        위의 규칙을 반드시 지키면서, 사용자의 투자 결정에 도움이 되는 정보를 제공하세요.
        """
        
        # 도구 목록 생성
        tools = create_tools()
        
        # ReAct 에이전트 생성
        agent = create_react_agent(
            llm=llm,
            tools=tools,
            system_message=SystemMessage(content=system_message)
        )
        
        # 에이전트 실행기 생성
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=verbose,
            max_iterations=max_iterations,
            handle_parsing_errors=True
        )
        
        log_info("에이전트 생성 성공", {
            "model": model,
            "tools": [tool.name for tool in tools]
        })
        
        return agent_executor
    except Exception as e:
        log_error(e, "에이전트 생성 중 오류 발생")
        return None

# 에이전트 응답 생성
def generate_agent_response(agent, user_query, api_key=None, model=None):
    """
    사용자 쿼리에 대한 에이전트 응답을 생성합니다.
    """
    if not api_key:
        api_key = st.session_state.get('openai_api_key', '')
    
    if not model:
        model = get_model_name()
    
    try:
        # OpenAI API 호출 측정 시작
        with get_openai_callback() as cb:
            # 에이전트 실행
            result = agent.invoke({
                "input": user_query,
                "chat_history": st.session_state.get('chat_history', [])
            })
            
            # 통계 정보
            token_usage = {
                "total_tokens": cb.total_tokens,
                "prompt_tokens": cb.prompt_tokens,
                "completion_tokens": cb.completion_tokens,
                "total_cost": cb.total_cost
            }
            
            # 에이전트 응답 추출
            agent_response = result.get("output", "응답을 생성할 수 없습니다.")
            
            # 로깅
            log_info("에이전트 응답 생성 완료", {
                "query": user_query[:100] + "..." if len(user_query) > 100 else user_query,
                "token_usage": token_usage
            })
            
            return {
                "response": agent_response,
                "token_usage": token_usage
            }
    except Exception as e:
        error_msg = f"응답 생성 중 오류: {str(e)}"
        log_error(e, error_msg)
        return {
            "response": error_msg,
            "token_usage": {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_cost": 0}
        }

# 간단한 텍스트 응답 생성
def generate_text_response(prompt, api_key=None, model=None):
    """
    단순 텍스트 응답을 생성합니다.
    """
    if not api_key:
        api_key = st.session_state.get('openai_api_key', '')
    
    if not model:
        model = get_model_name()
    
    try:
        # OpenAI 클라이언트 생성
        client = create_openai_client(api_key)
        
        # API 호출
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "당신은 도움이 되는 AI 어시스턴트입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # 응답 추출
        result = response.choices[0].message.content
        
        # 토큰 사용량
        token_usage = {
            "total_tokens": response.usage.total_tokens,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_cost": 0  # 실제 비용은 계산하지 않음
        }
        
        return {
            "response": result,
            "token_usage": token_usage
        }
    except Exception as e:
        error_msg = f"텍스트 응답 생성 중 오류: {str(e)}"
        log_error(e, error_msg)
        return {
            "response": error_msg,
            "token_usage": {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_cost": 0}
        }

# 모델 이름 가져오기
def get_model_name(model_options=None):
    """
    선택된 모델 이름을 반환합니다.
    """
    if model_options is None:
        model_options = st.session_state.get('model_options', {})
    
    # 모델 이름 맵핑
    model_mapping = {
        "gpt 4o mini": "gpt-4o-mini",
        "claude 3 haiku": "claude-3-haiku-20240307",
        "claude 3.7 sonnet": "claude-3-sonnet-20240229",
        "gpt-3.5-turbo": "gpt-3.5-turbo",
        "gpt-4": "gpt-4",
        "gpt-4-turbo": "gpt-4-turbo"
    }
    
    # 문자열인 경우 바로 매핑
    if isinstance(model_options, str):
        return model_mapping.get(model_options.lower(), "gpt-3.5-turbo")
    
    # 딕셔너리인 경우 'selected_model' 키 확인
    selected_model = model_options.get('selected_model', 'gpt-3.5-turbo')
    
    # 매핑된 모델명 반환 (없으면 기본값)
    return model_mapping.get(selected_model.lower(), "gpt-3.5-turbo")

# 에이전트 정보 가져오기
def get_agent_info():
    """
    현재 에이전트 설정 정보를 반환합니다.
    """
    # 모델 정보
    model = get_model_name()
    
    # 지갑 상태
    wallet_status = get_wallet_status()
    
    # 도구 설명
    tools = get_tool_descriptions()
    
    # API 키 설정 여부
    api_key_set = bool(st.session_state.get('openai_api_key', ''))
    upbit_api_set = bool(st.session_state.get('upbit_api_key', '') and 
                          st.session_state.get('upbit_api_secret', ''))
    
    return {
        "agent": {
            "model": model,
            "api_ready": api_key_set
        },
        "wallet": {
            "status": wallet_status.get("wallet_state", "UNKNOWN"),
            "api_ready": upbit_api_set,
            "balance": wallet_status.get("krw_balance", 0),
            "total_value": wallet_status.get("total_value", 0)
        },
        "tools": tools
    }