import streamlit as st
import pyupbit
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from typing import Optional, Dict, List, Tuple, Any
import sys
sys.path.append("tools/upbit")
from UPBIT import Trade

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
def get_market_info():
    """모든 암호화폐 시장 정보 조회"""
    try:
        tickers = pyupbit.get_tickers(fiat="KRW")
        all_market_info = []
        
        for ticker in tickers:
            try:
                # 현재가 정보
                ticker_price = pyupbit.get_current_price(ticker)
                if not ticker_price:
                    continue
                    
                # 일봉 데이터
                df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
                if df is None or df.empty:
                    continue
                    
                # 전일 종가, 전일 대비 등락률
                prev_close = df.iloc[0]['close']
                change_rate = (ticker_price - prev_close) / prev_close * 100
                
                # 거래량 정보
                today_volume = df.iloc[-1]['volume'] if 'volume' in df.columns else 0
                today_value = today_volume * ticker_price
                
                # 코인 이름 (티커에서 KRW- 제거)
                coin_name = ticker.replace("KRW-", "")
                
                all_market_info.append({
                    '코인': coin_name,
                    '현재가': ticker_price,
                    '전일종가': prev_close,
                    '변동률': change_rate,
                    '거래량': today_volume,
                    '거래대금': today_value
                })
            except Exception as e:
                # 개별 코인 처리 실패시 건너뛰기
                continue
        
        if not all_market_info:
            raise Exception("시장 정보를 가져올 수 없습니다.")
        
        return pd.DataFrame(all_market_info)
    except Exception as e:
        st.error(f"시장 정보 조회 중 오류 발생: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=300)  # 5분 캐시
def get_coin_chart_data(coin_ticker: str, interval: str = "minute60", count: int = 168):
    """코인의 차트 데이터 조회"""
    try:
        df = pyupbit.get_ohlcv(coin_ticker, interval=interval, count=count)
        if df is None or df.empty:
            st.warning(f"{coin_ticker}의 차트 데이터를 가져올 수 없습니다.")
            return pd.DataFrame()
        return df
    except Exception as e:
        st.error(f"차트 데이터 조회 중 오류 발생: {str(e)}")
        return pd.DataFrame()

def draw_price_chart(df: pd.DataFrame, coin_name: str):
    """가격 차트 그리기"""
    if df.empty:
        st.error("차트 데이터가 없습니다.")
        return
        
    try:
        fig = go.Figure()
        
        # 캔들스틱 차트
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=coin_name,
            increasing_line_color='red',   # 상승 빨간색
            decreasing_line_color='blue'   # 하락 파란색
        ))
        
        # 차트 레이아웃 설정
        fig.update_layout(
            title=f"{coin_name} 가격 차트",
            xaxis_title="날짜",
            yaxis_title="가격 (KRW)",
            height=500,
            template="plotly_white",
            xaxis_rangeslider_visible=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"차트 그리기 중 오류 발생: {str(e)}")
        return

def execute_order(upbit, coin_ticker, trade_type, amount, amount_type, current_price=None):
    """주문 실행"""
    try:
        if amount <= 0:
            st.error("금액 또는 수량은 0보다 커야 합니다.")
            return None
            
        # 매수 주문
        if trade_type == "매수":
            if amount_type == "KRW":
                # 금액 기준 시장가 매수
                return upbit.buy_market_order(coin_ticker, amount)
            else:
                # 수량 기준 시장가 매수 (수량 * 현재가)
                return upbit.buy_market_order(coin_ticker, amount * current_price)
        # 매도 주문
        else:
            if amount_type == "KRW":
                # 금액 기준 시장가 매도 (금액 / 현재가)
                return upbit.sell_market_order(coin_ticker, amount / current_price)
            else:
                # 수량 기준 시장가 매도
                return upbit.sell_market_order(coin_ticker, amount)
    except Exception as e:
        st.error(f"주문 실행 중 오류 발생: {str(e)}")
        return None

