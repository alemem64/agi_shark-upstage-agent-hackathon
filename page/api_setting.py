import streamlit as st
import pyupbit
from typing import Optional, List, Dict
import time
from datetime import datetime
import os
import tweepy
import json

# API 키 저장 파일 경로
API_KEY_STORE_FILE = "data/api_key_store.json"

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

def load_api_keys() -> Dict:
    """저장된 API 키를 파일에서 로드"""
    if not os.path.exists(API_KEY_STORE_FILE):
        return {}
    
    try:
        with open(API_KEY_STORE_FILE, 'r') as f:
            api_keys = json.load(f)
        print("API 키가 파일에서 로드되었습니다.")
        return api_keys
    except Exception as e:
        print(f"API 키 로드 오류: {str(e)}")
        return {}

def save_api_keys_to_file(api_keys: Dict) -> bool:
    """API 키를 파일에 저장"""
    try:
        # 디렉토리가 없으면 생성
        os.makedirs(os.path.dirname(API_KEY_STORE_FILE), exist_ok=True)
        
        with open(API_KEY_STORE_FILE, 'w') as f:
            json.dump(api_keys, f, indent=2)
        
        print("API 키가 파일에 저장되었습니다.")
        return True
    except Exception as e:
        print(f"API 키 저장 오류: {str(e)}")
        return False

def init_api_session_state():
    """API 키 관련 세션 상태 초기화"""
    # 파일에서 API 키 로드
    stored_keys = load_api_keys()
    
    # 세션 상태 초기화 및 저장된 키 적용
    if 'anthropic_key' not in st.session_state:
        st.session_state.anthropic_key = stored_keys.get('anthropic_key', "")
    if 'openai_key' not in st.session_state:
        st.session_state.openai_key = stored_keys.get('openai_key', "")
    if 'upbit_access_key' not in st.session_state:
        st.session_state.upbit_access_key = stored_keys.get('upbit_access_key', "")
    if 'upbit_secret_key' not in st.session_state:
        st.session_state.upbit_secret_key = stored_keys.get('upbit_secret_key', "")
    if 'upstage_api_key' not in st.session_state:
        st.session_state.upstage_api_key = stored_keys.get('upstage_api_key', "")
    if 'X_bearer_token' not in st.session_state:
        st.session_state.X_bearer_token = stored_keys.get('X_bearer_token', "")

def save_api_keys(openai_key, anthropic_key, upbit_access_key, upbit_secret_key, upstage_api_key, X_bearer_token):
    """API 키를 세션 상태와 파일에 저장"""
    # 세션 상태에 저장
    st.session_state.openai_key = openai_key
    st.session_state.anthropic_key = anthropic_key
    st.session_state.upbit_access_key = upbit_access_key
    st.session_state.upbit_secret_key = upbit_secret_key
    st.session_state.upstage_api_key = upstage_api_key
    st.session_state.X_bearer_token = X_bearer_token
    
    # 파일에 저장
    api_keys = {
        'openai_key': openai_key,
        'anthropic_key': anthropic_key,
        'upbit_access_key': upbit_access_key,
        'upbit_secret_key': upbit_secret_key,
        'upstage_api_key': upstage_api_key,
        'X_bearer_token': X_bearer_token
    }
    
    save_success = save_api_keys_to_file(api_keys)
    
    if save_success:
        st.success("API 키가 저장되었습니다!")
    else:
        st.warning("API 키가 세션에 저장되었지만 파일 저장에 실패했습니다.")

def show_api_settings():
    st.title("API 설정")
    
    # 필수 API 키가 설정되지 않은 경우 경고 표시
    if not st.session_state.upstage_api_key:
        st.warning("⚠️ Upstage API 키가 설정되지 않았습니다. 문서 처리 기능을 사용하려면 키를 입력해주세요.")
    
    if not st.session_state.openai_key:
        st.warning("⚠️ OpenAI API 키가 설정되지 않았습니다. RAG 및 LLM 기능을 사용하려면 키를 입력해주세요.")
    
    st.header("upstage")
    upstage_api_key = st.text_input("upstage API 키 (필수)", value=st.session_state.upstage_api_key, type="password")
    st.divider()

    st.header("LLM")
    openai_key = st.text_input("OpenAI API 키 (필수)", value=st.session_state.openai_key, type="password")
    anthropic_key = st.text_input("Anthropic API 키 (선택)", value=st.session_state.anthropic_key, type="password")
    st.divider()

    st.header("Upbit")
    upbit_access_key = st.text_input("Upbit Access API 키 (필수)", value=st.session_state.upbit_access_key, type="password")
    upbit_secret_key = st.text_input("Upbit Secret API 키 (필수)", value=st.session_state.upbit_secret_key, type="password")
    st.divider()

    st.header("X")
    X_bearer_token = st.text_input("X bearer API 키 (선택)", value=st.session_state.X_bearer_token, type="password")

    if st.button("저장하기", type="primary"):
        save_api_keys(openai_key, anthropic_key, upbit_access_key, upbit_secret_key, upstage_api_key, X_bearer_token)