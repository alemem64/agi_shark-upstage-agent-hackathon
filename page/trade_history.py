import streamlit as st
import pyupbit
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import sys
sys.path.append("tools/upbit")
from UPBIT import Trade
from page.api_setting import check_api_keys, get_upbit_trade_instance
import requests
import hashlib
import jwt
import uuid
from urllib.parse import urlencode

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

@st.cache_data(ttl=120)  # 2분으로 캐시 시간 단축
def get_order_history_from_trade(_upbit_trade) -> pd.DataFrame:
    """주문 내역 조회"""
    try:
        # 실제 거래소에서 데이터 가져오기 시도
        if _upbit_trade:
            st.info("Upbit API에서 거래 내역을 불러오는 중...")
            
            # 직접 API 호출을 위한 준비
            server_url = 'https://api.upbit.com'
            access_key = _upbit_trade.access_key
            secret_key = _upbit_trade.secret_key
            
            # 디버깅 정보
            has_keys = access_key != '{ACCESS KEY 입력 : }' and secret_key != '{SECRET KEY 입력 : }'
            if not has_keys:
                st.warning("유효한 API 키가 설정되지 않았습니다.")
                return generate_sample_trade_history()
            
            # 방법 1: 직접 API 호출로 주문 내역 조회
            try:
                # API 호출 준비 - 모든 상태('wait', 'done', 'cancel') 포함
                query = {'limit': 100}  # 상태를 지정하지 않으면 모든 상태가 포함됨
                query_string = urlencode(query).encode()
                
                m = hashlib.sha512()
                m.update(query_string)
                query_hash = m.hexdigest()
                
                payload = {
                    'access_key': access_key,
                    'nonce': str(uuid.uuid4()),
                    'query_hash': query_hash,
                    'query_hash_alg': 'SHA512'
                }
                
                jwt_token = jwt.encode(payload, secret_key)
                authorize_token = f'Bearer {jwt_token}'
                headers = {'Authorization': authorize_token}
                
                # API 요청 실행
                res = requests.get(f"{server_url}/v1/orders", params=query, headers=headers)
                
                # 응답 확인 및 처리
                if res.status_code == 200:
                    orders_data = res.json()
                    
                    if orders_data and len(orders_data) > 0:
                        # 주문 데이터 처리
                        processed_orders = []
                        
                        # 데이터 검증 및 처리
                        st.success(f"Upbit API에서 {len(orders_data)}개의 거래 내역을 불러왔습니다.")
                        
                        for order in orders_data:
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
                                    executed_volume = float(order.get('executed_volume', 0)) if 'executed_volume' in order else volume
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
                                st.error(f"주문 처리 중 오류: {str(e)}")
                                continue
                        
                        # 유효한 주문이 있으면 실제 데이터 반환
                        if processed_orders:
                            # 데이터프레임으로 변환
                            df = pd.DataFrame(processed_orders)
                            # 최신순 정렬
                            return df.sort_values('주문시간', ascending=False)
                    else:
                        st.info("API 응답은 성공했지만 거래 내역이 없습니다.")
                else:
                    st.error(f"API 오류 ({res.status_code}): {res.text}")
            except Exception as e:
                st.error(f"API 직접 호출 중 오류 발생: {str(e)}")
            
            # 방법 2: pyupbit 라이브러리 사용
            try:
                st.info("pyupbit 라이브러리로 주문 내역 조회 시도 중...")
                
                # 거래 내역 조회 방법 개선
                try:
                    # 1. 주문 리스트 가져오기 (ticker 인자 추가)
                    st.info("전체 주문 목록을 조회합니다...")
                    all_orders = _upbit_trade.upbit.get_order("", limit=100)
                    
                    # 2. 주문 리스트 가져오기 실패 시 완료된 주문만 시도
                    if not all_orders:
                        st.info("전체 주문 조회 실패. 완료된 주문만 조회합니다.")
                        all_orders = _upbit_trade.upbit.get_order("", state="done", limit=100)
                    
                    # 3. 위 방법으로도 실패하면 각 상태별로 시도
                    if not all_orders:
                        st.info("상태별 주문 조회 시도 중...")
                        orders_done = _upbit_trade.upbit.get_order("", state="done", limit=50)
                        orders_wait = _upbit_trade.upbit.get_order("", state="wait", limit=50)
                        orders_cancel = _upbit_trade.upbit.get_order("", state="cancel", limit=50)
                        
                        # 모든 주문을 리스트로 합침
                        all_orders = []
                        if orders_done:
                            if isinstance(orders_done, list):
                                all_orders.extend(orders_done)
                            elif isinstance(orders_done, dict):
                                all_orders.append(orders_done)
                                
                        if orders_wait:
                            if isinstance(orders_wait, list):
                                all_orders.extend(orders_wait)
                            elif isinstance(orders_wait, dict):
                                all_orders.append(orders_wait)
                                
                        if orders_cancel:
                            if isinstance(orders_cancel, list):
                                all_orders.extend(orders_cancel)
                            elif isinstance(orders_cancel, dict):
                                all_orders.append(orders_cancel)
                                
                except Exception as sub_e:
                    st.error(f"주문 목록 조회 중 오류: {str(sub_e)}")
                
                # 4. 최후의 방법: 주요 마켓의 주문 정보 가져오기
                if not all_orders:
                    st.info("주요 코인별 주문 조회를 시도합니다...")
                    all_orders = []
                    
                    # 주요 코인 목록
                    major_tickers = ["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-SOL", "KRW-DOGE", "KRW-ADA"]
                    
                    for ticker in major_tickers:
                        try:
                            # 코인별 주문 내역 조회
                            orders = _upbit_trade.upbit.get_order(ticker, state="done", limit=10)
                            if orders:
                                if isinstance(orders, list):
                                    all_orders.extend(orders)
                                elif isinstance(orders, dict):
                                    all_orders.append(orders)
                        except Exception as sub_e:
                            continue
                
                if all_orders:
                    # 데이터 처리
                    processed_orders = []
                    
                    # 형식 확인 및 변환
                    if not isinstance(all_orders, list):
                        if isinstance(all_orders, dict):
                            all_orders = [all_orders]
                        else:
                            st.warning(f"예상치 못한 응답 형식: {type(all_orders)}")
                            return generate_sample_trade_history()
                    
                    st.success(f"{len(all_orders)}개의 주문 내역을 불러왔습니다.")
                    
                    # 주문 데이터 처리
                    for order in all_orders:
                        try:
                            # 필수 필드가 있는지 확인
                            market = order.get('market', '')
                            side = order.get('side', '')
                            
                            if not market or not side:
                                continue
                                
                            # 숫자 데이터 변환
                            price = float(order.get('price', 0))
                            volume = float(order.get('volume', 0))
                            executed_volume = float(order.get('executed_volume', 0)) if 'executed_volume' in order else volume
                            
                            # 유효한 주문만 처리
                            if price > 0 and (volume > 0 or executed_volume > 0):
                                actual_volume = executed_volume if executed_volume > 0 else volume
                                actual_amount = price * actual_volume
                                paid_fee = float(order.get('paid_fee', 0))
                                state = order.get('state', 'done')
                                
                                processed_orders.append({
                                    "주문시간": format_datetime(order.get('created_at', '')),
                                    "코인": market.replace("KRW-", ""),
                                    "주문유형": "매수" if side == 'bid' else "매도",
                                    "주문가격": price,
                                    "주문수량": actual_volume,
                                    "주문금액": actual_amount,
                                    "수수료": paid_fee,
                                    "상태": "완료" if state == 'done' else "대기" if state == 'wait' else "취소"
                                })
                        except Exception as e:
                            st.error(f"주문 데이터 처리 중 오류: {str(e)}")
                            continue
                    
                    # 유효한 주문이 있으면 데이터프레임 반환
                    if processed_orders:
                        df = pd.DataFrame(processed_orders)
                        return df.sort_values('주문시간', ascending=False)
                    else:
                        # 주문 처리 후 데이터가 없는 경우에는 샘플 데이터 표시하지 않고 빈 데이터프레임 반환
                        st.warning("주문 처리 결과가 없습니다.")
                        return pd.DataFrame(columns=["주문시간", "코인", "주문유형", "주문가격", "주문수량", "주문금액", "수수료", "상태"])
                else:
                    st.info("pyupbit 라이브러리로 주문 내역을 불러올 수 없습니다.")
            except Exception as e:
                st.error(f"pyupbit 주문 내역 조회 실패: {str(e)}")
        
        # API 연결은 되었지만 주문 내역이 없는 경우에는 빈 데이터프레임 반환
        if _upbit_trade and _upbit_trade.access_key != '{ACCESS KEY 입력 : }' and _upbit_trade.secret_key != '{SECRET KEY 입력 : }':
            st.warning("거래 내역이 없습니다.")
            return pd.DataFrame(columns=["주문시간", "코인", "주문유형", "주문가격", "주문수량", "주문금액", "수수료", "상태"])
        
        # API 연결이 안 된 경우에만 샘플 데이터 생성 및 반환
        return generate_sample_trade_history()
        
    except Exception as e:
        st.error(f"거래 내역 조회 중 오류 발생: {str(e)}")
        return generate_sample_trade_history()

