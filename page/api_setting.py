import streamlit as st
import pyupbit
from typing import Optional, List, Dict
import time
from datetime import datetime
import os

def test_upbit_api(access_key: str, secret_key: str) -> bool:
    """Upbit API 키 테스트"""
    try:
        upbit = pyupbit.Upbit(access_key, secret_key)
        # 간단한 API 호출 테스트
        balance = upbit.get_balance("KRW")
        if balance is not None:
            st.success("Upbit API 연결 성공!")
            return True
        else:
            st.error("Upbit API 연결 실패: 잔고 조회 실패")
            return False
    except Exception as e:
        st.error(f"Upbit API 연결 실패: {e}")
        return False

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