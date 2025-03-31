import streamlit as st
import pyupbit
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime

# 스타일 설정
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stMetric {
        background-color: #1E1E1E;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem;
    }
    .stMetric:hover {
        background-color: #2D2D2D;
    }
    .stDataFrame {
        background-color: #1E1E1E;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .stSelectbox, .stRadio {
        background-color: #1E1E1E;
        padding: 0.5rem;
        border-radius: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

def format_number(number: float) -> str:
    """숫자를 천 단위 구분자와 함께 포맷팅"""
    return f"{number:,.0f}"

def get_order_history(upbit: pyupbit.Upbit) -> Optional[List[Dict]]:
    """주문 내역 조회"""
    try:
        # 모든 주문 내역 조회
        orders = upbit.get_order("")
        if not orders:
            return []
            
        # orders가 리스트가 아닌 경우 리스트로 변환
        if not isinstance(orders, list):
            orders = [orders]
            
        # 완료된 주문만 필터링
        completed_orders = [order for order in orders if order.get('state') == 'done']
        return completed_orders
    except Exception as e:
        st.error(f"주문 내역 조회 실패: {e}")
        return None

def process_order_data(orders: List[Dict]) -> List[Dict]:
    """주문 데이터 처리"""
    processed_orders = []
    for order in orders:
        processed_orders.append({
            "주문시간": datetime.fromtimestamp(order['created_at']).strftime('%Y-%m-%d %H:%M:%S'),
            "코인": order['market'].replace("KRW-", ""),
            "주문유형": "매수" if order['side'] == 'bid' else "매도",
            "주문가격": format_number(float(order['price'])),
            "주문수량": format_number(float(order['volume'])),
            "주문금액": format_number(float(order['price']) * float(order['volume'])),
            "수수료": format_number(float(order['paid_fee'])),
            "상태": "완료"
        })
    return processed_orders

def show_trade_history():
    st.title("📈 거래 내역")
    
    # API 키 확인
    if not st.session_state.get('upbit_access_key') or not st.session_state.get('upbit_secret_key'):
        st.warning("API 키를 설정해주세요.")
        return
        
    # Upbit 객체 생성
    upbit = pyupbit.Upbit(st.session_state.upbit_access_key, st.session_state.upbit_secret_key)
    
    # 주문 내역 조회
    orders = get_order_history(upbit)
    if orders is None:
        return
        
    # 주문 데이터 처리
    processed_orders = process_order_data(orders)
    
    if not processed_orders:
        st.info("거래 내역이 없습니다.")
        return
        
    # DataFrame 생성
    df = pd.DataFrame(processed_orders)
    
    # 주문 요약 정보 표시
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("총 주문수", len(processed_orders))
    with col2:
        buy_count = len([o for o in processed_orders if o['주문유형'] == '매수'])
        sell_count = len([o for o in processed_orders if o['주문유형'] == '매도'])
        st.metric("매수/매도 비율", f"{buy_count}/{sell_count}")
    with col3:
        total_fee = sum(float(o['수수료'].replace(',', '')) for o in processed_orders)
        st.metric("총 수수료", format_number(total_fee))
    
    # 필터링 옵션
    col1, col2 = st.columns(2)
    with col1:
        selected_coins = st.multiselect(
            "코인 필터",
            options=sorted(df['코인'].unique()),
            default=[]
        )
    with col2:
        selected_types = st.multiselect(
            "주문유형 필터",
            options=sorted(df['주문유형'].unique()),
            default=[]
        )
    
    # 필터링 적용
    if selected_coins:
        df = df[df['코인'].isin(selected_coins)]
    if selected_types:
        df = df[df['주문유형'].isin(selected_types)]
    
    # 정렬 옵션
    sort_by = st.selectbox(
        "정렬 기준",
        ["주문시간", "코인", "주문유형", "주문가격", "주문수량", "주문금액", "수수료"]
    )
    
    # 정렬 방향
    sort_order = st.radio("정렬 방향", ["오름차순", "내림차순"])
    
    # 정렬 적용
    if sort_order == "오름차순":
        df = df.sort_values(by=sort_by)
    else:
        df = df.sort_values(by=sort_by, ascending=False)
    
    # 데이터 표시
    st.dataframe(df, use_container_width=True)
