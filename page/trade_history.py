import streamlit as st
import pyupbit
import pandas as pd
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import sys
sys.path.append("tools/upbit")
from UPBIT import Trade
from page.api_setting import check_api_keys, get_upbit_trade_instance
import requests
import hashlib
import jwt
import uuid as uuid_module
from urllib.parse import urlencode
import time

# 스타일 설정
st.markdown("""
    <style>
    .order-card {
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 15px;
        border: 1px solid #ddd;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .order-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    .buy-order {
        background-color: rgba(255, 240, 240, 0.3);
        border-left: 4px solid #ff4b4b;
    }
    .sell-order {
        background-color: rgba(240, 240, 255, 0.3);
        border-left: 4px solid #4b4bff;
    }
    .transaction-card {
        background-color: rgba(240, 255, 240, 0.3);
        border-left: 4px solid #4bff4b;
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 15px;
        border: 1px solid #ddd;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .transaction-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    .status-done {
        color: #4bff4b;
        font-weight: bold;
        background-color: rgba(75, 255, 75, 0.1);
        padding: 5px 10px;
        border-radius: 20px;
    }
    .status-wait {
        color: #ffbb00;
        font-weight: bold;
        background-color: rgba(255, 187, 0, 0.1);
        padding: 5px 10px;
        border-radius: 20px;
    }
    .status-cancel {
        color: #aaaaaa;
        font-weight: bold;
        background-color: rgba(170, 170, 170, 0.1);
        padding: 5px 10px;
        border-radius: 20px;
    }
    .coin-name {
        font-weight: bold;
        font-size: 1.2rem;
        margin: 0;
    }
    .price-value {
        font-weight: bold;
        color: #333;
    }
    .info-label {
        color: #666;
        font-size: 0.9rem;
    }
    .info-divider {
        margin: 10px 0;
        border-top: 1px solid #eee;
    }
    </style>
""", unsafe_allow_html=True)

def format_number(number: float) -> str:
    """숫자를 천 단위 구분자와 함께 포맷팅"""
    return f"{number:,.0f}"

def format_date(date_string: str) -> str:
    """날짜 포맷팅"""
    if not date_string:
        return datetime.now().strftime("%Y-%m-%d %H:%M")
        
    try:
        dt = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%f%z")
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        try:
            dt = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S%z")
            return dt.strftime("%Y-%m-%d %H:%M")
        except:
            try:
                dt = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
                return dt.strftime("%Y-%m-%d %H:%M")
            except:
                # 날짜 형식이 변경되거나 잘못된 경우 원본 반환
                return date_string

