import streamlit as st
from model.api_anthropic import stream_anthropic_response

def show_sidebar():
    st.title("암호화폐 거래 AI Agent")
    chat_tab, chat_settings_tab = st.tabs(["채팅", "Agent 설정"])

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
            # 사용자 메시지 추가 및 표시
            user_prompt_text = user_prompt.text if user_prompt.text else ""
            user_prompt_file = user_prompt["files"] if user_prompt["files"] else None
            
            st.session_state.messages.append({"role": "user", "content": user_prompt_text})

            # 스트리밍 방식으로 응답 생성 및 표시
            with chat_container:
                with st.chat_message("user"):
                    st.write(user_prompt_text)
                    
                with st.chat_message("assistant"):
                    response_placeholder = st.empty()
                    full_response = ""
                    
                    # 스트리밍 응답 처리
                    for chunk in stream_anthropic_response(
                        user_prompt_text,
                        st.session_state.model_options
                    ):
                        full_response += chunk
                        response_placeholder.markdown(full_response + "▌")
                    
                    # 최종 응답으로 업데이트
                    response_placeholder.markdown(full_response)
                    
                    # 응답 기록에 저장
                    st.session_state.messages.append({"role": "assistant", "content": full_response})

    with chat_settings_tab:

        with st.expander("Agent 상태", expanded=True):
            agent_status_col1, agent_status_col2 = st.columns(2)
            with agent_status_col1:
                st.markdown(
                """
                    Agent 작동 횟수 :primary-background[**5회**]
                    
                """
                )
            with agent_status_col2:
                st.markdown(
                """
                    Agent 작동 시간 :primary-background[**10분**]
                """
                )

        with st.expander("Agent 설정", expanded=True):
            reboot_button = st.button("Agent 재부팅", use_container_width=True)
            reboot_frequency = st.text_input("Agent 재부팅 주기 (초)", value="10")
            st.session_state.model_options = st.selectbox("LLM 모델 선택", ("claude 3.7 sonnet", "claude 3 haiku"))
            toogle_col1, toogle_col2 = st.columns(2)
            with toogle_col1:
                toggle_web_search = st.toggle("웹 검색 참조", value=True)
                toggle_see_prev_trade = st.toggle("이전 거래 내역 숙고", value=True)
            with toogle_col2:
                toggle_always_see_doc = st.toggle("항시 참조 문서", value=True)
                toggle_see_rag_doc = st.toggle("RAG 문서 참조", value=True)


        with st.expander("투자 성향", expanded=True):

            prefer_coin = st.text_area("사용자 맞춤 지시", value="비트코인을 주로 투자하고 싶어")

            risk_style = st.select_slider(
                "위험 성향",
                options=["보수적", "중립적", "공격적"],
                value="중립적",
            )

            trading_period = st.select_slider(
                "거래 기간",
                options=["단기", "스윙", "장기"],
                value="스윙",
            )
        
        


        