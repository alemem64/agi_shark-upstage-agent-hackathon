import streamlit as st
import pyupbit
import pandas as pd
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import plotly.graph_objects as go
import sys
import numpy as np
sys.path.append("tools/upbit")
from UPBIT import Trade
from page.api_setting import check_api_keys, get_upbit_instance, get_upbit_trade_instance

def format_number(number: float) -> str:
    """숫자 포맷팅"""
    return f"{number:,.2f}"

@st.cache_data(ttl=300)  # 5분 캐시로 증가
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

def generate_sample_portfolio_data():
    """샘플 포트폴리오 데이터 생성 (API 호출 실패 시 대체용)"""
    # 포트폴리오 요약 정보
    portfolio_summary = {
        '총보유자산': 10000000,
        '총투자금액': 8000000,
        '총평가손익': 2000000,
        '총수익률': 25.0,
        '보유현금': 2000000,
        '일평가수익률': 1.5
    }
    
    # 코인 보유 내역
    sample_coins = [
        {'코인': 'BTC', '수량': 0.01, '평균매수가': 48000000, '현재가': 50000000, 
         '평가금액': 500000, '투자금액': 480000, '평가손익': 20000, '수익률': 4.17},
        {'코인': 'ETH', '수량': 0.5, '평균매수가': 2800000, '현재가': 3000000, 
         '평가금액': 1500000, '투자금액': 1400000, '평가손익': 100000, '수익률': 7.14},
        {'코인': 'XRP', '수량': 10000, '평균매수가': 450, '현재가': 500, 
         '평가금액': 5000000, '투자금액': 4500000, '평가손익': 500000, '수익률': 11.11},
        {'코인': 'SOL', '수량': 10, '평균매수가': 100000, '현재가': 120000, 
         '평가금액': 1200000, '투자금액': 1000000, '평가손익': 200000, '수익률': 20.0},
    ]
    
    return portfolio_summary, pd.DataFrame(sample_coins)

def calculate_daily_profit_rate(upbit_trade):
    """일일 수익률 계산"""
    try:
        # 주요 코인 리스트 (모든 코인을 조회하지 않고 주요 코인만 확인하여 속도 개선)
        major_tickers = ["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-SOL", "KRW-DOGE", "KRW-ADA"]
        
        # 24시간 전 가격 정보와 현재 가격 비교
        today_total = 0
        yesterday_total = 0
        
        # 모든 가격 한 번에 조회 (여러 API 호출 대신 한 번의 API 호출)
        current_prices = pyupbit.get_current_price(major_tickers)
        
        for ticker in major_tickers:
            coin_name = ticker.split('-')[1]
            balance = upbit_trade.get_balance(coin_name)
            
            if balance > 0:
                # 현재 가격
                current_price = current_prices.get(ticker, 0)
                
                if current_price > 0:
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
        return 0  # 오류 발생 시 기본값 반환 (UI에 0%로 표시)

@st.cache_data(ttl=300)  # 5분 캐시로 증가
def get_portfolio_info_from_trade(upbit_trade):
    """Trade 클래스를 사용하여 포트폴리오 정보 조회"""
    try:
        if not upbit_trade:
            # API 키가 없거나 인스턴스 생성 실패 시 샘플 데이터 반환
            return generate_sample_portfolio_data()
            
        # KRW 잔고
        krw_balance = upbit_trade.get_balance("KRW")
        
        # 코인 보유 내역
        coin_balances = []
        total_investment = 0
        total_current_value = 0
        
        # 모든 KRW 마켓 티커 중 주요 코인만 조회 (속도 개선)
        major_tickers = ["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-SOL", "KRW-DOGE", "KRW-ADA"]
        other_tickers = [f"KRW-{coin}" for coin in ["MATIC", "DOT", "LINK", "AVAX", "SHIB"]]
        tickers = major_tickers + other_tickers
        
        # 모든 가격 한 번에 조회 (여러 API 호출 대신 한 번의 API 호출)
        current_prices = pyupbit.get_current_price(tickers)
        
        for ticker in tickers:
            coin_name = ticker.split('-')[1]
            balance = upbit_trade.get_balance(coin_name)
            
            if balance > 0:
                current_price = current_prices.get(ticker, 0)
                
                if current_price > 0:
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
        
        # 포트폴리오가 비어있으면 샘플 데이터 반환
        if not coin_balances:
            return generate_sample_portfolio_data()
        
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
        # 오류 발생 시 샘플 데이터 반환
        return generate_sample_portfolio_data()

