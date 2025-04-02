import streamlit as st
import pyupbit
import pandas as pd
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import plotly.graph_objects as go
import sys
sys.path.append("tools/upbit")
from UPBIT import Trade

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

def get_upbit_trade_instance():
    """UPBIT.ipynb의 Trade 클래스 인스턴스 생성"""
    try:
        access_key = st.session_state.get("upbit_access_key")
        secret_key = st.session_state.get("upbit_secret_key")
        if not access_key or not secret_key:
            st.error("API 키가 설정되지 않았습니다. API 설정 페이지에서 API 키를 입력해주세요.")
            return None
        return Trade(access_key, secret_key)
    except Exception as e:
        st.error(f"업비트 Trade 인스턴스 생성 중 오류 발생: {str(e)}")
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

def calculate_daily_profit_rate(upbit_trade):
    """일일 수익률 계산"""
    try:
        tickers = pyupbit.get_tickers(fiat="KRW")
        
        # 24시간 전 가격 정보와 현재 가격 비교
        today_total = 0
        yesterday_total = 0
        
        for ticker in tickers:
            coin_name = ticker.split('-')[1]
            balance = upbit_trade.get_balance(coin_name)
            
            if balance > 0:
                # 현재 가격
                current_price = upbit_trade.get_current_price(ticker)
                
                # 24시간 전 가격
                today_value = balance * current_price
                
                # 일봉 데이터에서 전일 종가 가져오기
                df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
                if df is not None and not df.empty:
                    yesterday_price = df.iloc[0]['close']
                    yesterday_value = balance * yesterday_price
                    
                    today_total += today_value
                    yesterday_total += yesterday_value
        
        # 현금 포함
        krw_balance = upbit_trade.get_balance("KRW")
        today_total += krw_balance
        yesterday_total += krw_balance
        
        # 일일 수익률 계산
        if yesterday_total > 0:
            daily_profit_rate = ((today_total - yesterday_total) / yesterday_total) * 100
            return daily_profit_rate
        else:
            return 0
            
    except Exception as e:
        st.error(f"일일 수익률 계산 중 오류 발생: {str(e)}")
        return 0

def get_portfolio_info_from_trade(upbit_trade):
    """Trade 클래스를 사용하여 포트폴리오 정보 조회"""
    try:
        # KRW 잔고
        krw_balance = upbit_trade.get_balance("KRW")
        
        # 코인 보유 내역
        coin_balances = []
        total_investment = 0
        total_current_value = 0
        
        # 모든 KRW 마켓 티커 조회
        tickers = pyupbit.get_tickers(fiat="KRW")
        
        for ticker in tickers:
            coin_name = ticker.split('-')[1]
            balance = upbit_trade.get_balance(coin_name)
            
            if balance > 0:
                current_price = upbit_trade.get_current_price(ticker)
                
                if current_price:
                    # 평균 매수가 조회 (API에서 지원하지 않는 경우 추정)
                    try:
                        # 계좌 정보에서 평균 매수가 가져오기 시도
                        avg_buy_price = upbit_trade.upbit.get_avg_buy_price(ticker)
                    except:
                        # API에서 지원하지 않는 경우 현재가로 대체
                        avg_buy_price = current_price
                    
                    current_value = balance * current_price
                    investment = balance * avg_buy_price
                    
                    coin_balances.append({
                        '코인': coin_name,
                        '수량': balance,
                        '평균매수가': avg_buy_price,
                        '현재가': current_price,
                        '평가금액': current_value,
                        '투자금액': investment,
                        '평가손익': current_value - investment,
                        '수익률': ((current_price - avg_buy_price) / avg_buy_price) * 100 if avg_buy_price > 0 else 0
                    })
                    
                    total_investment += investment
                    total_current_value += current_value
        
        # 일일 수익률 계산
        daily_profit_rate = calculate_daily_profit_rate(upbit_trade)
        
        # 포트폴리오 요약 정보
        portfolio_summary = {
            '총보유자산': total_current_value + krw_balance,
            '총투자금액': total_investment,
            '총평가손익': total_current_value - total_investment,
            '총수익률': ((total_current_value - total_investment) / total_investment * 100) if total_investment > 0 else 0,
            '보유현금': krw_balance,
            '일평가수익률': daily_profit_rate
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
            
        # Trade 클래스 인스턴스 생성
        upbit_trade = get_upbit_trade_instance()
        if not upbit_trade:
            return
            
        # 포트폴리오 정보 조회
        portfolio_summary, coin_balances = get_portfolio_info_from_trade(upbit_trade)
        
        if portfolio_summary:
            # 포트폴리오 요약 정보
            st.markdown("### 📊 포트폴리오 요약")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric(
                    "총 보유자산",
                    f"{portfolio_summary['총보유자산']:,.0f}원"
                )
            with col2:
                st.metric(
                    "총 평가손익",
                    f"{portfolio_summary['총평가손익']:,.0f}원",
                    f"{portfolio_summary['총수익률']:.2f}%"
                )
            with col3:
                st.metric(
                    "일 평가수익률",
                    f"{portfolio_summary['일평가수익률']:.2f}%"
                )
            with col4:
                st.metric(
                    "총 투자금액",
                    f"{portfolio_summary['총투자금액']:,.0f}원"
                )
            with col5:
                st.metric(
                    "보유 현금",
                    f"{portfolio_summary['보유현금']:,.0f}원"
                )
            
            # 보유 코인 목록
            st.markdown("### 💰 보유 코인")
            if not coin_balances.empty:
                st.dataframe(
                    coin_balances.style.format({
                        '수량': '{:.8f}',
                        '평균매수가': '{:,.0f}',
                        '현재가': '{:,.0f}',
                        '평가금액': '{:,.0f}',
                        '투자금액': '{:,.0f}',
                        '평가손익': '{:,.0f}',
                        '수익률': '{:+.2f}%'
                    }),
                    use_container_width=True
                )
            else:
                st.info("보유한 코인이 없습니다.")
        else:
            st.error("포트폴리오 정보를 가져오지 못했습니다.")
            
    except Exception as e:
        st.error(f"포트폴리오 페이지 로딩 중 오류 발생: {str(e)}")
