import streamlit as st
import pyupbit
from typing import Optional, List, Dict
import time
from datetime import datetime
import os
import sys
sys.path.append("tools/upbit")
from UPBIT import Trade

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

def save_api_keys(openai_key, anthropic_key, upbit_access_key, upbit_secret_key, upstage_api_key):
    """API 키를 세션 상태에 저장"""
    # 기존 API 키와 새 API 키 비교
    api_changed = (st.session_state.upbit_access_key != upbit_access_key or 
                  st.session_state.upbit_secret_key != upbit_secret_key)
    
    # 세션 상태에 저장
    st.session_state.openai_key = openai_key
    st.session_state.anthropic_key = anthropic_key
    st.session_state.upbit_access_key = upbit_access_key
    st.session_state.upbit_secret_key = upbit_secret_key
    st.session_state.upstage_api_key = upstage_api_key
    
    # API 키가 변경되었으면 캐시 초기화 플래그 설정
    if api_changed and upbit_access_key and upbit_secret_key:
        st.session_state.refresh_data = True
    
    st.success("API 키가 저장되었습니다!")

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
    div[data-baseweb="input"], div[data-baseweb="base-input"] {
        border-radius: 8px !important;
    }
    input[type="password"] {
        border-radius: 8px !important;
    }
    input[type="text"] {
        border-radius: 8px !important;
    }
    .stTextInput > div {
        border-radius: 8px !important;
    }
    .stTextInput > div > div {
        border-radius: 8px !important;
    }
    .stButton > button {
        border-radius: 8px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("API 설정")
    
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

    
    if st.button("저장하기", type="primary"):
        save_api_keys(openai_key, anthropic_key, upbit_access_key, upbit_secret_key, upstage_api_key)
        
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