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
    
    # 현재 API 키 상태 표시
    current_access_key = st.session_state.get("upbit_access_key", "")
    current_secret_key = st.session_state.get("upbit_secret_key", "")
    
    if current_access_key and current_secret_key:
        st.success("API 키가 설정되어 있습니다.")
        if st.button("API 키 초기화", key="api_key_reset"):
            st.session_state.upbit_access_key = ""
            st.session_state.upbit_secret_key = ""
            st.success("API 키가 초기화되었습니다.")
            st.rerun()
    
    # API 키 입력
    access_key = st.text_input("Upbit Access Key", value=current_access_key, type="password")
    secret_key = st.text_input("Upbit Secret Key", value=current_secret_key, type="password")
    
    # 저장 및 테스트 버튼
    if st.button("저장 및 테스트", key="api_key_save"):
        if not access_key or not secret_key:
            st.error("Access Key와 Secret Key를 모두 입력해주세요.")
            return
            
        try:
            # API 연결 테스트
            upbit = pyupbit.Upbit(access_key, secret_key)
            balance = upbit.get_balance("KRW")
            
            if balance is not None:
                # API 키 저장
                st.session_state.upbit_access_key = access_key
                st.session_state.upbit_secret_key = secret_key
                
                st.success("API 연결 성공! API 키가 저장되었습니다.")
                st.info("포트폴리오 탭으로 이동합니다...")
                
                # 포트폴리오 탭으로 전환
                st.session_state.active_tab = "포트폴리오"
                st.rerun()
            else:
                st.error("API 연결에 실패했습니다. 키를 확인해주세요.")
        except Exception as e:
            st.error(f"API 연결 중 오류가 발생했습니다: {str(e)}")
    
    # 도움말
    st.markdown("""
    ### API 키 설정 방법
    1. Upbit 계정에 로그인합니다.
    2. 고객센터 > Open API 관리로 이동합니다.
    3. API Key 발급을 클릭합니다.
    4. 발급받은 Access Key와 Secret Key를 입력합니다.
    5. 저장 및 테스트 버튼을 클릭하여 연결을 확인합니다.
    """)

def process_order_data(order: Dict) -> Dict:
    try:
        executed_price = float(order['executed_price']) if order['executed_price'] else 0
        executed_volume = float(order['executed_volume']) if order['executed_volume'] else 0
        paid_fee = float(order['paid_fee']) if order['paid_fee'] else 0
        
        return {
            "체결금액": format_number(executed_price * executed_volume),
            "수수료": format_number(paid_fee),
        }
    except Exception as e:
        st.error(f"주문 데이터 처리 중 오류 발생: {e}")
        return {}

def get_order_history(upbit: pyupbit.Upbit) -> Optional[List[Dict]]:
    """주문 내역 조회 (캐싱 적용)"""
    cache_key = "order_history"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
        
    try:
        orders = upbit.get_order_completed()
        st.session_state[cache_key] = orders
        return orders
    except Exception as e:
        st.error(f"주문 내역 조회 실패: {e}")
        return None