@st.cache_data(ttl=300)  # 5분 캐싱
def get_user_orders(_upbit_trade) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """사용자의 주문 내역과 체결 내역 조회"""
    try:
        # API 연결 확인
        if not _upbit_trade:
            st.error("Upbit 인스턴스를 생성할 수 없습니다. API 설정을 확인하세요.")
            return pd.DataFrame(), pd.DataFrame()
            
        # 유효한 API 키 확인
        if not _upbit_trade.access_key or not _upbit_trade.secret_key or _upbit_trade.access_key == '{ACCESS KEY 입력 : }' or _upbit_trade.secret_key == '{SECRET KEY 입력 : }':
            st.error("유효한 API 키가 설정되지 않았습니다. API 설정 탭에서 키를 입력하세요.")
            return pd.DataFrame(), pd.DataFrame()
        
        # 주문 내역 초기화
        orders_df = pd.DataFrame(columns=["주문시간", "코인", "주문유형", "주문가격", "주문수량", "체결수량", "미체결수량", "주문금액", "수수료", "상태", "주문번호"])
        
        with st.spinner("API를 통해 주문 내역을 불러오는 중..."):
            # get_order_history 메서드 사용하여 주문 내역 조회
            all_orders = _upbit_trade.get_order_history(ticker_or_uuid="", limit=100)
            
            # 주문 내역이 없는 경우 주요 코인별로 조회 시도
            if not all_orders:
                st.info("주요 코인별 주문 내역을 조회합니다...")
                major_tickers = ["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-SOL", "KRW-DOGE", "KRW-ADA"]
                
                for ticker in major_tickers:
                    # 각 코인의 모든 상태 주문 조회
                    ticker_orders = _upbit_trade.get_order_history(ticker_or_uuid=ticker, limit=20)
                    if ticker_orders:
                        all_orders.extend(ticker_orders)
            
            # 주문 데이터 처리
            if all_orders:
                processed_orders = []
                for order in all_orders:
                    try:
                        # 필수 필드 확인
                        market = order.get('market', '')
                        side = order.get('side', '')
                        
                        if not market or not side:
                            continue
                            
                        # 숫자 데이터 안전하게 변환
                        try:
                            price = float(order.get('price', 0) or 0)
                            volume = float(order.get('volume', 0) or 0)
                            executed_volume = float(order.get('executed_volume', 0) or 0)
                            remaining_volume = volume - executed_volume
                            paid_fee = float(order.get('paid_fee', 0) or 0)
                        except (ValueError, TypeError):
                            continue
                        
                        state = order.get('state', '')
                        created_at = order.get('created_at', '')
                        order_uuid = order.get('uuid', '')
                        
                        # 유효한 데이터만 추가
                        if price > 0 and volume > 0:
                            amount = price * volume
                            
                            order_info = {
                                "주문시간": format_date(created_at),
                                "코인": market.replace("KRW-", ""),
                                "주문유형": "매수" if side == 'bid' else "매도",
                                "주문가격": float(price),
                                "주문수량": float(volume),
                                "체결수량": float(executed_volume),
                                "미체결수량": float(remaining_volume),
                                "주문금액": float(amount),
                                "수수료": float(paid_fee),
                                "상태": "완료" if state == 'done' else "대기" if state == 'wait' else "취소",
                                "주문번호": str(order_uuid)
                            }
                            processed_orders.append(order_info)
                    except Exception as e:
                        continue
                
                # 중복 제거
                if processed_orders:
                    # 주문번호 기준으로 중복 제거
                    unique_orders = []
                    seen_uuids = set()
                    
                    for order in processed_orders:
                        order_uuid = order.get("주문번호", "")
                        if order_uuid not in seen_uuids:
                            seen_uuids.add(order_uuid)
                            unique_orders.append(order)
                    
                    # 주문 내역 데이터프레임
                    orders_df = pd.DataFrame(unique_orders)
                    st.success(f"{len(unique_orders)}개의 주문 내역을 불러왔습니다.")
        
        # 주문 내역이 비어있으면 빈 데이터프레임 반환
        if orders_df.empty:
            st.warning("주문 내역을 불러올 수 없습니다. 샘플 데이터를 표시합니다.")
            return generate_sample_order_data()
        
        # 체결 내역은 완료된 주문만 포함
        transactions_df = orders_df[orders_df["상태"] == "완료"].copy() if not orders_df.empty else pd.DataFrame(
            columns=["주문시간", "코인", "주문유형", "주문가격", "주문수량", "체결수량", "미체결수량", "주문금액", "수수료", "상태", "주문번호"]
        )
        
        # 최신순 정렬
        orders_df = orders_df.sort_values('주문시간', ascending=False)
        transactions_df = transactions_df.sort_values('주문시간', ascending=False)
        
        return orders_df, transactions_df
    
    except Exception as e:
        st.error(f"주문 내역 조회 중 오류 발생: {str(e)}")
        st.warning("샘플 데이터를 표시합니다.")
        return generate_sample_order_data()

