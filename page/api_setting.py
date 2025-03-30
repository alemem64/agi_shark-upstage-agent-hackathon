import streamlit as st

def init_api_session_state():
    """API 키 관련 세션 상태 초기화"""
    if 'anthropic_key' not in st.session_state:
        st.session_state.anthropic_key = ""
    if 'openai_key' not in st.session_state:
        st.session_state.openai_key = ""
    if 'upbit_access_key' not in st.session_state:
        st.session_state.upbit_access_key = ""
    if 'upbit_secret_key' not in st.session_state:
        st.session_state.upbit_secret_key = ""
    if 'upstage_api_key' not in st.session_state:
        st.session_state.upstage_api_key = ""

def save_api_keys(anthropic_key, openai_key, upbit_access_key, upbit_secret_key, upstage_api_key):
    """API 키를 세션 상태에 저장"""
    st.session_state.anthropic_key = anthropic_key
    st.session_state.openai_key = openai_key
    st.session_state.upbit_access_key = upbit_access_key
    st.session_state.upbit_secret_key = upbit_secret_key
    st.session_state.upstage_api_key = upstage_api_key
    st.success("API 키가 저장되었습니다!")

def show_api_settings():
    """API 설정 페이지 표시"""
    st.title("API 설정")
    
    st.header("upstage")
    upstage_api_key = st.text_input("upstage API 키 (필수)", value=st.session_state.upstage_api_key, type="password")
    st.divider()

    st.header("LLM")
    anthropic_key = st.text_input("Anthropic API 키 (선택)", value=st.session_state.anthropic_key, type="password")
    openai_key = st.text_input("OpenAI API 키 (선택)", value=st.session_state.openai_key, type="password")
    st.divider()

    st.header("Upbit")
    upbit_access_key = st.text_input("Upbit Access API 키 (필수)", value=st.session_state.upbit_access_key, type="password")
    upbit_secret_key = st.text_input("Upbit Secret API 키 (필수)", value=st.session_state.upbit_secret_key, type="password")
    st.divider()

    
    if st.button("저장하기", type="primary"):
        save_api_keys(anthropic_key, openai_key, upbit_access_key, upbit_secret_key, upstage_api_key)