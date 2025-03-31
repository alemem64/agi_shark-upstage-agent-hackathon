import streamlit as st
import pyupbit
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from typing import Optional, Dict, List, Tuple, Any

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

def show_trade_market():
    try:
        st.title("거래 시장")
        
        # API 키 확인
        if not st.session_state.get("upbit_access_key") or not st.session_state.get("upbit_secret_key"):
            st.warning("API 키가 설정되지 않았습니다. API 설정 페이지에서 API 키를 입력해주세요.")
            return
            
        # 새로고침 버튼
        if st.button("🔄 새로고침", key="trading_market_refresh"):
            st.cache_data.clear()
            st.rerun()
            
        # 시장 정보 조회
        market_info = get_market_info()
        
        if market_info.empty:
            st.error("시장 정보를 불러오지 못했습니다.")
            return
            
        # 정렬 옵션
        col1, col2 = st.columns(2)
        with col1:
            sort_by = st.selectbox(
                "정렬 기준",
                ["가격", "변동률", "거래량", "거래대금"],
                key="sort_by_option"
            )
        with col2:
            sort_order = st.selectbox(
                "정렬 순서",
                ["오름차순", "내림차순"],
                key="sort_order_option"
            )
        
        # 정렬 기준 매핑
        sort_columns = {
            "가격": "현재가",
            "변동률": "변동률",
            "거래량": "거래량",
            "거래대금": "거래대금"
        }
        
        # 정렬 적용
        sorted_df = market_info.sort_values(
            by=sort_columns[sort_by],
            ascending=(sort_order == "오름차순")
        )
        
        # 거래 가능 리스트
        st.markdown("### 💹 거래 가능 코인 리스트")
        
        # 코인 리스트 표시
        st.dataframe(
            sorted_df,
            use_container_width=True,
            column_config={
                "코인": st.column_config.TextColumn(
                    "코인",
                    width="medium"
                ),
                "현재가": st.column_config.NumberColumn(
                    "현재가",
                    format="%.0f",
                    width="medium"
                ),
                "변동률": st.column_config.NumberColumn(
                    "변동률",
                    format="%.2f%%",
                    width="medium"
                ),
                "거래량": st.column_config.NumberColumn(
                    "거래량",
                    format="%.0f",
                    width="medium"
                ),
                "거래대금": st.column_config.NumberColumn(
                    "거래대금",
                    format="%.0f",
                    width="medium"
                )
            },
            height=300
        )
        
        # 구분선
        st.markdown("---")
        
        # 개별 코인 거래 섹션
        st.markdown("### 🔄 코인 거래")
        
        # 코인 선택
        selected_coin = st.selectbox(
            "코인 선택",
            sorted_df['코인'].tolist(),
            key="coin_select"
        )
        
        if selected_coin:
            # 코인 정보
            coin_info = sorted_df[sorted_df['코인'] == selected_coin].iloc[0]
            coin_ticker = f"KRW-{selected_coin}"
            current_price = coin_info['현재가']
            
            # 코인 정보 표시
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "현재가",
                    f"{int(current_price):,}원",
                    f"{coin_info['변동률']:.2f}%"
                )
            with col2:
                st.metric(
                    "거래량",
                    f"{int(coin_info['거래량']):,}"
                )
            with col3:
                st.metric(
                    "거래대금",
                    f"{int(coin_info['거래대금']):,}원"
                )
            
            # 차트 기간 선택
            chart_period = st.selectbox(
                "차트 기간",
                ["1시간", "일봉", "주봉", "월봉"],
                key="chart_period"
            )
            
            # 기간에 따른 차트 데이터 조회
            period_mapping = {
                "1시간": ("minute60", 168),    # 1시간 * 168 = 1주
                "일봉": ("day", 30),           # 일봉 * 30 = 1달
                "주봉": ("week", 12),          # 주봉 * 12 = 3달
                "월봉": ("month", 12)          # 월봉 * 12 = 1년
            }
            
            interval, count = period_mapping[chart_period]
            chart_data = get_coin_chart_data(coin_ticker, interval, count)
            
            # 차트 표시
            draw_price_chart(chart_data, selected_coin)
            
            # 구분선
            st.markdown("---")
            
            # 매수/매도 섹션
            st.markdown("### 💰 매수/매도")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # 거래 유형 선택
                trade_type = st.radio(
                    "거래 유형",
                    ["매수", "매도"],
                    key="trade_type"
                )
                
                # 금액/수량 유형 선택
                amount_type = st.radio(
                    "금액/수량",
                    ["KRW", "코인"],
                    key="amount_type"
                )
                
            with col2:
                # 금액/수량 입력
                if amount_type == "KRW":
                    amount = st.number_input(
                        "금액 (KRW)",
                        min_value=0,
                        step=1000,
                        format="%d",
                        key="amount_input"
                    )
                    if amount > 0:
                        estimated_amount = amount / current_price
                        st.info(f"예상 {selected_coin} 수량: {estimated_amount:.8f}")
                else:
                    amount = st.number_input(
                        f"수량 ({selected_coin})",
                        min_value=0.0,
                        step=0.0001,
                        format="%.8f",
                        key="amount_input"
                    )
                    if amount > 0:
                        estimated_amount = amount * current_price
                        st.info(f"예상 금액: {estimated_amount:,.0f} KRW")
                
                # 거래 실행 버튼
                if st.button("거래 실행", type="primary", key="execute_trade"):
                    try:
                        upbit = get_upbit_instance()
                        if not upbit:
                            return
                            
                        order = execute_order(upbit, coin_ticker, trade_type, amount, amount_type, current_price)
                        
                        if order:
                            st.success(f"{selected_coin} 주문이 접수되었습니다.")
                            # 주문 상태 모니터링
                            with st.spinner("주문 체결 대기 중..."):
                                for _ in range(10):  # 최대 10번 체크
                                    time.sleep(1)
                                    try:
                                        # 주문 상태 확인 (주문 UUID 필요)
                                        if 'uuid' in order:
                                            order_status = upbit.get_order(order['uuid'])
                                            if order_status['state'] == 'done':
                                                st.success("주문이 체결되었습니다!")
                                                break
                                            elif order_status['state'] == 'cancel':
                                                st.error("주문이 취소되었습니다.")
                                                break
                                    except Exception as e:
                                        st.error(f"주문 상태 확인 중 오류: {str(e)}")
                                        break
                    except Exception as e:
                        st.error(f"거래 실행 중 오류 발생: {str(e)}")
            
            # 구분선
            st.markdown("---")
            
            # 거래 내역 섹션
            st.markdown("### 📜 최근 거래 내역")
            order_history = get_order_history()
            
            if not order_history.empty:
                # 해당 코인의 거래 내역만 필터링
                coin_orders = order_history[order_history['코인'] == coin_ticker]
                
                if not coin_orders.empty:
                    st.dataframe(
                        coin_orders,
                        use_container_width=True
                    )
                else:
                    st.info(f"{selected_coin}의 거래 내역이 없습니다.")
            else:
                st.info("거래 내역이 없습니다.")
            
    except Exception as e:
        st.error(f"거래 시장 페이지 로딩 중 오류 발생: {str(e)}")