@st.cache_data(ttl=60)  # 1분 캐시
def get_order_history():
    try:
        upbit = get_upbit_instance()
        if not upbit:
            return pd.DataFrame()
            
        try:
            # 임시 데이터 생성 (실제로는 이 부분을 거래소 API로 대체)
            orders = []
            if st.session_state.get("upbit_access_key") and st.session_state.get("upbit_secret_key"):
                # API 키가 있는 경우 Upbit 객체 사용
                # 주요 코인에 대한 미체결 주문 조회
                tickers = ["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-DOGE"]
                for ticker in tickers:
                    try:
                        # 미체결 주문 조회
                        wait_orders = upbit.get_order(ticker, state="wait")
                        if wait_orders:
                            orders.extend(wait_orders)
                    except Exception as e:
                        continue
            
            # 샘플 데이터 추가 (실제로는 제거)
            sample_orders = [
                {
                    'market': 'KRW-BTC',
                    'side': 'bid',
                    'price': 35000000,
                    'volume': 0.0005,
                    'created_at': '2023-03-01T12:30:45',
                    'state': 'done'
                },
                {
                    'market': 'KRW-ETH',
                    'side': 'bid',
                    'price': 2500000,
                    'volume': 0.01,
                    'created_at': '2023-03-02T10:15:30',
                    'state': 'done'
                }
            ]
            orders.extend(sample_orders)
            
            if not orders:
                return pd.DataFrame()
                
            # 데이터프레임 생성
            df = pd.DataFrame(orders)
            
            # 필요한 컬럼이 있는지 확인
            required_columns = ['market', 'side', 'price', 'volume', 'created_at', 'state']
            for col in required_columns:
                if col not in df.columns:
                    return pd.DataFrame()
            
            # 필요한 컬럼만 선택하고 이름 변경
            df = df[required_columns].rename(columns={
                'market': '코인',
                'side': '거래유형',
                'price': '가격',
                'volume': '수량',
                'created_at': '주문시간',
                'state': '상태'
            })
            
            # 거래유형 한글화
            df['거래유형'] = df['거래유형'].map({'bid': '매수', 'ask': '매도'})
            
            # 상태 한글화
            df['상태'] = df['상태'].map({'done': '완료', 'cancel': '취소', 'wait': '대기중'})
            
            # 시간 형식 변환
            df['주문시간'] = pd.to_datetime(df['주문시간'])
            
            # 최신순 정렬
            df = df.sort_values('주문시간', ascending=False)
            
            return df
        except Exception as e:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"주문 내역 조회 중 오류 발생: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=60)  # 1분 캐시
def get_important_coins():
    """주요 코인 및 주목할만한 코인 정보 조회"""
    try:
        # 주요 코인 리스트
        major_coins = ["BTC", "ETH", "XRP", "SOL", "DOGE", "ADA"]
        
        # 전체 코인 정보 조회
        market_info = get_market_info()
        if market_info.empty:
            return pd.DataFrame()
        
        # 주요 코인 필터링
        major_coin_info = market_info[market_info['코인'].isin(major_coins)].copy()
        
        # 주목할만한 코인 (변동률 상위 5개)
        notable_coins = market_info.sort_values('변동률', ascending=False).head(5)
        
        # 결과 합치기 (중복 제거)
        result = pd.concat([major_coin_info, notable_coins]).drop_duplicates().reset_index(drop=True)
        
        return result
    except Exception as e:
        st.error(f"주요 코인 정보 조회 중 오류 발생: {str(e)}")
        return pd.DataFrame()

def draw_candle_chart(df: pd.DataFrame, coin_name: str, interval: str = "day"):
    """캔들 차트 그리기 (일봉/월봉/년봉)"""
    if df.empty:
        st.error("차트 데이터가 없습니다.")
        return
        
    try:
        fig = go.Figure()
        
        # 캔들스틱 차트
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=coin_name,
            increasing_line_color='red',   # 상승 빨간색
            decreasing_line_color='blue'   # 하락 파란색
        ))
        
        # 이동평균선 추가
        if len(df) >= 5:
            ma5 = df['close'].rolling(window=5).mean()
            fig.add_trace(go.Scatter(x=df.index, y=ma5, mode='lines', name='5일 이동평균', line=dict(color='purple')))
        
        if len(df) >= 20:
            ma20 = df['close'].rolling(window=20).mean()
            fig.add_trace(go.Scatter(x=df.index, y=ma20, mode='lines', name='20일 이동평균', line=dict(color='orange')))
        
        # 차트 레이아웃 설정
        interval_text = "일별" if interval == "day" else "월별" if interval == "month" else "년별"
        fig.update_layout(
            title=f"{coin_name} {interval_text} 가격 차트",
            xaxis_title="날짜",
            yaxis_title="가격 (KRW)",
            height=500,
            template="plotly_white",
            xaxis_rangeslider_visible=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"차트 그리기 중 오류 발생: {str(e)}")
        return

