import streamlit as st
from model.api_anthropic import stream_anthropic_response

def show_sidebar():
    st.title("암호화폐 거래 AI Agent")
    chat_tab, chat_settings_tab = st.tabs(["채팅", "설정"])

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
        st.session_state.model_options = st.selectbox("모델 선택", ("claude 3.7 sonnet", "claude 3 haiku"))