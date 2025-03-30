import streamlit as st
from page.portfolio import show_portfolio
from page.api_setting import show_api_settings, init_api_session_state
from model.api_anthropic import stream_anthropic_response

# 세션 상태 초기화
init_api_session_state()

# 채팅 기록 초기화
if 'messages' not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 투자에 관해 무엇을 도와드릴까요?"}]

st.set_page_config(
    page_title="AI 투자 채팅봇",
    page_icon="🦈",
    layout="wide",
)

main_col, chat_col = st.columns([0.65, 0.35], gap="large")

with main_col:
    portfolio_tab, strategy_tab, api_tab = st.tabs(["투자 내역", "투자 전략", "API 설정"])

    with portfolio_tab:
        show_portfolio()

    with strategy_tab:
        st.title("투자 전략")
        st.write("This is the strategy page of the app.")

    with api_tab:
        show_api_settings()


with chat_col:
    # 채팅 기록 표시하는 컨테이너를 채팅 입력 필드 위에 배치
    chat_container = st.container(height=700, border=True)
    
    # 사용자 입력 처리 (채팅 컨테이너 아래에 배치)
    user_prompt = st.chat_input(
        placeholder="어떻게 투자할까요?",
        accept_file=True,
        file_type=None
    )
    
    # 채팅 기록 채우기 (이제 입력 필드 위에 표시됨)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
    
    if user_prompt:
        # 사용자 메시지 추가 및 표시
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        
        # 스트리밍 방식으로 응답 생성 및 표시
        with chat_container:
            with st.chat_message("user"):
                st.write(user_prompt)
                
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                full_response = ""
                
                # 스트리밍 응답 처리
                for chunk in stream_anthropic_response(
                    user_prompt, 
                    system_prompt="당신은 암호화폐 투자 전문가입니다. 사용자의 투자 관련 질문에 전문적으로 답변해주세요."
                ):
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")
                
                # 최종 응답으로 업데이트
                response_placeholder.markdown(full_response)
                
                # 응답 기록에 저장
                st.session_state.messages.append({"role": "assistant", "content": full_response})



