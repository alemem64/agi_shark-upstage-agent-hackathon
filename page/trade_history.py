import streamlit as st
import pyupbit
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import sys
sys.path.append("tools/upbit")
from UPBIT import Trade
from page.api_setting import check_api_keys, get_upbit_trade_instance

# 스타일 설정 - 최소화하여 렌더링 성능 향상
st.markdown("""
    <style>
    .stMetric {
        background-color: #1E1E1E;
        padding: 0.75rem;
        border-radius: 0.5rem;
        margin: 0.25rem;
    }
    </style>
""", unsafe_allow_html=True)

def format_number(number: float) -> str:
    """숫자를 천 단위 구분자와 함께 포맷팅"""
    return f"{number:,.0f}"

def format_date(date_string: str) -> str:
    """날짜 포맷팅"""
    try:
        dt = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%f%z")
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        try:
            dt = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S%z")
            return dt.strftime("%Y-%m-%d %H:%M")
        except:
            return date_string

@st.cache_data(ttl=300)  # 5분 캐시로 증가
def get_order_history_from_trade(upbit_trade) -> pd.DataFrame:
    """주문 내역 조회"""
    try:
        # 최종 주문 내역 리스트
        orders = []
        
        # 실제 거래소에서 데이터 가져오기 시도
        if upbit_trade:
            try:
                # 방법 1: 전체 주문 내역 조회 시도
                all_orders = upbit_trade.upbit.get_order("", state="done", limit=100)
                if all_orders:
                    if isinstance(all_orders, list):
                        orders.extend(all_orders)
                    elif isinstance(all_orders, dict):
                        orders.append(all_orders)
            except Exception as e:
                # 방법 2: 주요 코인만 개별 조회 시도 (속도 향상)
                try:
                    # 주요 코인만 조회 (모든 코인을 조회하면 속도가 느려짐)
                    major_tickers = ["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-SOL", "KRW-DOGE", "KRW-ADA"]
                    
                    for ticker in major_tickers:
                        try:
                            # 해당 코인의 완료된 주문 내역 가져오기
                            coin_orders = upbit_trade.upbit.get_order(ticker, state="done")
                            if coin_orders:
                                if isinstance(coin_orders, list):
                                    orders.extend(coin_orders)
                                elif isinstance(coin_orders, dict):
                                    orders.append(coin_orders)
                        except:
                            continue
                except Exception as e:
                    pass
        
        # API 키가 설정되지 않았거나 실제 주문이 없는 경우를 위한 샘플 데이터
        if not orders:
            # 더미 데이터 추가 (최근 10일간의 샘플 거래 내역)
            today = datetime.now()
            sample_coins = ["BTC", "ETH", "XRP", "DOGE", "ADA"]
            
            for i in range(20):  # 더 많은 데이터 포인트 생성 (페이징 테스트)
                order_date = today - timedelta(days=i//2)
                date_str = order_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")
                
                # 매수 주문 추가
                if i % 3 != 0:  # 일부 날짜만 매수 주문 추가
                    coin = sample_coins[i % len(sample_coins)]
                    price = 50000000 if coin == "BTC" else 3000000 if coin == "ETH" else 500
                    volume = 0.001 if coin == "BTC" else 0.01 if coin == "ETH" else 100
                    
                    orders.append({
                        'market': f'KRW-{coin}',
                        'side': 'bid',
                        'price': price,
                        'volume': volume,
                        'executed_volume': volume,
                        'paid_fee': price * volume * 0.0005,
                        'created_at': date_str,
                        'state': 'done'
                    })
                
                # 매도 주문 추가
                if i % 4 != 0:  # 일부 날짜만 매도 주문 추가
                    coin = sample_coins[(i+2) % len(sample_coins)]
                    price = 51000000 if coin == "BTC" else 3100000 if coin == "ETH" else 520
                    volume = 0.001 if coin == "BTC" else 0.01 if coin == "ETH" else 50
                    
                    orders.append({
                        'market': f'KRW-{coin}',
                        'side': 'ask',
                        'price': price,
                        'volume': volume,
                        'executed_volume': volume,
                        'paid_fee': price * volume * 0.0005,
                        'created_at': date_str,
                        'state': 'done'
                    })
        
        # 주문 데이터 처리
        processed_orders = []
        for order in orders:
            try:
                # 필수 필드가 있는지 확인
                market = order.get('market', '')
                if not market:
                    continue
                    
                side = order.get('side', '')
                if not side:
                    continue
                    
                # 숫자 데이터 안전하게 변환
                try:
                    price = float(order.get('price', 0))
                    volume = float(order.get('volume', 0))
                    executed_volume = float(order.get('executed_volume', 0)) if 'executed_volume' in order else 0
                    paid_fee = float(order.get('paid_fee', 0))
                except (ValueError, TypeError):
                    # 숫자 변환 실패 시 기본값 사용
                    price = 0
                    volume = 0
                    executed_volume = 0
                    paid_fee = 0
                    
                created_at = order.get('created_at', '')
                state = order.get('state', 'done')
                
                # 유효한 데이터만 추가
                if price > 0 and (volume > 0 or executed_volume > 0):
                    actual_volume = executed_volume if executed_volume > 0 else volume
                    actual_amount = price * actual_volume
                    
                    processed_orders.append({
                        "주문시간": format_datetime(created_at),
                        "코인": market.replace("KRW-", ""),
                        "주문유형": "매수" if side == 'bid' else "매도",
                        "주문가격": price,
                        "주문수량": actual_volume,
                        "주문금액": actual_amount,
                        "수수료": paid_fee,
                        "상태": "완료" if state == 'done' else "대기" if state == 'wait' else "취소"
                    })
            except Exception as e:
                continue
                
        # 데이터프레임으로 변환
        df = pd.DataFrame(processed_orders)
        
        # 데이터가 없으면 빈 데이터프레임 반환
        if df.empty:
            return pd.DataFrame(columns=["주문시간", "코인", "주문유형", "주문가격", "주문수량", "주문금액", "수수료", "상태"])
            
        # 최신순 정렬
        return df.sort_values('주문시간', ascending=False)
        
    except Exception as e:
        # 오류 발생시 빈 데이터프레임 반환
        return pd.DataFrame(columns=["주문시간", "코인", "주문유형", "주문가격", "주문수량", "주문금액", "수수료", "상태"])

def format_datetime(dt_str):
    """ISO 형식의 날짜 문자열을 가독성 있는 형식으로 변환"""
    try:
        # 다양한 날짜 형식 처리
        try:
            dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S%z')
        except:
            try:
                dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S.%f%z')
            except:
                dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S')
        
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return dt_str

def process_order_data_from_trade(orders: List[Dict]) -> List[Dict]:
    """주문 데이터 처리"""
    if not orders:
        return []
        
    processed_orders = []
    for order in orders:
        try:
            # 필수 필드가 있는지 확인
            market = order.get('market', '')
            if not market:
                continue
                
            side = order.get('side', '')
            if not side:
                continue
                
            # 숫자 데이터 안전하게 변환
            try:
                price = float(order.get('price', 0))
                volume = float(order.get('volume', 0))
                executed_volume = float(order.get('executed_volume', 0)) if 'executed_volume' in order else 0
                paid_fee = float(order.get('paid_fee', 0))
            except (ValueError, TypeError):
                # 숫자 변환 실패 시 기본값 사용
                price = 0
                volume = 0
                executed_volume = 0
                paid_fee = 0
                
            created_at = order.get('created_at', '')
            
            # 유효한 데이터만 추가
            if price > 0 and (volume > 0 or executed_volume > 0):
                actual_volume = executed_volume if executed_volume > 0 else volume
                actual_amount = price * actual_volume
                
                processed_orders.append({
                    "주문시간": format_datetime(created_at),
                    "코인": market.replace("KRW-", ""),
                    "주문유형": "매수" if side == 'bid' else "매도",
                    "주문가격": price,
                    "주문수량": actual_volume,
                    "주문금액": actual_amount,
                    "수수료": paid_fee,
                    "상태": "완료"
                })
        except Exception as e:
            continue
            
    return processed_orders

def show_trade_history():
    """거래 내역 화면 표시"""
    st.title("📝 거래 내역")
    
    # API 키 확인
    has_api_keys = check_api_keys()
    
    # Upbit Trade 인스턴스 생성
    upbit_trade = get_upbit_trade_instance()
    
    # 새로고침 버튼
    if st.button("🔄 새로고침", key="history_refresh"):
        st.cache_data.clear()
        st.rerun()
    
    # 주문 내역 가져오기
    orders_df = get_order_history_from_trade(upbit_trade)
    
    if not orders_df.empty:
        # 필터링 옵션
        st.markdown("### 🔍 필터 옵션")
        col1, col2 = st.columns(2)
        
        with col1:
            order_status = st.selectbox(
                "주문 상태",
                options=["전체", "완료", "대기", "취소"],
                key="order_status"
            )
        
        with col2:
            order_type = st.selectbox(
                "주문 유형",
                options=["전체", "매수", "매도"],
                key="order_type"
            )
            
        # 필터링 적용
        if order_status != "전체":
            orders_df = orders_df[orders_df["상태"] == order_status]
            
        if order_type != "전체":
            orders_df = orders_df[orders_df["주문유형"] == order_type]
        
        # 정렬 옵션
        sort_col = st.selectbox(
            "정렬 기준",
            options=["주문시간", "코인", "주문금액"],
            key="sort_col"
        )
        
        sort_order = st.radio(
            "정렬 순서",
            options=["내림차순", "오름차순"],
            horizontal=True,
            key="sort_order"
        )
        
        # 정렬 적용
        ascending = sort_order == "오름차순"
        orders_df = orders_df.sort_values(by=sort_col, ascending=ascending)
        
        # 페이지네이션
        orders_per_page = 5
        
        if 'history_page' not in st.session_state:
            st.session_state.history_page = 0
            
        total_pages = max(1, (len(orders_df) + orders_per_page - 1) // orders_per_page)
        
        # 현재 페이지가 유효한지 확인
        if st.session_state.history_page >= total_pages:
            st.session_state.history_page = 0
            
        # 현재 페이지에 해당하는 주문 필터링
        start_idx = st.session_state.history_page * orders_per_page
        end_idx = min(start_idx + orders_per_page, len(orders_df))
        
        # 데이터프레임이 비어있지 않은지 확인
        if len(orders_df) > 0:
            current_orders = orders_df.iloc[start_idx:end_idx]
            
            # 거래 내역 표시
            st.markdown("### 📋 거래 내역")
            
            # 각 거래 카드로 표시
            for _, order in current_orders.iterrows():
                with st.container():
                    # 배경색 설정
                    if order["주문유형"] == "매수":
                        st.markdown("""
                            <div style="background-color: rgba(255, 240, 240, 0.3); padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                        """, unsafe_allow_html=True)
                    else:  # 매도
                        st.markdown("""
                            <div style="background-color: rgba(240, 240, 255, 0.3); padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                        """, unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.markdown(f"**코인**: {order['코인']}")
                        st.markdown(f"**주문시간**: {order['주문시간']}")
                        
                    with col2:
                        order_type_text = order["주문유형"]
                        order_type_color = "red" if order["주문유형"] == "매수" else "blue"
                        st.markdown(f"**주문유형**: <span style='color:{order_type_color}'>{order_type_text}</span>", unsafe_allow_html=True)
                        
                        status_text = order["상태"]
                        status_color = "green" if status_text == "완료" else "orange" if status_text == "대기" else "gray"
                        st.markdown(f"**상태**: <span style='color:{status_color}'>{status_text}</span>", unsafe_allow_html=True)
                    
                    with col3:
                        st.markdown(f"**가격**: {order['주문가격']:,.0f} KRW")
                        st.markdown(f"**수량**: {order['주문수량']:.8f}")
                        
                    st.markdown(f"**거래금액**: {order['주문금액']:,.0f} KRW")
                    
                    st.markdown("</div>", unsafe_allow_html=True)
            
            # 페이지네이션 컨트롤
            if total_pages > 1:
                col1, col2, col3 = st.columns([1, 4, 1])
                with col1:
                    if st.button("◀️ 이전", key="prev_history", disabled=st.session_state.history_page <= 0):
                        st.session_state.history_page -= 1
                        st.rerun()
                with col2:
                    st.markdown(f"<div style='text-align:center'>페이지 {st.session_state.history_page + 1} / {total_pages}</div>", unsafe_allow_html=True)
                with col3:
                    if st.button("다음 ▶️", key="next_history", disabled=st.session_state.history_page >= total_pages - 1):
                        st.session_state.history_page += 1
                        st.rerun()
        else:
            st.info("필터링된 거래 내역이 없습니다.")
    else:
        st.info("거래 내역이 없습니다.")
        
    # API 키 없는 경우 안내
    if not has_api_keys:
        st.info("현재 샘플 데이터가 표시되고 있습니다. 실제 거래 내역을 보려면 API 설정 탭에서 API 키를 설정하세요.")