def generate_sample_order_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """샘플 주문 내역과 체결 내역 생성"""
    st.info("API 연결이 없어 샘플 주문 내역을 표시합니다. 실제 거래 내역을 보려면 API 키를 설정하세요.")
    
    # 샘플 데이터 생성
    today = datetime.now()
    sample_coins = ["BTC", "ETH", "XRP", "DOGE", "ADA", "SOL"]
    
    # 주문 상태 유형
    order_states = ["완료", "대기", "취소"]
    state_weights = [0.6, 0.3, 0.1]  # 상태별 비율
    
    sample_orders = []
    order_uuid = 1000  # 샘플 주문번호 시작값
    
    # 더 다양한 거래 내역 생성 (다양한 시간대와 가격)
    for i in range(40):  # 40개로 증가
        # 더 넓은 시간 범위 (최근 15일)
        days_ago = i // 3
        hours_ago = (i % 24)
        minutes_ago = i * 5 % 60
        
        order_date = today - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
        date_str = order_date.strftime("%Y-%m-%d %H:%M")
        
        # 다양한 코인 선택
        coin_idx = (i + hash(date_str)) % len(sample_coins)
        coin = sample_coins[coin_idx]
        
        # 코인 타입별 가격 설정 (변동성 추가)
        import random
        price_variation = random.uniform(0.95, 1.05)  # 5% 변동성
        
        if coin == "BTC":
            base_price = 50000000
            price = int(base_price * price_variation)
            volume = round(0.001 + (i * 0.0001), 8)
        elif coin == "ETH":
            base_price = 3000000
            price = int(base_price * price_variation)
            volume = round(0.01 + (i * 0.001), 8)
        elif coin == "SOL":
            base_price = 150000
            price = int(base_price * price_variation)
            volume = round(0.1 + (i * 0.01), 8)
        else:
            base_price = 500 + (i * 10)
            price = int(base_price * price_variation)
            volume = round(10 + i, 8)
            
        # 주문 유형 (매수/매도)
        order_type = "매수" if i % 2 == 0 else "매도"
        
        # 주문 상태 (가중치에 따라 선택)
        import numpy as np
        state = np.random.choice(order_states, p=state_weights)
        
        # 체결 수량 계산 (상태에 따라 다름)
        if state == "완료":
            executed_volume = volume
            remaining_volume = 0
        elif state == "대기":
            executed_volume = 0
            remaining_volume = volume
        else:  # 취소
            if random.random() < 0.3:  # 30% 확률로 일부 체결
                executed_volume = round(volume * random.uniform(0.1, 0.5), 8)
                remaining_volume = round(volume - executed_volume, 8)
            else:  # 70% 확률로 미체결 취소
                executed_volume = 0
                remaining_volume = volume
        
        # 주문 금액 및 수수료
        amount = price * volume
        fee = amount * 0.0005
        
        # 주문번호 생성 (실제와 유사하게)
        order_id = f"sample-{uuid_module.uuid4().hex[:12]}"
        
        sample_orders.append({
            "주문시간": date_str,
            "코인": coin,
            "주문유형": order_type,
            "주문가격": price,
            "주문수량": volume,
            "체결수량": executed_volume,
            "미체결수량": remaining_volume,
            "주문금액": amount,
            "수수료": fee,
            "상태": state,
            "주문번호": order_id
        })
    
    # 주문 내역 데이터프레임
    orders_df = pd.DataFrame(sample_orders)
    
    # 체결 내역은 완료된 주문만 포함
    transactions_df = orders_df[orders_df["상태"] == "완료"].copy()
    
    # 최신순 정렬
    orders_df = orders_df.sort_values('주문시간', ascending=False)
    transactions_df = transactions_df.sort_values('주문시간', ascending=False)
    
    return orders_df, transactions_df

