import jwt
import hashlib
import os
import requests
import uuid
from urllib.parse import urlencode, unquote

import pyupbit

from datetime import datetime, timedelta
import time

class Trade:
    def __init__(self, access_key=None, secret_key=None):
        self.access_key = access_key if access_key else '{ACCESS KEY 입력 : }'
        self.secret_key = secret_key if secret_key else '{SECRET KEY 입력 : }'
        self.server_url = 'https://api.upbit.com'
        
        # API 키 유효성 상태
        self.is_valid = False
        
        try:
            if self.access_key != '{ACCESS KEY 입력 : }' and self.secret_key != '{SECRET KEY 입력 : }':
                # pyupbit 인스턴스 생성
                self.upbit = pyupbit.Upbit(access_key, secret_key)
                # 간단한 유효성 검사
                try:
                    balance = self.upbit.get_balance("KRW")
                    if balance is not None:
                        self.is_valid = True
                    else:
                        print("⚠️ 경고: API 키 인증 실패")
                except Exception as e:
                    print(f"⚠️ 경고: API 인증 중 오류 발생: {e}")
            else:
                self.upbit = None
                print("⚠️ 경고: 실제 API 키가 설정되지 않았습니다. 일부 기능이 제한될 수 있습니다.")
        except Exception as e:
            self.upbit = None
            print(f"⚠️ 경고: 업비트 API 초기화 중 오류: {e}")
    
    def get_order_history(self, ticker_or_uuid="", state=None, page=1, limit=100):
        """주문 내역 조회 (개선된 버전)
        
        Args:
            ticker_or_uuid (str): 티커명 또는 주문 UUID (빈 값: 전체 주문 조회)
            state (str): 주문 상태 (wait, done, cancel)
            page (int): 페이지 번호
            limit (int): 요청 개수 (최대 100)
            
        Returns:
            list: 주문 내역 목록
        """
        if not self.is_valid or not self.upbit:
            print("유효한 API 키가 설정되지 않았습니다.")
            return []
            
        try:
            # 1. pyupbit 라이브러리 사용 시도
            orders = []
            
            # 상태가 지정되지 않은 경우 모든 상태 조회
            states = [state] if state else ["wait", "done", "cancel"]
            
            for current_state in states:
                try:
                    # pyupbit.get_order 직접 호출
                    result = self.upbit.get_order(ticker_or_uuid, state=current_state, limit=limit)
                    
                    if isinstance(result, list):
                        orders.extend(result)
                    elif isinstance(result, dict) and result:  # 딕셔너리이고 비어있지 않은 경우
                        orders.append(result)
                except Exception as e:
                    print(f"{current_state} 상태 주문 조회 중 오류: {str(e)}")
                    continue
                    
            if orders:
                return orders
                
            # 2. 직접 API 호출 시도 (fallback)
            return self._get_orders_direct_api(ticker_or_uuid, state, limit)
            
        except Exception as e:
            print(f"주문 내역 조회 중 오류: {str(e)}")
            # 3. 에러 발생 시 직접 API 호출 시도
            return self._get_orders_direct_api(ticker_or_uuid, state, limit)
    
    def _get_orders_direct_api(self, ticker_or_uuid=None, state=None, limit=100):
        """직접 API를 호출하여 주문 내역 조회"""
        try:
            query = {'limit': limit}
            
            # UUID인 경우와 티커인 경우 구분
            if ticker_or_uuid:
                if len(ticker_or_uuid) >= 30:  # UUID로 추정
                    query['uuid'] = ticker_or_uuid
                else:  # 티커로 추정
                    query['market'] = ticker_or_uuid
            
            if state:
                query['state'] = state
                
            query_string = urlencode(query).encode()
            
            m = hashlib.sha512()
            m.update(query_string)
            query_hash = m.hexdigest()
            
            payload = {
                'access_key': self.access_key,
                'nonce': str(uuid.uuid4()),
                'query_hash': query_hash,
                'query_hash_alg': 'SHA512'
            }
            
            jwt_token = jwt.encode(payload, self.secret_key)
            # JWT 인코딩 결과가 bytes인 경우 문자열로 변환
            if isinstance(jwt_token, bytes):
                jwt_token = jwt_token.decode('utf-8')
                
            authorize_token = f'Bearer {jwt_token}'
            headers = {'Authorization': authorize_token}
            
            response = requests.get(f"{self.server_url}/v1/orders", params=query, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API 요청 실패 (HTTP {response.status_code}): {response.text}")
                return []
        except Exception as e:
            print(f"직접 API 호출 중 오류: {e}")
            return []
    
    def orders_status(self, orderid): 
        """개별 주문 상세 조회"""
        if not self.is_valid:
            return {}
            
        try:
            query = {'uuid': orderid}
            query_string = urlencode(query).encode()
            
            m = hashlib.sha512()
            m.update(query_string)
            query_hash = m.hexdigest()
            
            payload = {
                'access_key': self.access_key,
                'nonce': str(uuid.uuid4()),
                'query_hash': query_hash,
                'query_hash_alg': 'SHA512'
            }
            
            jwt_token = jwt.encode(payload, self.secret_key)
            # JWT 인코딩 결과가 bytes인 경우 문자열로 변환
            if isinstance(jwt_token, bytes):
                jwt_token = jwt_token.decode('utf-8')
                
            authorize_token = f'Bearer {jwt_token}'
            headers = {'Authorization': authorize_token}
            
            response = requests.get(f"{self.server_url}/v1/order", params=query, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"주문 상세 조회 실패 (HTTP {response.status_code}): {response.text}")
                return {}
        except Exception as e:
            print(f"주문 상세 조회 중 오류: {e}")
            return {}
    
    def get_balance(self, ticker): 
        """특정 코인 잔고 조회"""
        if not self.is_valid or not self.upbit:
            return 0
            
        try:
            return self.upbit.get_balance(ticker)
        except Exception as e:
            print(f"잔고 조회 실패: {e}")
            try:
                # 직접 API 호출 시도
                query = {}
                query_string = urlencode(query).encode()
                
                m = hashlib.sha512()
                m.update(query_string)
                query_hash = m.hexdigest()
                
                payload = {
                    'access_key': self.access_key,
                    'nonce': str(uuid.uuid4()),
                    'query_hash': query_hash,
                    'query_hash_alg': 'SHA512'
                }
                
                jwt_token = jwt.encode(payload, self.secret_key)
                if isinstance(jwt_token, bytes):
                    jwt_token = jwt_token.decode('utf-8')
                    
                authorize_token = f'Bearer {jwt_token}'
                headers = {'Authorization': authorize_token}
                
                response = requests.get(f"{self.server_url}/v1/accounts", headers=headers)
                
                if response.status_code == 200:
                    accounts = response.json()
                    for account in accounts:
                        if account['currency'] == ticker.split('-')[-1]:
                            return float(account['balance'])
                    return 0
                else:
                    return 0
            except Exception:
                return 0
    
    def get_current_price(self, ticker): 
        """특정 코인 현재 시세 조회"""
        try:
            return pyupbit.get_current_price(ticker)
        except Exception as e:
            print(f"현재가 조회 실패: {e}")
            return 0
    
    def get_order(self, orderid): 
        """특정 주문 정보 조회"""
        return self.orders_status(orderid)
    
    def get_ohlcv(self, ticker, interval, count): 
        """특정 코인 차트 조회"""
        try:
            return pyupbit.get_ohlcv(ticker, interval=interval, count=count)
        except Exception as e:
            print(f"차트 데이터 조회 실패: {e}")
            return None
    
    def get_market_all(self): 
        """모든 코인 시세 조회"""
        try:
            url = "https://api.upbit.com/v1/market/all"
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"시장 데이터 조회 실패 (HTTP {response.status_code})")
                return []
        except Exception as e:
            print(f"시장 데이터 조회 중 오류: {e}")
            return []
    
    def get_market_detail(self, market): 
        """특정 코인 상세 정보 조회"""
        try:
            return pyupbit.get_market_detail(market)
        except Exception as e:
            print(f"시장 상세 정보 조회 실패: {e}")
            return {}
    
    def buy_market_order(self, ticker, amount): 
        """시장가 매수 주문"""
        if not self.is_valid or not self.upbit:
            print("유효한 API 키가 설정되지 않아 주문을 실행할 수 없습니다.")
            return None
            
        try:
            result = self.upbit.buy_market_order(ticker, amount)
            print(f"시장가 매수 주문: {ticker}, {amount}KRW")
            return result
        except Exception as e:
            print(f"시장가 매수 주문 실패: {e}")
            return None


    def sell_market_order(self, ticker, volume=None): 
        """시장가 매도 주문"""
        if not self.is_valid or not self.upbit:
            print("유효한 API 키가 설정되지 않아 주문을 실행할 수 없습니다.")
            return None
            
        try:
            if volume is None:
                # 전량 매도
                available_volume = self.upbit.get_balance(ticker)
                if available_volume > 0:
                    result = self.upbit.sell_market_order(ticker, available_volume)
                    print(f"전량 시장가 매도 주문: {ticker}, {available_volume}{ticker.split('-')[1]}")
                    return result
                else:
                    print(f"매도할 {ticker} 수량이 없습니다.")
                    return None
            else:
                # 지정 수량 매도
                result = self.upbit.sell_market_order(ticker, volume)
                print(f"시장가 매도 주문: {ticker}, {volume}{ticker.split('-')[1]}")
                return result
        except Exception as e:
            print(f"시장가 매도 주문 실패: {e}")
            return None

    def buy_limit_order(self, ticker, price, volume): 
        """지정가 매수 주문"""
        if not self.is_valid or not self.upbit:
            print("유효한 API 키가 설정되지 않아 주문을 실행할 수 없습니다.")
            return None
            
        try:
            result = self.upbit.buy_limit_order(ticker, price, volume)
            print(f"지정가 매수 주문: {ticker}, 가격: {price}KRW, 수량: {volume}")
            return result
        except Exception as e:
            print(f"지정가 매수 주문 실패: {e}")
            return None

    def sell_limit_order(self, ticker, price, volume=None): 
        """지정가 매도 주문"""
        if not self.is_valid or not self.upbit:
            print("유효한 API 키가 설정되지 않아 주문을 실행할 수 없습니다.")
            return None
            
        try:
            if volume is None:
                # 전량 매도
                available_volume = self.upbit.get_balance(ticker)
                if available_volume > 0:
                    result = self.upbit.sell_limit_order(ticker, price, available_volume)
                    print(f"전량 지정가 매도 주문: {ticker}, 가격: {price}KRW, 수량: {available_volume}")
                    return result
                else:
                    print(f"매도할 {ticker} 수량이 없습니다.")
                    return None
            else:
                # 지정 수량 매도
                result = self.upbit.sell_limit_order(ticker, price, volume)
                print(f"지정가 매도 주문: {ticker}, 가격: {price}KRW, 수량: {volume}")
                return result
        except Exception as e:
            print(f"지정가 매도 주문 실패: {e}")
            return None

    def cancel_order(self, uuid): 
        """주문 취소"""
        if not self.is_valid or not self.upbit:
            print("유효한 API 키가 설정되지 않아 주문 취소를 실행할 수 없습니다.")
            return None
            
        try:
            result = self.upbit.cancel_order(uuid)
            print(f"주문 취소: {uuid}")
            return result
        except Exception as e:
            print(f"주문 취소 실패: {e}")
            return None

    def Strategy(self, ticker, k):
        df=pyupbit.get_ohlcv(ticker, interval="day", count=200)
        df['range']=df['high']-df['low']
        df['target']=df['open']+df['range'].shift(1)
        df['bull']=df['open']>df['target']
        df['ma5']=df['close'].rolling(window=5).mean()
        df['buy']=df['bull']&df['close']>df['ma5']
        df['sell']=df['bull']&df['close']<df['ma5']

        if df['buy'].iloc[-1]:
            return pyupbit.buy_limit(ticker, k)
        elif df['sell'].iloc[-1]:
            return pyupbit.sell_limit(ticker, k)
    
    def run(self):
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                print(e)
                time.sleep(1) 
    
    def schedule_job(self):
        schedule.every(1).seconds.do(self.run) 
    
    def start(self):
        self.schedule_job()
        self.run()
    
    def auto_trade(self, ticker, invest_amount, strategy="vb", k=0.5): # 자동 매매 실행
        """
        자동 매매 실행
    
        Args:
            ticker (str): 코인 티커 (예: "KRW-BTC")
            invest_amount (float): 투자 금액(KRW)
            strategy (str, optional): 전략 선택 ("vb": 변동성 돌파)
            k (float, optional): 변동성 돌파 전략의 k값
        
        Returns:
            dict: 주문 결과
        """
        try:
            # 현재 시간 확인
            now = datetime.now()
        
            if strategy == "vb":
                # 변동성 돌파 전략
                df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
            
                # 변동성 계산
                prev_range = df['high'].iloc[-2] - df['low'].iloc[-2]
                target_price = df['open'].iloc[-1] + (prev_range * k)
            
                # 현재가 확인
                current_price = pyupbit.get_current_price(ticker)
            
                # 매수 조건: 현재가가 목표가 이상이고, 09:00~20:00 사이
                if (current_price >= target_price) and (9 <= now.hour < 20):
                    # 보유 현금 확인
                    krw_balance = self.upbit.get_balance("KRW")
                
                    # 최소 주문 금액 확인 (최소 5000원)
                    order_amount = min(invest_amount, krw_balance)
                    if order_amount >= 5000:
                        return self.buy_market_order(ticker, order_amount)
                    else:
                        print(f"주문 가능 금액이 부족합니다: {order_amount}KRW")
                        return None
            
                # 매도 조건: 08:50~09:00 사이 전량 매도
                elif (8 == now.hour and now.minute >= 50) or (now.hour == 9 and now.minute < 1):
                    return self.sell_market_order(ticker)
            
                else:
                    print(f"현재 매매 조건 미충족: 현재가 {current_price}, 목표가 {target_price}")
                    return None
            else:
                print(f"지원하지 않는 전략입니다: {strategy}")
                return None
            
        except Exception as e:
            print(f"자동 매매 실행 실패: {e}")
            return None 