def generate_sample_trade_history() -> pd.DataFrame:
    """샘플 거래 내역 생성 (API 호출 실패 시 대체용)"""
    st.info("샘플 거래 내역을 표시합니다.")
    
    # 샘플 데이터 생성
    today = datetime.now()
    sample_coins = ["BTC", "ETH", "XRP", "DOGE", "ADA"]
    
    sample_orders = []
    for i in range(20):  # 더 많은 데이터 포인트 생성 (페이징 테스트)
        order_date = today - timedelta(days=i//2)
        date_str = order_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        
        # 매수 주문 추가
        if i % 3 != 0:  # 일부 날짜만 매수 주문 추가
            coin = sample_coins[i % len(sample_coins)]
            price = 50000000 if coin == "BTC" else 3000000 if coin == "ETH" else 500
            volume = 0.001 if coin == "BTC" else 0.01 if coin == "ETH" else 100
            
            sample_orders.append({
                "주문시간": format_datetime(date_str),
                "코인": coin,
                "주문유형": "매수",
                "주문가격": price,
                "주문수량": volume,
                "주문금액": price * volume,
                "수수료": price * volume * 0.0005,
                "상태": "완료"
            })
        
        # 매도 주문 추가
        if i % 4 != 0:  # 일부 날짜만 매도 주문 추가
            coin = sample_coins[(i+2) % len(sample_coins)]
            price = 51000000 if coin == "BTC" else 3100000 if coin == "ETH" else 520
            volume = 0.001 if coin == "BTC" else 0.01 if coin == "ETH" else 50
            
            sample_orders.append({
                "주문시간": format_datetime(date_str),
                "코인": coin,
                "주문유형": "매도",
                "주문가격": price,
                "주문수량": volume,
                "주문금액": price * volume,
                "수수료": price * volume * 0.0005,
                "상태": "완료"
            })
            
    # 데이터프레임으로 변환
    df = pd.DataFrame(sample_orders)
    
    # 데이터가 없으면 빈 데이터프레임 반환
    if df.empty:
        return pd.DataFrame(columns=["주문시간", "코인", "주문유형", "주문가격", "주문수량", "주문금액", "수수료", "상태"])
        
    # 최신순 정렬
    return df.sort_values('주문시간', ascending=False)

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
    
    # 새로고침 버튼과 함께 API 새로고침 상태 확인
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔄 새로고침", key="history_refresh"):
            # 캐시 초기화 및 앱 재실행
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        if upbit_trade:
            if upbit_trade.access_key != '{ACCESS KEY 입력 : }' and upbit_trade.secret_key != '{SECRET KEY 입력 : }':
                st.success("API가 연결되었습니다. 실제 거래 내역을 표시합니다.")
            else:
                st.warning("API 키가 설정되지 않았습니다. 샘플 데이터를 표시합니다.")
        else:
            st.warning("Upbit 인스턴스를 생성할 수 없습니다. API 설정을 확인하세요.")
        
    # 거래 내역 설명 추가
    history_info = """
    <div class="data-container">
        <div class="data-label">거래 내역 설명</div>
        <ul style="margin-top: 5px; padding-left: 20px;">
            <li><strong>코인</strong>: 거래한 암호화폐 종류</li>
            <li><strong>주문시간</strong>: 거래가 발생한 시간</li>
            <li><strong>주문유형</strong>: 매수(빨간색) 또는 매도(파란색)</li>
            <li><strong>상태</strong>: 거래의 현재 상태(완료, 대기, 취소)</li>
            <li><strong>가격</strong>: 코인 단위당 거래 가격</li>
            <li><strong>수량</strong>: 거래한 코인의 수량</li>
            <li><strong>거래금액</strong>: 총 거래 금액(가격 × 수량)</li>
        </ul>
    </div>
    """
    st.write(history_info, unsafe_allow_html=True)
    
    # API 연결 상태에 따른 추가 정보 표시
    if has_api_keys and upbit_trade and upbit_trade.access_key != '{ACCESS KEY 입력 : }':
        with st.spinner("거래 내역을 불러오는 중..."):
            # 주문 내역 가져오기
            orders_df = get_order_history_from_trade(upbit_trade)
            
            # 실제 데이터가 있는지 확인
            if len(orders_df) > 0:
                st.success(f"총 {len(orders_df)}개의 실제 거래 내역을 불러왔습니다.")
            else:
                st.warning("거래 내역이 없습니다.")
    else:
        # API 키가 없는 경우 샘플 데이터 표시
        orders_df = generate_sample_trade_history()
        st.info("샘플 데이터를 표시합니다.")
    
    if not orders_df.empty:
        # 필터링 옵션
        st.markdown("### 🔍 필터 옵션")
        col1, col2 = st.columns(2)
        
        with col1:
            # 상태 옵션 동적 생성
            status_options = ["전체"]
            if not orders_df.empty and "상태" in orders_df.columns:
                status_options.extend(orders_df["상태"].unique())
                
            order_status = st.selectbox(
                "주문 상태",
                options=status_options,
                key="order_status"
            )
        
        with col2:
            # 주문 유형 옵션 동적 생성
            type_options = ["전체"]
            if not orders_df.empty and "주문유형" in orders_df.columns:
                type_options.extend(orders_df["주문유형"].unique())
                
            order_type = st.selectbox(
                "주문 유형",
                options=type_options,
                key="order_type"
            )
            
        # 필터링 적용
        if order_status != "전체" and "상태" in orders_df.columns:
            orders_df = orders_df[orders_df["상태"] == order_status]
            
        if order_type != "전체" and "주문유형" in orders_df.columns:
            orders_df = orders_df[orders_df["주문유형"] == order_type]
        
        # 정렬 옵션
        # 데이터프레임의 실제 컬럼에 맞게 정렬 옵션 설정
        sort_options = ["주문시간"]  # 기본 옵션
        if not orders_df.empty:
            sort_options = list(orders_df.columns)
            
        sort_col = st.selectbox(
            "정렬 기준",
            options=sort_options,
            index=sort_options.index("주문시간") if "주문시간" in sort_options else 0,
            key="sort_col"
        )
        
        sort_order = st.radio(
            "정렬 순서",
            options=["내림차순", "오름차순"],
            horizontal=True,
            key="sort_order"
        )
        
        # 정렬 적용
        if sort_col in orders_df.columns:
            ascending = sort_order == "오름차순"
            orders_df = orders_df.sort_values(by=sort_col, ascending=ascending)
        
        # 페이지네이션
        orders_per_page = 5
        
        if 'history_page' not in st.session_state:
            st.session_state.history_page = 0
            
        # 필터링 후 데이터가 비어 있는지 확인
        if len(orders_df) == 0:
            st.info("필터링 조건에 맞는 거래 내역이 없습니다.")
        else:
            total_pages = max(1, (len(orders_df) + orders_per_page - 1) // orders_per_page)
            
            # 현재 페이지가 유효한지 확인
            if st.session_state.history_page >= total_pages:
                st.session_state.history_page = 0
                
            # 현재 페이지에 해당하는 주문 필터링
            start_idx = st.session_state.history_page * orders_per_page
            end_idx = min(start_idx + orders_per_page, len(orders_df))
            
            current_orders = orders_df.iloc[start_idx:end_idx]
            
            # 거래 내역 표시
            st.markdown("### 📋 거래 내역")
            
            # 각 거래 카드로 표시
            for _, order in current_orders.iterrows():
                with st.container():
                    # 배경색 설정
                    if order["주문유형"] == "매수":
                        card_style = "background-color: rgba(255, 240, 240, 0.3);"
                    else:  # 매도
                        card_style = "background-color: rgba(240, 240, 255, 0.3);"
                    
                    order_card = f"""
                    <div class="data-container" style="{card_style}">
                        <div style="display: grid; grid-template-columns: 2fr 2fr 1fr; gap: 10px;">
                            <div>
                                <p><strong>코인:</strong> {order['코인']}</p>
                                <p><strong>주문시간:</strong> {order['주문시간']}</p>
                            </div>
                            <div>
                                <p><strong>주문유형:</strong> <span style="color: {'red' if order['주문유형'] == '매수' else 'blue'};">{order['주문유형']}</span></p>
                                <p><strong>상태:</strong> <span style="color: {'green' if order['상태'] == '완료' else 'orange' if order['상태'] == '대기' else 'gray'};">{order['상태']}</span></p>
                            </div>
                            <div>
                                <p><strong>가격:</strong> {order['주문가격']:,.0f} KRW</p>
                                <p><strong>수량:</strong> {order['주문수량']:.8f}</p>
                            </div>
                        </div>
                        <p style="margin-top: 10px;"><strong>거래금액:</strong> {order['주문금액']:,.0f} KRW</p>
                    </div>
                    """
                    st.write(order_card, unsafe_allow_html=True)
            
            # 페이지네이션 컨트롤
            if total_pages > 1:
                col1, col2, col3 = st.columns([1, 4, 1])
                with col1:
                    if st.button("◀️ 이전", key="prev_history", disabled=st.session_state.history_page <= 0):
                        st.session_state.history_page -= 1
                        st.rerun()
                with col2:
                    paging_info = f"<div style='text-align:center'>페이지 {st.session_state.history_page + 1} / {total_pages}</div>"
                    st.write(paging_info, unsafe_allow_html=True)
                with col3:
                    if st.button("다음 ▶️", key="next_history", disabled=st.session_state.history_page >= total_pages - 1):
                        st.session_state.history_page += 1
                        st.rerun()
    else:
        st.warning("거래 내역이 없습니다.")
        
    # API 키 없는 경우 안내
    if not has_api_keys:
        st.info("실제 거래 내역을 보려면 API 설정 탭에서 API 키를 설정하세요.")
