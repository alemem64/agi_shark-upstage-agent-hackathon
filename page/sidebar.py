import streamlit as st
from model.api_anthropic import stream_anthropic_response
from datetime import datetime
from model.document_parser_agent import DocumentParserAgent
from model.X_agent import X_Agent

def show_sidebar():
    st.title("암호화폐 거래 AI Agent")
    chat_tab, chat_settings_tab = st.tabs(["채팅", "Agent 설정"])

    # 세션 상태에 Agent 상태 변수 초기화
    if 'agent_run_count' not in st.session_state:
        st.session_state.agent_run_count = 0
    
    if 'agent_start_time' not in st.session_state:
        st.session_state.agent_start_time = None

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
            user_prompt_file = None
            # 문서 처리만 유지
            document_text = ""
            if user_prompt_file:
                parser = DocumentParserAgent()
                result = parser.parse_document(user_prompt_file.getvalue(), user_prompt_file.name)
                if result['success']:
                    document_text = f"\n\n참고 문서 내용:\n{result['text']}"
            
            full_prompt = user_prompt_text + document_text  # search_info 제거
            st.session_state.messages.append({"role": "user", "content": user_prompt_text})
            
            with chat_container:
                with st.chat_message("user"):
                    st.write(user_prompt_text)
                with st.chat_message("assistant"):
                    response_placeholder = st.empty()
                    full_response = ""
                    for chunk in stream_anthropic_response(full_prompt, st.session_state.model_options):
                        full_response += chunk
                        response_placeholder.markdown(full_response + "▌")
                    response_placeholder.markdown(full_response)
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
                st.success("Agent가 재부팅되었습니다.")
            reboot_frequency = st.text_input("Agent 재부팅 주기 (작동 횟수)", value="10")

            # 재부팅 주기 체크 및 LLM 초기화
            try:
                reboot_freq = int(reboot_frequency)
                if st.session_state.agent_run_count >= reboot_freq:
                    st.session_state.agent_run_count = 0  # 카운터 초기화
                    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 투자에 관해 무엇을 도와드릴까요?"}]  # 채팅 기록 초기화
                    st.session_state.agent_start_time = datetime.now()  # 시작 시간 재설정
                    st.success(f"Agent가 {reboot_freq}회 작동 후 자동으로 재부팅되었습니다.")
            except ValueError:
                st.error("재부팅 주기는 숫자로 입력해주세요.")

            work_frequency = st.text_input("Agent 작동 주기 (초)", value="10")
            st.session_state.model_options = st.selectbox("LLM 모델 선택", ("claude 3.7 sonnet", "claude 3 haiku"))
            toogle_col1, toogle_col2 = st.columns(2)
            with toogle_col1:
                toggle_web_search = st.toggle("웹 검색 참조", value=True)
                toggle_see_prev_trade = st.toggle("이전 거래 내역 숙고", value=True)
            with toogle_col2:
                toggle_always_see_doc = st.toggle("항시 참조 문서", value=True)
                toggle_see_rag_doc = st.toggle("RAG 문서 참조", value=True)


        with st.expander("투자 성향", expanded=True):

            user_requirement = st.text_area("사용자 맞춤 지시", value="비트코인을 주로 투자하고 싶어")
            st.session_state['user_requirement'] = user_requirement
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

        apply_chat_settings_button = st.button("설정 적용하기", use_container_width=True, type="primary")
        if apply_chat_settings_button:
            st.success("설정이 적용되었습니다.")
        


        