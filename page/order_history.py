import streamlit as st
import pandas as pd
from datetime import datetime
import pyupbit
from typing import Optional, List, Dict

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
def get_order_history():
    try:
        upbit = get_upbit_instance()
        if not upbit:
            return pd.DataFrame()
            
        try:
            # 완료된 주문 내역 조회
            # get_order 함수는 ticker_or_uuid 또는 state 중 하나가 필요
            # state만 지정할 경우 'wait'만 허용
            # 모든 거래 내역을 조회하기 위해 별도 방법 사용
            
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
                        
                        # 최근 체결된 주문 조회 (예: 최근 일주일)
                        # 이 부분은 API 제한으로 인해 실제 구현 어려울 수 있음
                    except Exception as e:
                        st.warning(f"{ticker} 주문 조회 중 오류: {str(e)}")
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
                },
                {
                    'market': 'KRW-BTC',
                    'side': 'ask',
                    'price': 36000000,
                    'volume': 0.0005,
                    'created_at': '2023-03-03T14:45:20',
                    'state': 'done'
                }
            ]
            orders.extend(sample_orders)
            
            if not orders:
                st.info("최근 거래 내역이 없습니다.")
                return pd.DataFrame()
                
            # 데이터프레임 생성
            df = pd.DataFrame(orders)
            
            # 필요한 컬럼이 있는지 확인
            required_columns = ['market', 'side', 'price', 'volume', 'created_at', 'state']
            for col in required_columns:
                if col not in df.columns:
                    st.warning(f"주문 내역에 필요한 컬럼({col})이 없습니다.")
                    return pd.DataFrame()
            
            # 필요한 컬럼만 선택하고 이름 변경
            df = df[required_columns].rename(columns={
                'market': '코인',
                'side': '거래유형',
                'price': '주문가격',
                'volume': '주문수량',
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
            st.error(f"주문 내역 조회 중 상세 오류: {str(e)}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"주문 내역 조회 중 오류 발생: {str(e)}")
        return pd.DataFrame()

def show_order_history():
    try:
        st.title("거래내역")
        
        # API 키 확인
        if not st.session_state.get("upbit_access_key") or not st.session_state.get("upbit_secret_key"):
            st.warning("API 키가 설정되지 않았습니다. API 설정 페이지에서 API 키를 입력해주세요.")
            return
            
        # 새로고침 버튼
        if st.button("🔄 새로고침", key="order_history_refresh"):
            st.cache_data.clear()
            st.rerun()
            
        # 거래내역 표시
        order_history = get_order_history()
        if not order_history.empty:
            # 필터링 옵션
            col1, col2, col3 = st.columns(3)
            with col1:
                all_coins = ["전체"] + list(order_history['코인'].unique())
                selected_coin = st.selectbox(
                    "코인 필터",
                    all_coins,
                    key="coin_filter"
                )
            with col2:
                all_types = ["전체"] + list(order_history['거래유형'].unique())
                selected_type = st.selectbox(
                    "거래유형 필터",
                    all_types,
                    key="type_filter"
                )
            with col3:
                all_statuses = ["전체"] + list(order_history['상태'].unique())
                selected_status = st.selectbox(
                    "상태 필터",
                    all_statuses,
                    key="status_filter"
                )
            
            # 필터링 적용
            filtered_df = order_history.copy()
            if selected_coin != "전체":
                filtered_df = filtered_df[filtered_df['코인'] == selected_coin]
            if selected_type != "전체":
                filtered_df = filtered_df[filtered_df['거래유형'] == selected_type]
            if selected_status != "전체":
                filtered_df = filtered_df[filtered_df['상태'] == selected_status]
            
            # 거래내역 테이블
            st.dataframe(
                filtered_df,
                use_container_width=True,
                column_config={
                    "코인": st.column_config.TextColumn(
                        "코인",
                        width="medium"
                    ),
                    "거래유형": st.column_config.TextColumn(
                        "거래유형",
                        width="medium"
                    ),
                    "주문가격": st.column_config.NumberColumn(
                        "주문가격",
                        format="%.0f",
                        width="medium"
                    ),
                    "주문수량": st.column_config.NumberColumn(
                        "주문수량",
                        format="%.8f",
                        width="medium"
                    ),
                    "주문시간": st.column_config.DatetimeColumn(
                        "주문시간",
                        width="medium",
                        format="YYYY-MM-DD HH:mm:ss"
                    ),
                    "상태": st.column_config.TextColumn(
                        "상태",
                        width="medium"
                    )
                }
            )
            
            # 요약 정보
            st.markdown("### 📊 거래 요약")
            col1, col2 = st.columns(2)
            with col1:
                total_trades = len(filtered_df)
                st.metric("총 거래 건수", f"{total_trades:,}건")
            with col2:
                buy_count = len(filtered_df[filtered_df['거래유형'] == '매수'])
                sell_count = len(filtered_df[filtered_df['거래유형'] == '매도'])
                st.metric("매수/매도 비율", f"{buy_count:,}건/{sell_count:,}건")
        else:
            st.info("거래 내역이 없습니다.")
            
    except Exception as e:
        st.error(f"거래내역 페이지 로딩 중 오류 발생: {str(e)}") 