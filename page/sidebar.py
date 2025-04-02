import streamlit as st
import asyncio
import uuid

from model.open_ai_agent import stream_openai_response
from datetime import datetime
from model.document_parser_agent import DocumentParserAgent

def show_sidebar():
    st.title("암호화폐 거래 AI Agent")
    chat_tab, chat_settings_tab = st.tabs(["채팅", "Agent 설정"])

    # 세션 상태에 Agent 상태 변수 초기화
    if 'agent_run_count' not in st.session_state:
        st.session_state.agent_run_count = 0
    
    if 'agent_start_time' not in st.session_state:
        st.session_state.agent_start_time = None

    # 세션 상태 초기화 부분에 conversation_id 추가
    if 'conversation_id' not in st.session_state:
        st.session_state.conversation_id = f"conversation_{uuid.uuid4()}"

    # Agent 실행 시간 계산 함수
    def calculate_runtime():
        if st.session_state.agent_start_time:
            current_time = datetime.now()
            runtime = current_time - st.session_state.agent_start_time
            minutes = int(runtime.total_seconds() // 60)
            return f"{minutes}분"
        return "0분"

    with chat_tab:

        chat_container = st.container(height=650, border=True)
        
        # 사용자 입력 처리 (채팅 컨테이너 아래에 배치)
        user_prompt = st.chat_input(
            placeholder="어떻게 투자할까요?",
            accept_file=True,
            file_type=None
        )

        # 채팅 기록 채우기 
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.write(message["content"])
        
        if user_prompt:
            st.session_state.agent_run_count += 1
            user_prompt_text = user_prompt.text if user_prompt.text else ""
            user_prompt_file = user_prompt.get("files", [None])[0] if user_prompt.get("files") else None
            
            # 파일이 업로드된 경우 문서 분석 수행
            document_text = ""
            if user_prompt_file:
                parser = DocumentParserAgent()
                result = parser.parse_document(user_prompt_file.getvalue(), user_prompt_file.name)
                
                if result['success']:
                    document_text = f"\n\n참고 문서 내용:\n{result['text']}"
                    st.session_state.messages.append({
                        "role": "system",
                        "content": f"사용자가 업로드한 문서 '{result['metadata']['file_name']}'의 내용입니다: {document_text}"
                    })
                else:
                    st.error(f"문서 분석 실패: {result['error']}")
            
            # 사용자 메시지와 문서 내용을 합쳐서 전달
            full_prompt = user_prompt_text + document_text
            st.session_state.messages.append({"role": "user", "content": user_prompt_text})

            print(full_prompt)
            
            # 스트리밍 방식으로 응답 생성 및 표시
            with chat_container:
                with st.chat_message("user"):
                    st.write(user_prompt_text)
                    
                with st.chat_message("assistant"):
                    response_placeholder = st.empty()
                    # 스트리밍 응답 처리
                    # 이벤트 루프 생성 및 관리 방식 변경
                    full_response = ""
                    sent_data = f"입력: {full_prompt[:50]}..., 모델: {st.session_state.model_options}"
                    print(f"요청 데이터: {sent_data}")

                    try:
                        # 기존 이벤트 루프 가져오기 시도
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            # 이벤트 루프가 없으면 새로 생성
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        # 비동기 코루틴 함수
                        async def process_chunks():
                            nonlocal full_response
                            full_response = ""
                            try:
                                async for chunk in stream_openai_response(
                                    full_prompt,
                                    st.session_state.model_options,
                                    st.session_state.conversation_id
                                ):
                                    print(f"청크 수신: {len(chunk)} 바이트")
                                    full_response += chunk
                                    response_placeholder.markdown(full_response + "▌")
                                
                                response_placeholder.markdown(full_response)
                                return full_response
                            except Exception as e:
                                error_msg = f"응답 생성 중 오류: {str(e)}"
                                print(error_msg)
                                response_placeholder.markdown(error_msg)
                                return error_msg
                        
                        # 기존 루프에서 실행하거나 새 루프에서 실행
                        if loop.is_running():
                            print("기존 이벤트 루프 사용 중")
                            task = asyncio.create_task(process_chunks())
                            full_response = st.session_state.get("_temp_response", "")
                            st.session_state["_temp_task"] = task
                        else:
                            print("새 이벤트 루프 실행")
                            full_response = loop.run_until_complete(
                                asyncio.wait_for(process_chunks(), timeout=60)
                            )
                        
                        print(f"응답 완료: {len(full_response)} 자")
                        
                    except asyncio.TimeoutError:
                        full_response = "응답 생성 시간이 초과되었습니다. 다시 시도해주세요."
                        response_placeholder.markdown(full_response)
                        print("타임아웃 발생")
                    except Exception as e:
                        full_response = f"오류 발생: {str(e)}"
                        response_placeholder.markdown(full_response)
                        print(f"예외 발생: {str(e)}")
                    
                    # 응답 기록에 저장
                    st.session_state.messages.append({"role": "assistant", "content": full_response})

    with chat_settings_tab:
        with st.expander("Agent 상태", expanded=True):
            agent_status_col1, agent_status_col2 = st.columns(2)
            with agent_status_col1:
                st.markdown(
                f"""
                    Agent 작동 횟수 :primary-background[**{st.session_state.agent_run_count}회**]
                    
                """
                )
            with agent_status_col2:
                st.markdown(
                f"""
                    Agent 작동 시간 :primary-background[**{calculate_runtime()}**]
                """
                )

        with st.expander("Agent 설정", expanded=True):
            reboot_button = st.button("Agent 재부팅", use_container_width=True)
            # 수동 재부팅 버튼 처리
            if reboot_button:
                st.session_state.agent_run_count = 0
                st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 투자에 관해 무엇을 도와드릴까요?"}]
                st.session_state.agent_start_time = datetime.now()
                # 대화 ID 초기화
                st.session_state.conversation_id = f"conversation_{uuid.uuid4()}"
                st.success("Agent가 재부팅되었습니다.")
                st.rerun()
            reboot_frequency = st.text_input("Agent 재부팅 주기 (작동 횟수)", value="10")

            # 재부팅 주기 체크 및 LLM 초기화
            try:
                reboot_freq = int(reboot_frequency)
                if st.session_state.agent_run_count >= reboot_freq:
                    st.session_state.agent_run_count = 0  # 카운터 초기화
                    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 투자에 관해 무엇을 도와드릴까요?"}]  # 채팅 기록 초기화
                    st.session_state.agent_start_time = datetime.now()  # 시작 시간 재설정
                    st.success(f"Agent가 {reboot_freq}회 작동 후 자동으로 재부팅되었습니다.")
                    st.rerun()
            except ValueError:
                st.error("재부팅 주기는 숫자로 입력해주세요.")

            work_frequency = st.text_input("Agent 작동 주기 (초)", value="10")
            st.session_state.model_options = st.selectbox("LLM 모델 선택", ("gpt 4o mini", "claude 3 haiku", "claude 3.7 sonnet"))
            toogle_col1, toogle_col2 = st.columns(2)
            with toogle_col1:
                toggle_web_search = st.toggle("웹 검색 참조", value=True)
                toggle_see_prev_trade = st.toggle("이전 거래 내역 숙고", value=True)
            with toogle_col2:
                toggle_always_see_doc = st.toggle("항시 참조 문서", value=True)
                toggle_see_rag_doc = st.toggle("RAG 문서 참조", value=True)
                
        with st.expander("거래 설정", expanded=True):
            # 위험 성향 선택 시 세션 상태에 저장
            risk_style = st.select_slider(
                "위험 성향",
                options=["보수적", "중립적", "공격적"],
                value="중립적",
            )
            st.session_state['risk_style'] = risk_style

            # 거래 기간 선택 시 세션 상태에 저장
            trading_period = st.select_slider(
                "거래 기간",
                options=["단기", "스윙", "장기"],
                value="스윙",
            )
            st.session_state['trading_period'] = trading_period

            user_requirement = st.text_area("기타 거래 조건", value="비트코인을 주로 투자하고 싶어")
            st.session_state['user_requirement'] = user_requirement

        apply_chat_settings_button = st.button("설정 적용하기", use_container_width=True, type="primary")
        if apply_chat_settings_button:
            st.success("설정이 적용되었습니다.")
        


        