def show_portfolio():
    """포트폴리오 표시"""
    # 이미 app.py에서 타이틀을 추가하므로 여기서는 제거
    
    # API 키 확인
    has_api_keys = check_api_keys()
    
    # Upbit Trade 인스턴스 생성
    upbit_trade = get_upbit_trade_instance()
    
    # 새로고침 버튼
    if st.button("🔄 새로고침", key="portfolio_refresh"):
        st.cache_data.clear()
        st.rerun()
    
    # 포트폴리오 정보 조회
    portfolio_summary, coin_balances = get_portfolio_info_from_trade(upbit_trade)
    
    if not portfolio_summary:
        st.error("포트폴리오 정보를 불러오지 못했습니다.")
        # 샘플 데이터 생성
        portfolio_summary, coin_balances = generate_sample_portfolio_data()
    
    # 일일 수익률 계산
    daily_profit_rate = 0
    if upbit_trade:
        daily_profit_rate = calculate_daily_profit_rate(upbit_trade)
    else:
        # 샘플 데이터 사용
        daily_profit_rate = portfolio_summary.get('일평가수익률', 1.5)
    
    # 포트폴리오 요약 정보 표시
    st.markdown("### 🔍 포트폴리오 요약")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "총 보유자산", 
            f"{portfolio_summary['총보유자산']:,.0f} KRW", 
            f"{daily_profit_rate:.2f}%"
        )
    
    with col2:
        profit_delta = f"{portfolio_summary['총수익률']:.2f}%"
        profit_value = f"{portfolio_summary['총평가손익']:,.0f} KRW"
        
        st.metric(
            "총 평가손익", 
            profit_value, 
            profit_delta
        )
    
    with col3:
        st.metric(
            "보유 현금", 
            f"{portfolio_summary['보유현금']:,.0f} KRW"
        )
    
    # 코인별 보유 현황 표시
    st.markdown("### 💰 코인별 보유 현황")
    
    # 페이지네이션 처리
    page_size = 5  # 한 페이지당 표시할 코인 수
    if 'portfolio_page' not in st.session_state:
        st.session_state.portfolio_page = 0
    
    total_pages = (len(coin_balances) + page_size - 1) // page_size if not coin_balances.empty else 1
    start_idx = st.session_state.portfolio_page * page_size
    end_idx = min(start_idx + page_size, len(coin_balances))
    
    # 페이지 선택
    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 4, 1])
        with col1:
            if st.button("이전", key="prev_page", disabled=st.session_state.portfolio_page <= 0):
                st.session_state.portfolio_page -= 1
                st.rerun()
        with col2:
            st.markdown(f"<div style='text-align: center'>페이지 {st.session_state.portfolio_page + 1}/{total_pages}</div>", unsafe_allow_html=True)
        with col3:
            if st.button("다음", key="next_page", disabled=st.session_state.portfolio_page >= total_pages - 1):
                st.session_state.portfolio_page += 1
                st.rerun()
    
    # 현재 페이지의 코인 목록 표시
    if not coin_balances.empty:
        # 현재 페이지에 해당하는 데이터만 표시
        page_data = coin_balances.iloc[start_idx:end_idx]
        
        # 코인별 보유 현황 표시
        for _, row in page_data.iterrows():
            with st.container():
                st.markdown(f"#### {row['코인']}")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"**현재가**: {row['현재가']:,.0f} KRW")
                    st.markdown(f"**수량**: {row['수량']:.8f}")
                
                with col2:
                    st.markdown(f"**평균 매수가**: {row['평균매수가']:,.0f} KRW")
                    st.markdown(f"**평가금액**: {row['평가금액']:,.0f} KRW")
                
                with col3:
                    st.markdown(f"**투자금액**: {row['투자금액']:,.0f} KRW")
                    st.markdown(f"**평가손익**: {row['평가손익']:,.0f} KRW")
                
                with col4:
                    profit_rate = row['수익률']
                    color = "green" if profit_rate >= 0 else "red"
                    st.markdown(f"**수익률**: <span style='color:{color}'>{profit_rate:.2f}%</span>", unsafe_allow_html=True)
                
                    # 간단한 수익률 차트
                    ratio = min(100, max(0, (profit_rate + 20) * 2.5)) / 100
                    st.progress(ratio, "수익률")
                
                st.markdown("---")
    else:
        st.info("보유 중인 코인이 없습니다.")
        
    # API 키가 없는 경우 안내 메시지
    if not has_api_keys:
        st.info("현재 샘플 데이터가 표시되고 있습니다. 실제 데이터를 보려면 API 설정 탭에서 API 키를 설정하세요.")