def show_coin_details(upbit_trade, coin_ticker: str):
    """코인 상세 정보 표시"""
    try:
        # 코인 이름 추출
        coin_name = coin_ticker.split('-')[1]
        
        # 현재가 조회
        current_price = upbit_trade.get_current_price(coin_ticker)
        if not current_price:
            st.error(f"{coin_name} 현재가 조회 실패")
            return
        
        # 계좌 잔고 조회
        krw_balance = upbit_trade.get_balance("KRW")
        coin_balance = upbit_trade.get_balance(coin_name)
        
        # UI 구성
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("현재가", f"{current_price:,} KRW")
        
        with col2:
            st.metric("매수 가능 금액", f"{krw_balance:,} KRW")
        
        with col3:
            st.metric("보유량", f"{coin_balance:,} {coin_name}")
        
        # 차트 기간 선택
        chart_interval = st.radio(
            "차트 기간",
            options=["일봉", "주봉", "월봉"],
            horizontal=True,
            key=f"{coin_name}_chart_interval"
        )
        
        # 선택된 기간에 따라 차트 데이터 조회
        interval_map = {
            "일봉": "day",
            "주봉": "week",
            "월봉": "month"
        }
        
        interval = interval_map.get(chart_interval, "day")
        chart_data = pyupbit.get_ohlcv(coin_ticker, interval=interval, count=30)
        
        # 차트 그리기
        draw_candle_chart(chart_data, coin_name, interval)
        
        # 매수/매도 UI
        st.markdown("### 거래하기")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("매수")
            buy_amount = st.number_input(
                "매수 금액 (KRW)",
                min_value=5000,  # 최소 주문 금액
                max_value=int(krw_balance),
                value=5000,
                step=1000,
                key=f"{coin_name}_buy_amount"
            )
            
            # 수수료 계산 (0.05%)
            fee = buy_amount * 0.0005
            expected_quantity = (buy_amount - fee) / current_price
            
            st.info(f"예상 수수료: {fee:,.0f} KRW")
            st.info(f"예상 매수 수량: {expected_quantity:,.8f} {coin_name}")
            
            if st.button("매수 주문", key=f"{coin_name}_buy_button"):
                result = upbit_trade.buy_market_order(coin_ticker, buy_amount)
                if result:
                    st.success(f"매수 주문이 접수되었습니다. 주문번호: {result.get('uuid', '알 수 없음')}")
                else:
                    st.error("매수 주문 실패")
        
        with col2:
            st.subheader("매도")
            sell_percentage = st.slider(
                "매도 비율",
                min_value=1,
                max_value=100,
                value=100,
                step=1,
                key=f"{coin_name}_sell_percentage"
            )
            
            sell_quantity = coin_balance * (sell_percentage / 100)
            expected_amount = sell_quantity * current_price
            fee = expected_amount * 0.0005
            
            st.info(f"매도 수량: {sell_quantity:,.8f} {coin_name}")
            st.info(f"예상 매도 금액: {expected_amount:,.0f} KRW")
            st.info(f"예상 수수료: {fee:,.0f} KRW")
            
            if st.button("매도 주문", key=f"{coin_name}_sell_button"):
                if coin_balance <= 0:
                    st.error(f"{coin_name}을(를) 보유하고 있지 않습니다.")
                else:
                    result = upbit_trade.sell_market_order(coin_ticker, sell_quantity)
                    if result:
                        st.success(f"매도 주문이 접수되었습니다. 주문번호: {result.get('uuid', '알 수 없음')}")
                    else:
                        st.error("매도 주문 실패")
    
    except Exception as e:
        st.error(f"코인 상세 정보 표시 중 오류 발생: {str(e)}")

def show_trade_market():
    st.title("📊 실시간 거래소")
    
    # API 키 확인
    if not st.session_state.get("upbit_access_key") or not st.session_state.get("upbit_secret_key"):
        st.warning("API 키가 설정되지 않았습니다. API 설정 페이지에서 API 키를 입력해주세요.")
        st.info("현재 데모 모드로 동작 중입니다. 실제 거래를 위해서는 API 키를 설정해주세요.")
    
    # Upbit Trade 인스턴스 생성
    upbit_trade = get_upbit_trade_instance()
    if not upbit_trade and st.session_state.get("upbit_access_key"):
        return
        
    # 주요 코인 및 주목할만한 코인 표시
    st.markdown("### 💰 주요 코인 및 주목할만한 코인")
    important_coins = get_important_coins()
    
    if not important_coins.empty:
        st.dataframe(
            important_coins.style.format({
                '현재가': '{:,.0f}',
                '전일종가': '{:,.0f}',
                '변동률': '{:+.2f}%',
                '거래량': '{:,.0f}',
                '거래대금': '{:,.0f}'
            }),
            use_container_width=True,
            height=300
        )
    else:
        st.error("코인 정보를 불러오지 못했습니다.")
        return
    
    # 코인 선택
    selected_coin = st.selectbox(
        "코인 선택",
        options=["KRW-" + coin for coin in important_coins['코인']],
        format_func=lambda x: f"{x.split('-')[1]} ({x})",
        key="selected_coin"
    )
    
    if selected_coin:
        st.markdown(f"### 📈 {selected_coin.split('-')[1]} 상세 정보")
        show_coin_details(upbit_trade, selected_coin)
