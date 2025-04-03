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
def get_user_orders(_upbit_trade, max_pages=5) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """사용자의 주문 내역과 체결 내역 조회 (여러 페이지 조회)"""
    orders_columns = ["주문시간", "코인", "종류", "주문방식", "주문가격", "주문수량", "체결수량", "미체결수량", "주문총액", "상태", "주문번호"]
    transactions_columns = ["체결시간", "코인", "종류", "거래수량", "거래단가", "거래금액", "수수료", "주문시간", "주문번호"]

    all_processed_orders = [] # 모든 페이지의 주문 결과 누적
    all_processed_transactions = [] # 모든 페이지의 체결 결과 누적

    try:
        if not _upbit_trade or not _upbit_trade.is_valid: # Trade 객체 유효성 검사 추가
            st.error("Upbit 인스턴스 생성 또는 API 키 인증 실패.")
            return pd.DataFrame(columns=orders_columns), pd.DataFrame(columns=transactions_columns)

        # API 키 테스트는 초기화 시 수행되므로 여기서는 생략 가능
        # try: ... upbit.get_balance ... except ... 부분 제거

        # 여러 페이지 순회 조회
        st.info(f"[Debug] 최대 {max_pages} 페이지까지 주문 내역 조회 시작...")
        for page_num in range(1, max_pages + 1):
            st.info(f"[Debug] 페이지 {page_num} 조회 시도...")
            page_orders = None
            try:
                page_orders = _upbit_trade.get_order_history(page=page_num, limit=100)
                st.info(f"[Debug] 페이지 {page_num} API 결과 수신 (타입: {type(page_orders)}, 길이: {len(page_orders) if isinstance(page_orders, list) else 'N/A'})")
                if not isinstance(page_orders, list): page_orders = []
            except Exception as api_call_error:
                st.error(f"페이지 {page_num} API 호출 중 오류 발생: {str(api_call_error)}")
                break

            if not page_orders:
                st.info(f"[Debug] 페이지 {page_num} 결과 없음. 조회 중단.")
                break

            # 현재 페이지 데이터 처리 (에러 발생 가능성 있는 블록 감싸기 제거)
            current_page_error_count = 0
            if len(page_orders) > 0:
                 st.info(f"[Debug] 페이지 {page_num} 첫 번째 주문 데이터: {page_orders[0]}")

            for i, order in enumerate(page_orders):
                try:
                    if isinstance(order, dict) and 'error' in order:
                         st.error(f"[Debug] API 응답 오류 수신 (페이지 {page_num}, 주문 {i+1}): {order['error']}")
                         current_page_error_count += 1
                         continue

                    market = order.get('market', ''); side = order.get('side', ''); state = order.get('state', '')
                    if not market or not side or not state: continue

                    ord_type = order.get('ord_type', ''); created_at = order.get('created_at', ''); uuid = order.get('uuid', '')
                    order_price_str = order.get('price'); order_price = float(order_price_str) if order_price_str is not None else 0.0
                    volume = float(order.get('volume', 0) or 0); executed_volume = float(order.get('executed_volume', 0) or 0)
                    remaining_volume = volume - executed_volume; paid_fee = float(order.get('paid_fee', 0) or 0)

                    coin = market.replace("KRW-", ""); order_type_str = "매수" if side == 'bid' else "매도"
                    order_state_str = "완료" if state == 'done' else "대기" if state == 'wait' else "취소"
                    order_datetime_str = format_date(created_at)

                    order_info = { # 모든 주문 데이터
                        "주문시간": order_datetime_str, "코인": coin, "종류": order_type_str, "주문방식": ord_type,
                        "주문가격": order_price, "주문수량": volume, "체결수량": executed_volume,
                        "미체결수량": remaining_volume, "주문총액": order_price * volume if order_price else 0.0,
                        "상태": order_state_str, "주문번호": uuid
                    }
                    all_processed_orders.append(order_info)

                    if state == 'done' and executed_volume > 0: # 체결 완료 건만
                        avg_price_str = order.get('avg_price')
                        if avg_price_str: try: trade_price = float(avg_price_str); except: trade_price = 0.0
                        else: trade_price = order_price
                        trade_volume = executed_volume; trade_amount = trade_price * trade_volume

                        transaction_info = { # 체결 내역 데이터
                            "체결시간": order_datetime_str, "코인": coin, "종류": order_type_str,
                            "거래수량": trade_volume, "거래단가": trade_price, "거래금액": trade_amount,
                            "수수료": paid_fee, "주문시간": order_datetime_str, "주문번호": uuid
                        }
                        all_processed_transactions.append(transaction_info)

                except Exception as process_error:
                    st.warning(f"[Debug] 데이터 처리 중 오류 (페이지 {page_num}, 주문 {i+1}): {str(process_error)} - 데이터: {order}")
                    current_page_error_count += 1
                    continue # 개별 주문 처리 오류 시 다음 주문으로

            # 페이지 처리 완료 로그 (루프 내부에 위치)
            st.info(f"[Debug] 페이지 {page_num} 처리 완료. 오류 {current_page_error_count}건")

        # 모든 페이지 처리 후 최종 로그
        st.info(f"[Debug] 총 {len(all_processed_orders)}건 주문, {len(all_processed_transactions)}건 체결 내역 수집 완료.")

        # 최종 DataFrame 생성
        orders_df = pd.DataFrame(columns=orders_columns)
        transactions_df = pd.DataFrame(columns=transactions_columns)

        if all_processed_orders:
            unique_orders = []
            seen_uuids_ord = set()
            for order in all_processed_orders:
                 uuid = order.get("주문번호", "")
                 if uuid not in seen_uuids_ord:
                     seen_uuids_ord.add(uuid)
                     unique_orders.append(order)
            orders_df = pd.DataFrame(unique_orders, columns=orders_columns)
            orders_df = orders_df.sort_values('주문시간', ascending=False)
            st.success(f"총 {len(orders_df)}건의 주문 내역(모든 상태)을 처리했습니다.")

        if all_processed_transactions:
            unique_transactions = []
            seen_uuids_tx = set()
            for tx in all_processed_transactions:
                 uuid = tx.get("주문번호", "")
                 if uuid not in seen_uuids_tx:
                     seen_uuids_tx.add(uuid)
                     unique_transactions.append(tx)
            transactions_df = pd.DataFrame(unique_transactions, columns=transactions_columns)
            transactions_df = transactions_df.sort_values('체결시간', ascending=False)
            st.success(f"총 {len(transactions_df)}건의 체결 완료 내역을 처리했습니다.")

        if orders_df.empty and transactions_df.empty:
            st.warning("조회된 주문/체결 내역이 없습니다.")

        return orders_df, transactions_df

    except Exception as e:
        st.error(f"주문/체결 내역 조회 함수 실행 중 오류 발생: {str(e)}")
        st.warning("오류로 인해 빈 데이터를 반환합니다.")
        return pd.DataFrame(columns=orders_columns), pd.DataFrame(columns=transactions_columns)

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
            "종류": order_type,
            "주문방식": ord_type,
            "주문가격": price,
            "주문수량": volume,
            "체결수량": executed_volume,
            "미체결수량": remaining_volume,
            "주문총액": amount,
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
    
    # 주문 내역과 체결 내역 가져오기
    with st.spinner("실제 거래 내역을 불러오는 중..."):
        orders_df, transactions_df = get_user_orders(upbit_trade)
        # get_user_orders 호출 직후 transactions_df 상태 로그 추가
        st.info(f"[Debug] get_user_orders 반환 직후 - 체결 DF {transactions_df.shape[0]} 행")
        if not transactions_df.empty:
            st.info(f"[Debug] 반환된 체결 DF 내용 (첫 5행):")
            st.dataframe(transactions_df.head()) # 내용 확인용 데이터프레임 출력

    st.subheader("💰 체결 내역")
    st.markdown("체결 완료된 거래 내역입니다.")

    if transactions_df.empty:
        st.warning("체결된 거래 내역이 없습니다.")
        return

    st.markdown("#### 🔍 필터")
    col1, col2 = st.columns(2)

    with col1:
        coin_options = ["전체"]
        if not transactions_df.empty and "코인" in transactions_df.columns:
            coin_options.extend(sorted(transactions_df["코인"].unique()))
        tx_coin = st.selectbox("코인", options=coin_options, key="tx_coin_filter")

    with col2:
        type_options = ["전체"]
        if not transactions_df.empty and "종류" in transactions_df.columns:
            type_options.extend(sorted(transactions_df["종류"].unique()))
        tx_type = st.selectbox("종류", options=type_options, key="tx_type_filter")

    filtered_tx = transactions_df.copy()
    if tx_coin != "전체" and "코인" in filtered_tx.columns:
        filtered_tx = filtered_tx[filtered_tx["코인"] == tx_coin]
    if tx_type != "전체" and "종류" in filtered_tx.columns:
        filtered_tx = filtered_tx[filtered_tx["종류"] == tx_type]

    # 필터링 직후 filtered_tx 상태 로그 추가
    st.info(f"[Debug] 필터링 후 - 필터링된 체결 DF {filtered_tx.shape[0]} 행")
    if not filtered_tx.empty:
        st.info(f"[Debug] 필터링된 체결 DF 내용 (첫 5행):")
        st.dataframe(filtered_tx.head()) # 내용 확인용 데이터프레임 출력

    if filtered_tx.empty:
        st.info("필터링 조건에 맞는 체결 내역이 없습니다.")
    else:
        # 페이지네이션
        tx_per_page = 10 if display_mode == "테이블" else 5
        if 'tx_page' not in st.session_state:
            st.session_state.tx_page = 0
        total_pages = max(1, (len(filtered_tx) + tx_per_page - 1) // tx_per_page)
        if st.session_state.tx_page >= total_pages:
            st.session_state.tx_page = 0
        start_idx = st.session_state.tx_page * tx_per_page
        end_idx = min(start_idx + tx_per_page, len(filtered_tx))
        page_tx = filtered_tx.iloc[start_idx:end_idx]

        # 페이지 표시 전 page_tx 상태 로그 추가
        st.info(f"[Debug] 페이지네이션 후 - 현재 페이지 체결 DF {page_tx.shape[0]} 행")
        if not page_tx.empty:
            st.info(f"[Debug] 현재 페이지 체결 DF 내용 (첫 5행):")
            st.dataframe(page_tx.head()) # 내용 확인용 데이터프레임 출력

        # 테이블 또는 카드 표시 로직 (기존과 동일)
        if display_mode == "테이블":
            # 테이블 형식으로 표시
            display_columns = ["체결시간", "코인", "종류", "거래수량", "거래단가", "거래금액", "수수료", "주문시간"]
            
            # 데이터 포맷팅
            formatted_tx = page_tx.copy()
            if "거래단가" in formatted_tx.columns:
                formatted_tx["거래단가"] = formatted_tx["거래단가"].apply(lambda x: f"{x:,.0f} KRW")
            if "거래금액" in formatted_tx.columns:
                formatted_tx["거래금액"] = formatted_tx["거래금액"].apply(lambda x: f"{x:,.0f} KRW")
            if "수수료" in formatted_tx.columns:
                formatted_tx["수수료"] = formatted_tx["수수료"].apply(lambda x: f"{x:,.4f} KRW")
            if "거래수량" in formatted_tx.columns:
                formatted_tx["거래수량"] = formatted_tx["거래수량"].apply(lambda x: f"{x:.8f}")
            
            # 주문 유형에 따른 스타일링
            def highlight_tx_type(s):
                if s == "매수":
                    return 'background-color: rgba(255, 0, 0, 0.1); color: darkred; font-weight: bold'
                else:  # 매도
                    return 'background-color: rgba(0, 0, 255, 0.1); color: darkblue; font-weight: bold'
            
            # 스타일 적용한 테이블 표시
            st.dataframe(
                formatted_tx[display_columns].style
                .applymap(highlight_tx_type, subset=["종류"]),
                use_container_width=True,
                height=400
            )
            
            # 체결 내역 요약 (통계)
            with st.expander("📊 체결 내역 통계"):
                if not filtered_tx.empty:
                    coin_totals = filtered_tx.groupby("코인")["거래금액"].sum().reset_index()
                    st.markdown("##### 코인별 총 거래금액")
                    for _, row in coin_totals.iterrows():
                        st.markdown(f"**{row['코인']}**: {row['거래금액']:.0f} KRW")
                    
                    buy_count = len(filtered_tx[filtered_tx["종류"] == "매수"])
                    sell_count = len(filtered_tx[filtered_tx["종류"] == "매도"])
                    
                    if (buy_count + sell_count) > 0: # Avoid division by zero
                        st.markdown("##### 매수/매도 비율")
                        st.markdown(f"매수: {buy_count}건 ({buy_count/(buy_count+sell_count)*100:.1f}%)")
                        st.markdown(f"매도: {sell_count}건 ({sell_count/(buy_count+sell_count)*100:.1f}%)")
                    else:
                        st.markdown("##### 매수/매도 비율: 정보 없음")
                    
                    total_fee = filtered_tx["수수료"].sum()
                    st.markdown(f"##### 총 지불 수수료: {total_fee:.4f}")
        else:
            # 카드 형식으로 표시 (기존 코드 향상)
            st.markdown('<div class="trade-cards-container">', unsafe_allow_html=True)
            
            for _, tx in page_tx.iterrows():
                tx_type_text = "매수함" if tx["종류"] == "매수" else "매도함"
                tx_type_class = "buy-order" if tx["종류"] == "매수" else "sell-order"
                
                # 향상된 체결 카드 디자인
                tx_card = f"""
                <div class="transaction-card" style="border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <h4 style="margin: 0; font-size: 1.2rem; font-weight: bold;">{tx['코인']} {tx_type_text}</h4>
                        <span class="status-done" style="padding: 5px 10px; border-radius: 20px;">체결완료</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                        <div>
                            <p style="margin: 5px 0;"><strong>📅 체결시간:</strong> {tx['체결시간']}</p>
                            <p style="margin: 5px 0;"><strong>💰 거래단가:</strong> {tx['거래단가']:.0f} KRW</p>
                            <p style="margin: 5px 0;"><strong>🔢 거래수량:</strong> {tx['거래수량']:.8f}</p>
                        </div>
                        <div>
                            <p style="margin: 5px 0;"><strong>💵 거래금액:</strong> {tx['거래금액']:.0f} KRW</p>
                            <p style="margin: 5px 0;"><strong>🧾 수수료:</strong> {tx['수수료']:.4f}</p>
                            <p style="font-size: 0.8em; color: #666; margin: 5px 0;"><strong>🔑 주문번호:</strong> {tx['주문번호']}</p>
                        </div>
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
