import streamlit as st
import pyupbit
from typing import Optional, List, Dict
import time
from datetime import datetime
import os
import tweepy
import json
import sys
from UPBIT import Trade

# API 키 저장 파일 경로
API_KEY_STORE_FILE = "data/api_key_store.json"
sys.path.append("tools/upbit")

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
    # API 경고 메시지가 이미 표시되었는지 추적하는 플래그 추가
    if 'api_warning_shown' not in st.session_state:
        st.session_state.api_warning_shown = False

def check_api_keys():
    """API 키가 설정되었는지 확인하고, 필요한 경우 경고 메시지 표시"""
    has_keys = st.session_state.upbit_access_key and st.session_state.upbit_secret_key
    
    # API 키가 없는 경우 경고 메시지 표시 (한 번만)
    if not has_keys and not st.session_state.api_warning_shown:
        # 사이드바에는 작은 경고 아이콘만 표시
        if hasattr(st.sidebar, 'current_key') and st.sidebar.current_key != "":
            st.sidebar.warning("API 키 미설정")
        else:
            # 실제 페이지에는 자세한 안내 표시
            with st.container():
                st.warning("업비트 API 키가 설정되지 않았습니다. API 설정 탭에서 키를 입력하세요.")
                st.info("현재는 데모 모드로 동작 중입니다. 샘플 데이터가 표시됩니다.")
        
        # 경고 메시지 표시 플래그 설정
        st.session_state.api_warning_shown = True
    
    return has_keys

def reset_api_warning():
    """탭 변경 시 API 경고 메시지 초기화 (각 탭에서 한 번씩만 표시)"""
    st.session_state.api_warning_shown = False

def save_api_keys(openai_key, anthropic_key, upbit_access_key, upbit_secret_key, upstage_api_key, X_bearer_token):
    """API 키를 세션 상태와 파일에 저장"""
    # 세션 상태에 저장
    # 기존 API 키와 새 API 키 비교
    api_changed = (st.session_state.upbit_access_key != upbit_access_key or 
                  st.session_state.upbit_secret_key != upbit_secret_key)
    
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
    # API 키가 변경되었으면 캐시 초기화 플래그 설정
    if api_changed and upbit_access_key and upbit_secret_key:
        st.session_state.refresh_data = True
    
    if save_success:
        st.success("API 키가 저장되었습니다!")
    else:
        st.warning("API 키가 세션에 저장되었지만 파일 저장에 실패했습니다.")

def get_upbit_instance():
    """pyupbit 인스턴스 생성"""
    try:
        access_key = st.session_state.get("upbit_access_key")
        secret_key = st.session_state.get("upbit_secret_key")
        if not access_key or not secret_key:
            return None
        return pyupbit.Upbit(access_key, secret_key)
    except Exception as e:
        st.error(f"업비트 인스턴스 생성 중 오류 발생: {str(e)}")
        return None

def get_upbit_trade_instance():
    """UPBIT.Trade 클래스 인스턴스 생성"""
    try:
        access_key = st.session_state.get("upbit_access_key")
        secret_key = st.session_state.get("upbit_secret_key")
        if not access_key or not secret_key:
            return None
        return Trade(access_key, secret_key)
    except Exception as e:
        st.error(f"업비트 Trade 인스턴스 생성 중 오류 발생: {str(e)}")
        return None

def show_api_settings():
    # 둥근 입력란을 위한 CSS 추가
    st.markdown("""
    <style>
    /* 입력 필드 컨테이너 */
    div[data-baseweb="input"],
    div[data-baseweb="base-input"] {
        /* border-radius와 기본적인 border 스타일은 유지 */
        border-radius: 8px !important;
        border: 1px solid #ccc !important;
        transition: border-color 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
        /* 내부 input과의 간격을 위해 패딩 조정 */
        padding: 1px !important; /* 컨테이너 패딩 최소화 */
    }

    /* 포커스 시 컨테이너 스타일 */
    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="base-input"]:focus-within {
        border-color: #007bff !important;
        box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25) !important;
    }

    /* 내부 input 요소 */
    .stTextInput input[type="text"],
    .stTextInput input[type="password"] {
        border: none !important; /* 내부 input의 기본 테두리 제거 */
        border-radius: 7px !important; /* 컨테이너보다 약간 작게 */
        padding: 8px 10px !important; /* 내부 패딩 */
        /* 배경색 등을 투명하게 하여 컨테이너 배경이 보이도록 할 수도 있음 */
        background-color: transparent !important;
        box-shadow: none !important; /* 내부 그림자 제거 */
        outline: none !important; /* 포커스 시 기본 외곽선 제거 */
        width: 100%; /* 너비 채우기 */
        box-sizing: border-box; /* 패딩 포함 너비 계산 */
    }

    /* Streamlit의 특정 구조 타겟팅 강화 (필요시) */
    div[data-testid="stTextInput"] > div > div {
        /* 이 요소에 직접적인 border나 padding은 피함 */
        border: none !important;
        padding: 0 !important;
    }

    .stButton > button {
        border-radius: 8px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
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
        
        # API 키 테스트
        if upbit_access_key and upbit_secret_key:
            st.info("Upbit API 키를 테스트합니다...")
            api_success = test_upbit_api(upbit_access_key, upbit_secret_key)
            
            # API 연동 성공 시 즉시 캐시 초기화
            if api_success:
                st.info("모든 데이터를 새로고침합니다...")
                # 캐시 초기화
                st.cache_data.clear()
                # 연동 완료 상태 표시
                st.success("API 연동이 완료되었습니다. 모든 페이지에서 실제 데이터가 표시됩니다.")
                st.balloons()  # 축하 효과
                
                # 자동으로 다른 페이지로 이동
                st.info("실제 데이터를 가져오기 위해 페이지를 새로고침합니다...")
                time.sleep(2)  # 사용자가 메시지를 읽을 시간을 줍니다
                st.session_state.selected_tab = "포트폴리오"  # 기본적으로 포트폴리오 페이지로 이동
                st.rerun()