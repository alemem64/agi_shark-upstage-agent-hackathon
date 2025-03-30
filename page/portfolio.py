import streamlit as st
import pyupbit
import pandas as pd
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import plotly.graph_objects as go

def format_number(number: float) -> str:
    """숫자 포맷팅"""
    return f"{number:,.2f}"

def get_upbit_instance():
    try:
        access_key = st.session_state.get("upbit_access_key")
        secret_key = st.session_state.get("upbit_secret_key")
        if not access_key or not secret_key:
            st.error("API 키가 설정되지 않았습니다. API 설정 페이지에서 API 키를 입력해주세요.")
            return None
        return pyupbit.Upbit(access_key, secret_key)
    except Exception as e:
        st.error(f"업비트 인스턴스 생성 중 오류 발생: {str(e)}")
        return None

@st.cache_data(ttl=60)  # 1분 캐시
def get_portfolio_info():
    try:
        upbit = get_upbit_instance()
        if not upbit:
            return None, pd.DataFrame()
            
        # 보유 자산 조회
        balances = upbit.get_balances()
        if not balances:
            return None, pd.DataFrame()
            
        # KRW 잔고
        krw_balance = float(next((b['balance'] for b in balances if b['currency'] == 'KRW'), 0))
        
        # 코인 보유 내역
        coin_balances = []
        total_investment = 0
        total_current_value = 0
        
        for balance in balances:
            if balance['currency'] != 'KRW':
                ticker = f"KRW-{balance['currency']}"
                current_price = pyupbit.get_current_price(ticker)
                
                if current_price:
                    quantity = float(balance['balance'])
                    avg_buy_price = float(balance['avg_buy_price'])
                    current_value = quantity * current_price
                    investment = quantity * avg_buy_price
                    
                    coin_balances.append({
                        '코인': balance['currency'],
                        '수량': quantity,
                        '평균매수가': avg_buy_price,
                        '현재가': current_price,
                        '평가금액': current_value,
                        '투자금액': investment,
                        '평가손익': current_value - investment,
                        '수익률': ((current_price - avg_buy_price) / avg_buy_price) * 100
                    })
                    
                    total_investment += investment
                    total_current_value += current_value
        
        # 포트폴리오 요약 정보
        portfolio_summary = {
            '총보유자산': total_current_value + krw_balance,
            '총투자금액': total_investment,
            '총평가손익': total_current_value - total_investment,
            '총수익률': ((total_current_value - total_investment) / total_investment * 100) if total_investment > 0 else 0,
            '보유현금': krw_balance
        }
        
        # 데이터프레임 생성
        df = pd.DataFrame(coin_balances)
        if not df.empty:
            df = df.sort_values('평가금액', ascending=False)
        
        return portfolio_summary, df
        
    except Exception as e:
        st.error(f"포트폴리오 정보 조회 중 오류 발생: {str(e)}")
        return None, pd.DataFrame()

def show_portfolio():
    try:
        st.title("포트폴리오")
        
        # API 키 확인
        if not st.session_state.get("upbit_access_key") or not st.session_state.get("upbit_secret_key"):
            st.warning("API 키가 설정되지 않았습니다. API 설정 페이지에서 API 키를 입력해주세요.")
            return
            
        # 새로고침 버튼
        if st.button("🔄 새로고침", key="portfolio_refresh"):
            st.cache_data.clear()
            st.rerun()
            
        # 포트폴리오 정보 조회
        portfolio_summary, coin_balances = get_portfolio_info()
        
        if portfolio_summary:
            # 포트폴리오 요약 정보
            st.markdown("### 📊 포트폴리오 요약")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "총 보유자산",
                    f"{portfolio_summary['총보유자산']:,.0f}원",
                    f"{portfolio_summary['보유현금']:,.0f}원 (현금)"
                )
            with col2:
                st.metric(
                    "총 평가손익",
                    f"{portfolio_summary['총평가손익']:,.0f}원",
                    f"{portfolio_summary['총수익률']:.2f}%"
                )
            with col3:
                st.metric(
                    "총 투자금액",
                    f"{portfolio_summary['총투자금액']:,.0f}원"
                )
            with col4:
                st.metric(
                    "보유 현금",
                    f"{portfolio_summary['보유현금']:,.0f}원"
                )
            
            # 보유 코인 목록
            st.markdown("### 💰 보유 코인")
            if not coin_balances.empty:
                st.dataframe(
                    coin_balances,
                    use_container_width=True,
                    column_config={
                        "코인": st.column_config.TextColumn(
                            "코인",
                            width="medium"
                        ),
                        "수량": st.column_config.NumberColumn(
                            "수량",
                            format="%.8f",
                            width="medium"
                        ),
                        "평균매수가": st.column_config.NumberColumn(
                            "평균매수가",
                            format="%.0f",
                            width="medium"
                        ),
                        "현재가": st.column_config.NumberColumn(
                            "현재가",
                            format="%.0f",
                            width="medium"
                        ),
                        "평가금액": st.column_config.NumberColumn(
                            "평가금액",
                            format="%.0f",
                            width="medium"
                        ),
                        "투자금액": st.column_config.NumberColumn(
                            "투자금액",
                            format="%.0f",
                            width="medium"
                        ),
                        "평가손익": st.column_config.NumberColumn(
                            "평가손익",
                            format="%.0f",
                            width="medium"
                        ),
                        "수익률": st.column_config.NumberColumn(
                            "수익률",
                            format="%.2f%%",
                            width="medium"
                        )
                    }
                )
            else:
                st.info("보유한 코인이 없습니다.")
        else:
            st.error("포트폴리오 정보를 가져오지 못했습니다.")
            
    except Exception as e:
        st.error(f"포트폴리오 페이지 로딩 중 오류 발생: {str(e)}")