def show_trade_history():
    """거래 내역 화면 표시"""
    st.title("📝 나의 거래 내역")
    
    # API 키 확인
    has_api_keys = check_api_keys()
    
    # Upbit Trade 인스턴스 생성
    upbit_trade = get_upbit_trade_instance()
    
    # 새로고침 버튼과 표시 옵션
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        if st.button("🔄 새로고침", key="history_refresh"):
            # 캐시 초기화 및 앱 재실행
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        # 표시 형식 선택
        display_mode = st.radio(
            "표시 형식",
            ["카드", "테이블"],
            horizontal=True,
            key="display_mode"
        )
    
    with col3:
        if upbit_trade and has_api_keys:
            st.success("API가 연결되었습니다.")
        else:
            st.warning("API 키 설정이 필요합니다. API 설정 탭에서 키를 입력하세요.")
    
    # API 키가 없으면 안내 메시지 표시 후 종료
    if not has_api_keys:
        st.info("실제 거래 내역을 보려면 API 설정 탭에서 API 키를 설정하세요.")
        st.markdown("""
        <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-top: 20px;">
            <h3>API 키 설정 방법</h3>
            <ol>
                <li>업비트 웹사이트에 로그인합니다.</li>
                <li>오른쪽 상단의 '내 계정' > 'Open API 관리'로 이동합니다.</li>
                <li>API 키를 생성하고 주문 기능을 활성화합니다.</li>
                <li>발급받은 Access Key와 Secret Key를 복사합니다.</li>
                <li>이 앱의 'API 설정' 탭에서 키를 등록합니다.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # 거래 내역 탭 추가
    tab1, tab2 = st.tabs(["📋 주문 내역", "💰 체결 내역"])
    
    # 주문 내역과 체결 내역 가져오기
    with st.spinner("실제 거래 내역을 불러오는 중..."):
        orders_df, transactions_df = get_user_orders(upbit_trade)
    
    # 주문 내역 탭
    with tab1:
        st.subheader("주문 내역")
        st.markdown("주문한 모든 거래 내역입니다. (대기, 완료, 취소 포함)")
        
        # 주문 내역이 없는 경우
        if orders_df.empty:
            st.warning("주문 내역이 없습니다. API 설정이 올바른지 확인하세요.")
            return
        
        # 필터링 옵션
        st.markdown("#### 🔍 필터")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # 코인 필터
            coin_options = ["전체"]
            if not orders_df.empty and "코인" in orders_df.columns:
                coin_options.extend(sorted(orders_df["코인"].unique()))
                
            order_coin = st.selectbox(
                "코인",
                options=coin_options,
                key="order_coin_filter"
            )
        
        with col2:
            # 상태 필터
            status_options = ["전체"]
            if not orders_df.empty and "상태" in orders_df.columns:
                status_options.extend(sorted(orders_df["상태"].unique()))
                
            order_status = st.selectbox(
                "주문 상태",
                options=status_options,
                key="order_status_filter"
            )
        
        with col3:
            # 주문 유형 필터
            type_options = ["전체"]
            if not orders_df.empty and "주문유형" in orders_df.columns:
                type_options.extend(sorted(orders_df["주문유형"].unique()))
                
            order_type = st.selectbox(
                "주문 유형",
                options=type_options,
                key="order_type_filter"
            )
        
        # 필터링 적용
        filtered_orders = orders_df.copy()
        
        if order_coin != "전체" and "코인" in filtered_orders.columns:
            filtered_orders = filtered_orders[filtered_orders["코인"] == order_coin]
            
        if order_status != "전체" and "상태" in filtered_orders.columns:
            filtered_orders = filtered_orders[filtered_orders["상태"] == order_status]
            
        if order_type != "전체" and "주문유형" in filtered_orders.columns:
            filtered_orders = filtered_orders[filtered_orders["주문유형"] == order_type]
        
        # 필터링된 주문 내역 표시
        if filtered_orders.empty:
            st.info("필터링 조건에 맞는 주문 내역이 없습니다.")
        else:
            # 페이지네이션
            orders_per_page = 10 if display_mode == "테이블" else 5
            
            if 'orders_page' not in st.session_state:
                st.session_state.orders_page = 0
                
            total_pages = max(1, (len(filtered_orders) + orders_per_page - 1) // orders_per_page)
            
            # 현재 페이지가 유효한지 확인
            if st.session_state.orders_page >= total_pages:
                st.session_state.orders_page = 0
                
            # 현재 페이지에 해당하는 주문 필터링
            start_idx = st.session_state.orders_page * orders_per_page
            end_idx = min(start_idx + orders_per_page, len(filtered_orders))
            
            page_orders = filtered_orders.iloc[start_idx:end_idx]
            
            # 테이블 또는 카드 형식으로 표시
            if display_mode == "테이블":
                # 테이블 형식으로 표시
                display_columns = ["주문시간", "코인", "주문유형", "주문가격", "주문수량", "체결수량", "미체결수량", "주문금액", "수수료", "상태"]
                
                # 데이터 포맷팅
                formatted_orders = page_orders.copy()
                if "주문가격" in formatted_orders.columns:
                    formatted_orders["주문가격"] = formatted_orders["주문가격"].apply(lambda x: f"{x:,.0f} KRW")
                if "주문금액" in formatted_orders.columns:
                    formatted_orders["주문금액"] = formatted_orders["주문금액"].apply(lambda x: f"{x:,.0f} KRW")
                if "수수료" in formatted_orders.columns:
                    formatted_orders["수수료"] = formatted_orders["수수료"].apply(lambda x: f"{x:,.2f} KRW")
                
                # 상태에 따른 스타일링
                def highlight_status(s):
                    if s == "완료":
                        return 'background-color: rgba(0, 255, 0, 0.2); color: darkgreen; font-weight: bold'
                    elif s == "대기":
                        return 'background-color: rgba(255, 255, 0, 0.2); color: darkorange; font-weight: bold'
                    else:  # 취소
                        return 'background-color: rgba(255, 0, 0, 0.1); color: gray; font-weight: bold'
                
                # 주문 유형에 따른 스타일링
                def highlight_order_type(s):
                    if s == "매수":
                        return 'background-color: rgba(255, 0, 0, 0.1); color: darkred; font-weight: bold'
                    else:  # 매도
                        return 'background-color: rgba(0, 0, 255, 0.1); color: darkblue; font-weight: bold'
                
                # 스타일 적용한 테이블 표시
                st.dataframe(
                    formatted_orders[display_columns].style
                    .applymap(highlight_status, subset=["상태"])
                    .applymap(highlight_order_type, subset=["주문유형"]),
                    use_container_width=True,
                    height=400
                )
                
                # 주문 세부정보 확장 섹션
                with st.expander("📋 주문 상세정보"):
                    for i, (_, order) in enumerate(page_orders.iterrows()):
                        st.markdown(f"**주문 #{i+1}** - {order['코인']} {order['주문유형']} ({order['상태']})")
                        st.markdown(f"📅 주문시간: {order['주문시간']}")
                        st.markdown(f"💰 주문가격: {order['주문가격']:,.0f} KRW × {order['주문수량']:.8f} = {order['주문금액']:,.0f} KRW")
                        st.markdown(f"✅ 체결수량: {order['체결수량']:.8f} / 미체결: {order['미체결수량']:.8f}")
                        st.markdown(f"🧾 수수료: {order['수수료']:,.2f} KRW")
                        st.markdown(f"🔑 주문번호: `{order['주문번호']}`")
                        st.markdown("---")
                
            else:
                # 카드 형식으로 표시 (기존 코드 향상)
                st.markdown('<div class="trade-cards-container">', unsafe_allow_html=True)
                
                for _, order in page_orders.iterrows():
                    order_type_class = "buy-order" if order["주문유형"] == "매수" else "sell-order"
                    status_class = f"status-{order['상태'] if order['상태'] == '완료' else 'wait' if order['상태'] == '대기' else 'cancel'}"
                    
                    # 향상된 카드 디자인
                    order_card = f"""
                    <div class="order-card {order_type_class}" style="border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <h4 style="margin: 0; font-size: 1.2rem; font-weight: bold;">{order['코인']} {order['주문유형']}</h4>
                            <span class="{status_class}" style="padding: 5px 10px; border-radius: 20px;">{order['상태']}</span>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                            <div>
                                <p style="margin: 5px 0;"><strong>📅 주문시간:</strong> {order['주문시간']}</p>
                                <p style="margin: 5px 0;"><strong>💰 주문가격:</strong> {order['주문가격']:,.0f} KRW</p>
                                <p style="margin: 5px 0;"><strong>🔢 주문수량:</strong> {order['주문수량']:.8f}</p>
                            </div>
                            <div>
                                <p style="margin: 5px 0;"><strong>💵 주문금액:</strong> {order['주문금액']:,.0f} KRW</p>
                                <p style="margin: 5px 0;"><strong>✅ 체결수량:</strong> {order['체결수량']:.8f}</p>
                                <p style="margin: 5px 0;"><strong>❓ 미체결수량:</strong> {order['미체결수량']:.8f}</p>
                            </div>
                        </div>
                        <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee;">
                            <p style="margin: 5px 0;"><strong>🧾 수수료:</strong> {order['수수료']:,.2f} KRW</p>
                            <p style="font-size: 0.8em; color: #666; margin: 5px 0;"><strong>🔑 주문번호:</strong> {order['주문번호']}</p>
                        </div>
                    </div>
                    """
                    st.markdown(order_card, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 페이지네이션 컨트롤
            if total_pages > 1:
                col1, col2, col3 = st.columns([1, 4, 1])
                with col1:
                    if st.button("◀️ 이전", key="prev_orders", disabled=st.session_state.orders_page <= 0):
                        st.session_state.orders_page -= 1
                        st.rerun()
                with col2:
                    paging_info = f"<div style='text-align:center'>페이지 {st.session_state.orders_page + 1} / {total_pages} (총 {len(filtered_orders)}개 주문)</div>"
                    st.markdown(paging_info, unsafe_allow_html=True)
                with col3:
                    if st.button("다음 ▶️", key="next_orders", disabled=st.session_state.orders_page >= total_pages - 1):
                        st.session_state.orders_page += 1
                        st.rerun()
    
    # 체결 내역 탭
    with tab2:
        st.subheader("체결 내역")
        st.markdown("완료된 거래 내역만 표시합니다.")
        
        # 체결 내역이 없는 경우
        if transactions_df.empty:
            st.warning("체결된 거래 내역이 없습니다.")
            return
        
        # 필터링 옵션
        st.markdown("#### 🔍 필터")
        col1, col2 = st.columns(2)
        
        with col1:
            # 코인 필터
            coin_options = ["전체"]
            if not transactions_df.empty and "코인" in transactions_df.columns:
                coin_options.extend(sorted(transactions_df["코인"].unique()))
                
            tx_coin = st.selectbox(
                "코인",
                options=coin_options,
                key="tx_coin_filter"
            )
        
        with col2:
            # 주문 유형 필터
            type_options = ["전체"]
            if not transactions_df.empty and "주문유형" in transactions_df.columns:
                type_options.extend(sorted(transactions_df["주문유형"].unique()))
                
            tx_type = st.selectbox(
                "주문 유형",
                options=type_options,
                key="tx_type_filter"
            )
        
        # 필터링 적용
        filtered_tx = transactions_df.copy()
        
        if tx_coin != "전체" and "코인" in filtered_tx.columns:
            filtered_tx = filtered_tx[filtered_tx["코인"] == tx_coin]
            
        if tx_type != "전체" and "주문유형" in filtered_tx.columns:
            filtered_tx = filtered_tx[filtered_tx["주문유형"] == tx_type]
        
        # 필터링된 체결 내역 표시
        if filtered_tx.empty:
            st.info("필터링 조건에 맞는 체결 내역이 없습니다.")
        else:
            # 페이지네이션
            tx_per_page = 10 if display_mode == "테이블" else 5
            
            if 'tx_page' not in st.session_state:
                st.session_state.tx_page = 0
                
            total_pages = max(1, (len(filtered_tx) + tx_per_page - 1) // tx_per_page)
            
            # 현재 페이지가 유효한지 확인
            if st.session_state.tx_page >= total_pages:
                st.session_state.tx_page = 0
                
            # 현재 페이지에 해당하는 체결 필터링
            start_idx = st.session_state.tx_page * tx_per_page
            end_idx = min(start_idx + tx_per_page, len(filtered_tx))
            
            page_tx = filtered_tx.iloc[start_idx:end_idx]
            
            # 테이블 또는 카드 형식으로 표시
            if display_mode == "테이블":
                # 테이블 형식으로 표시
                display_columns = ["주문시간", "코인", "주문유형", "주문가격", "체결수량", "주문금액", "수수료"]
                
                # 데이터 포맷팅
                formatted_tx = page_tx.copy()
                if "주문가격" in formatted_tx.columns:
                    formatted_tx["주문가격"] = formatted_tx["주문가격"].apply(lambda x: f"{x:,.0f} KRW")
                if "주문금액" in formatted_tx.columns:
                    formatted_tx["주문금액"] = formatted_tx["주문금액"].apply(lambda x: f"{x:,.0f} KRW")
                if "수수료" in formatted_tx.columns:
                    formatted_tx["수수료"] = formatted_tx["수수료"].apply(lambda x: f"{x:,.2f} KRW")
                
                # 주문 유형에 따른 스타일링
                def highlight_tx_type(s):
                    if s == "매수":
                        return 'background-color: rgba(255, 0, 0, 0.1); color: darkred; font-weight: bold'
                    else:  # 매도
                        return 'background-color: rgba(0, 0, 255, 0.1); color: darkblue; font-weight: bold'
                
                # 스타일 적용한 테이블 표시
                st.dataframe(
                    formatted_tx[display_columns].style
                    .applymap(highlight_tx_type, subset=["주문유형"]),
                    use_container_width=True,
                    height=400
                )
                
                # 체결 내역 요약 (통계)
                with st.expander("📊 체결 내역 통계"):
                    if not filtered_tx.empty:
                        # 코인별 총 거래금액
                        coin_totals = filtered_tx.groupby("코인")["주문금액"].sum().reset_index()
                        st.markdown("##### 코인별 총 거래금액")
                        for _, row in coin_totals.iterrows():
                            st.markdown(f"**{row['코인']}**: {row['주문금액']:,.0f} KRW")
                        
                        # 매수/매도 비율
                        buy_count = len(filtered_tx[filtered_tx["주문유형"] == "매수"])
                        sell_count = len(filtered_tx[filtered_tx["주문유형"] == "매도"])
                        
                        st.markdown("##### 매수/매도 비율")
                        st.markdown(f"매수: {buy_count}건 ({buy_count/(buy_count+sell_count)*100:.1f}%)")
                        st.markdown(f"매도: {sell_count}건 ({sell_count/(buy_count+sell_count)*100:.1f}%)")
                        
                        # 총 수수료
                        total_fee = filtered_tx["수수료"].sum()
                        st.markdown(f"##### 총 지불 수수료: {total_fee:,.2f} KRW")
            else:
                # 카드 형식으로 표시 (향상된 디자인)
                st.markdown('<div class="trade-cards-container">', unsafe_allow_html=True)
                
                for _, tx in page_tx.iterrows():
                    tx_type_text = "매수함" if tx["주문유형"] == "매수" else "매도함"
                    tx_type_class = "buy-order" if tx["주문유형"] == "매수" else "sell-order"
                    
                    # 향상된 체결 카드 디자인
                    tx_card = f"""
                    <div class="transaction-card" style="border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <h4 style="margin: 0; font-size: 1.2rem; font-weight: bold;">{tx['코인']} {tx_type_text}</h4>
                            <span class="status-done" style="padding: 5px 10px; border-radius: 20px;">체결완료</span>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                            <div>
                                <p style="margin: 5px 0;"><strong>📅 체결시간:</strong> {tx['주문시간']}</p>
                                <p style="margin: 5px 0;"><strong>💰 체결가격:</strong> {tx['주문가격']:,.0f} KRW</p>
                            </div>
                            <div>
                                <p style="margin: 5px 0;"><strong>🔢 체결수량:</strong> {tx['체결수량']:.8f}</p>
                                <p style="margin: 5px 0;"><strong>💵 체결금액:</strong> {tx['주문금액']:,.0f} KRW</p>
                            </div>
                        </div>
                        <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee;">
                            <p style="margin: 5px 0;"><strong>🧾 수수료:</strong> {tx['수수료']:,.2f} KRW</p>
                            <p style="font-size: 0.8em; color: #666; margin: 5px 0;"><strong>🔑 주문번호:</strong> {tx['주문번호']}</p>
                        </div>
                    </div>
                    """
                    st.markdown(tx_card, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 페이지네이션 컨트롤
            if total_pages > 1:
                col1, col2, col3 = st.columns([1, 4, 1])
                with col1:
                    if st.button("◀️ 이전", key="prev_tx", disabled=st.session_state.tx_page <= 0):
                        st.session_state.tx_page -= 1
                        st.rerun()
                with col2:
                    paging_info = f"<div style='text-align:center'>페이지 {st.session_state.tx_page + 1} / {total_pages} (총 {len(filtered_tx)}개 체결)</div>"
                    st.markdown(paging_info, unsafe_allow_html=True)
                with col3:
                    if st.button("다음 ▶️", key="next_tx", disabled=st.session_state.tx_page >= total_pages - 1):
                        st.session_state.tx_page += 1
                        st.rerun()
