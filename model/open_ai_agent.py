import streamlit as st
import asyncio
import sys
import pandas as pd
import json
import logging
import os
import datetime
import traceback
from typing import Dict, List, Optional, Any

from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent, Runner, ModelSettings, function_tool, set_default_openai_key, RunConfig, FunctionTool

# UpbitTrader를 직접 가져옵니다
try:
    from upbit.upbit_trader import UpbitTrader
except ImportError:
    # upbit_trader 모듈이 없는 경우 대체 구현
    class UpbitTrader:
        def __init__(self, access_key, secret_key):
            self.access_key = access_key
            self.secret_key = secret_key
            self.is_valid = False
            
        def get_balance(self, ticker):
            log_error(None, f"UpbitTrader 모듈이 로드되지 않았습니다.")
            return 0

# 로깅 설정
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = os.path.join(LOG_DIR, f"crypto_agent_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# 로거 설정
logger = logging.getLogger("crypto_agent")
logger.setLevel(logging.DEBUG)

# 파일 핸들러
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)

# 스트림 핸들러 (콘솔 출력)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)

# 포맷 설정
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# 핸들러 추가
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# 디버그 모드 설정
def set_debug_mode(enable=True):
    """디버그 모드 설정"""
    if 'debug_mode' not in st.session_state:
        st.session_state.debug_mode = enable
    else:
        st.session_state.debug_mode = enable
    logger.info(f"디버그 모드: {enable}")

# 오류 로깅 및 디버그 정보 표시 함수
def log_error(error, context=None, show_tb=True):
    """오류 로깅 및 디버그 정보 표시"""
    error_msg = f"오류: {str(error)}"
    if context:
        error_msg = f"{context} - {error_msg}"
    
    logger.error(error_msg)
    if show_tb:
        tb = traceback.format_exc()
        logger.error(f"Traceback:\n{tb}")
    
    if st.session_state.get('debug_mode', False):
        st.error(error_msg)
        if show_tb:
            with st.expander("상세 오류 정보"):
                st.code(tb)
    else:
        st.error("오류가 발생했습니다. 자세한 내용은 로그를 확인하세요.")

# 디버그 정보 로깅 함수
def log_info(message, data=None):
    """디버그 정보 로깅"""
    logger.info(message)
    if data:
        logger.debug(f"{message} - 데이터: {json.dumps(data, ensure_ascii=False)}")
    
    if st.session_state.get('debug_mode', False) and data:
        with st.expander(f"디버그 정보: {message}"):
            st.json(data)

# 업비트 인스턴스를 가져오는 함수
def get_upbit_instance():
    """업비트 API 인스턴스를 반환합니다."""
    upbit_access = st.session_state.get('upbit_access_key', '')
    upbit_secret = st.session_state.get('upbit_secret_key', '')
    
    if upbit_access and upbit_secret:
        try:
            import pyupbit
            upbit = pyupbit.Upbit(upbit_access, upbit_secret)
            return upbit
        except Exception as e:
            log_error(e, "업비트 인스턴스 생성 중 오류")
    
    return None

# 업비트 트레이더 인스턴스를 가져오는 함수
def get_upbit_trade_instance():
    """업비트 트레이더 인스턴스를 반환합니다."""
    upbit_access = st.session_state.get('upbit_access_key', '')
    upbit_secret = st.session_state.get('upbit_secret_key', '')
    
    if upbit_access and upbit_secret:
        try:
            trader = UpbitTrader(upbit_access, upbit_secret)
            return trader
        except Exception as e:
            log_error(e, "업비트 트레이더 인스턴스 생성 중 오류")
    
    return None

def get_model_name(model_options):
    if model_options == "claude 3.7 sonnet":
        return "claude-3-7-sonnet-latest"
    elif model_options == "claude 3 haiku":
        return "claude-3-haiku-20240307"
    elif model_options == "gpt 4o mini":
        return "gpt-4o-mini"

# 도구 함수 구현
async def get_available_coins_func(ctx, args=None):
    """
    거래 가능한 코인 목록과 현재 보유 중인 코인 목록을 반환합니다.
    사용자가 매도하려는 경우에는 보유 중인 코인만 표시합니다.
    """
    log_info("get_available_coins 함수 호출")
    
    action_type = ""
    if args and isinstance(args, dict):
        action_type = args.get("action_type", "").lower()  # 'buy' 또는 'sell'
    elif isinstance(args, str):
        try:
            args_dict = json.loads(args)
            action_type = args_dict.get("action_type", "").lower()
        except:
            # 문자열을 JSON으로 파싱할 수 없는 경우 무시
            pass
    
    try:
        upbit = get_upbit_instance()
        
        if upbit:
            log_info("get_available_coins: 유효한 Upbit 인스턴스로 실제 데이터 조회 시도")
            
            # 사용자의 보유 코인 목록 조회
            portfolio_coins = []
            try:
                balances = upbit.get_balances()
                for balance in balances:
                    if balance['currency'] != 'KRW' and float(balance['balance']) > 0:
                        portfolio_coins.append({
                            'ticker': f"KRW-{balance['currency']}",
                            'korean_name': balance['currency'],  # API에서 한글 이름을 따로 제공하지 않음
                            'balance': float(balance['balance']),
                            'avg_buy_price': float(balance['avg_buy_price'])
                        })
            except Exception as e:
                log_error(e, "보유 코인 목록 조회 중 오류 발생")
                # 오류 발생해도 계속 진행
            
            # 매도 목적인 경우, 보유 코인만 반환
            if action_type == "sell":
                log_info("get_available_coins: 매도용 코인 목록 필터링 (보유 코인만)")
                if not portfolio_coins:
                    return json.dumps({
                        "success": True,
                        "message": "현재 보유 중인 코인이 없습니다.",
                        "coins": []
                    }, ensure_ascii=False)
                
                return json.dumps({
                    "success": True,
                    "message": f"보유 중인 코인 {len(portfolio_coins)}개를 찾았습니다.",
                    "coins": portfolio_coins
                }, ensure_ascii=False)
            
            # KRW 마켓 코인 조회
            try:
                import pyupbit
                markets = pyupbit.get_tickers(fiat="KRW")
                market_info = []
                
                # 시장 정보 가져오기
                for market in markets[:20]:  # 상위 20개만 처리 (속도 향상)
                    try:
                        ticker_info = pyupbit.get_current_price(market)
                        if ticker_info:
                            market_info.append({
                                'market': market,
                                'korean_name': market.replace('KRW-', '')
                            })
                    except:
                        continue
            except Exception as e:
                log_error(e, "KRW 마켓 코인 조회 중 오류 발생")
                market_info = []
            
            krw_markets = market_info
            log_info(f"get_available_coins: {len(krw_markets)}개의 KRW 마켓 코인 조회됨")
            
            # 위험 성향에 기반해 추천 코인 필터링 (예시)
            risk_style = st.session_state.get('risk_style', '중립적')
            risk_filters = {
                '보수적': lambda m: m['market'] in ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-ADA', 'KRW-DOGE'],
                '중립적': lambda m: True,  # 모든 코인 허용
                '공격적': lambda m: True   # 모든 코인 허용
            }
            
            filtered_markets = [m for m in krw_markets if risk_filters.get(risk_style, lambda x: True)(m)]
            
            # 결과 제한 (최대 10개)
            result_markets = filtered_markets[:10] if len(filtered_markets) > 10 else filtered_markets
            
            # 결과 형식 변환
            coins = []
            for market in result_markets:
                coins.append({
                    'ticker': market['market'],
                    'korean_name': market['korean_name']
                })
            
            log_info("get_available_coins: 성공")
            return json.dumps({
                "success": True,
                "message": f"거래 가능한 코인 {len(coins)}개를 찾았습니다.",
                "coins": coins,
                "portfolio": portfolio_coins  # 보유 코인 정보 추가
            }, ensure_ascii=False)
            
        else:  # upbit API 인스턴스 없음
            # 데모 데이터 - 연결할 API 키가 없을 때
            log_info("get_available_coins: API 연결 없이 데모 데이터 반환")
            
            # 데모용 보유 코인 목록
            demo_portfolio = [
                {'ticker': 'KRW-BTC', 'korean_name': '비트코인', 'balance': 0.001, 'avg_buy_price': 65000000},
                {'ticker': 'KRW-ETH', 'korean_name': '이더리움', 'balance': 0.05, 'avg_buy_price': 3500000}
            ]
            
            # 매도 목적인 경우, 데모 보유 코인만 반환
            if action_type == "sell":
                return json.dumps({
                    "success": True,
                    "message": "보유 중인 코인 2개를 찾았습니다. (데모 모드)",
                    "coins": demo_portfolio,
                    "is_demo": True
                }, ensure_ascii=False)
            
            # 데모용 거래 가능 코인 목록
            demo_coins = [
                {'ticker': 'KRW-BTC', 'korean_name': '비트코인'},
                {'ticker': 'KRW-ETH', 'korean_name': '이더리움'},
                {'ticker': 'KRW-XRP', 'korean_name': '리플'},
                {'ticker': 'KRW-ADA', 'korean_name': '에이다'},
                {'ticker': 'KRW-DOGE', 'korean_name': '도지코인'},
                {'ticker': 'KRW-SOL', 'korean_name': '솔라나'},
                {'ticker': 'KRW-DOT', 'korean_name': '폴카닷'},
                {'ticker': 'KRW-AVAX', 'korean_name': '아발란체'}
            ]
            
            return json.dumps({
                "success": True, 
                "message": "거래 가능한 코인 8개를 찾았습니다. (데모 모드)",
                "coins": demo_coins,
                "portfolio": demo_portfolio,
                "is_demo": True
            }, ensure_ascii=False)
            
    except Exception as e:
        log_error(e, "get_available_coins 함수 실행 중 오류")
        return json.dumps({
            "success": False,
            "message": f"코인 목록 조회 중 오류 발생: {str(e)}",
            "coins": []
        }, ensure_ascii=False)

async def get_coin_price_info_func(ctx, args):
    """
    코인 가격 정보를 조회합니다.
    ticker: 코인 티커 (예: 'BTC')
    """
    log_info("get_coin_price_info 함수 호출")
    
    # args가 문자열인 경우 파싱
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except:
            error_msg = "매개변수 형식이 잘못되었습니다."
            log_error(None, error_msg, show_tb=False)
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
    
    # 티커 추출
    ticker = args.get("ticker", "").upper()
    
    # 티커가 없으면 오류
    if not ticker:
        error_msg = "티커(ticker) 값이 필요합니다."
        log_error(None, error_msg, show_tb=False)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
    
    # KRW 프리픽스 추가
    if not ticker.startswith("KRW-"):
        ticker = f"KRW-{ticker}"
    
    log_info("get_coin_price_info: 티커 파싱 완료", {"ticker": ticker})
    
    try:
        # pyupbit 사용하여 데이터 조회
        try:
            import pyupbit
            
            # 현재가 조회
            current_price = pyupbit.get_current_price(ticker)
            log_info("get_coin_price_info: 현재가 조회 결과", {"price": current_price})
            
            # 보유량 조회
            upbit = get_upbit_instance()
            balance_info = {"balance": 0, "avg_buy_price": 0}
            
            if upbit:
                coin_currency = ticker.replace("KRW-", "")
                balances = upbit.get_balances()
                for balance in balances:
                    if balance['currency'] == coin_currency:
                        balance_info = {
                            "balance": float(balance['balance']),
                            "avg_buy_price": float(balance['avg_buy_price'])
                        }
                        break
            
            log_info("get_coin_price_info: 잔고 조회 결과", balance_info)
            
            # 일봉 데이터 조회
            df = pyupbit.get_ohlcv(ticker, interval="day", count=7)
            log_info("get_coin_price_info: OHLCV 데이터 조회 성공")
            
            # 데이터 포맷팅
            ohlcv_data = []
            for idx, row in df.iterrows():
                ohlcv_data.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close']),
                    "volume": float(row['volume'])
                })
            
            # 데이터 조합
            result = {
                "success": True,
                "ticker": ticker,
                "current_price": current_price,
                "balance_info": balance_info,
                "ohlcv_data": ohlcv_data
            }
            
            log_info("get_coin_price_info: 성공")
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            error_msg = f"코인 가격 정보 조회 중 오류 발생: {str(e)}"
            log_error(e, error_msg)
            return json.dumps({"success": False, "message": error_msg, "ticker": ticker}, ensure_ascii=False)
            
    except Exception as e:
        error_msg = f"코인 가격 정보 조회 중 예상치 못한 오류: {str(e)}"
        log_error(e, error_msg)
        return json.dumps({"success": False, "message": error_msg, "ticker": ticker}, ensure_ascii=False)

async def buy_coin_func(ctx, args):
    """
    코인 매수 함수
    ticker: 코인 티커 (예: 'BTC')
    price_type: 'market' 또는 'limit'
    amount: 매수량 (원화)
    limit_price: 지정가 주문 시 가격
    """
    try:
        # 로깅 시작
        log_info(f"buy_coin 함수 호출", {"args": args})
        print(f"매수 함수 호출: {args}")
        
        # args가 문자열인 경우 JSON으로 파싱
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError as e:
                error_msg = f"매개변수 파싱 오류: {str(e)}"
                log_error(e, error_msg)
                return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
        
        # 인자 파싱
        parsed_args = {}
        parsed_args["ticker"] = args.get("ticker", "").upper()
        parsed_args["price_type"] = args.get("price_type", "market").lower()
        parsed_args["amount"] = float(args.get("amount", 0))
        parsed_args["limit_price"] = float(args.get("limit_price", 0)) if args.get("limit_price") else None
        
        log_info(f"buy_coin: 파라미터 파싱 완료", parsed_args)
        
        # 티커 검증
        if not parsed_args["ticker"]:
            error_msg = "티커(ticker)가 지정되지 않았습니다."
            log_error(None, error_msg, show_tb=False)
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
        
        # KRW 마켓 프리픽스가 없으면 추가
        ticker = parsed_args["ticker"]
        if not ticker.startswith("KRW-"):
            ticker = f"KRW-{ticker}"
        log_info(f"buy_coin: 코인명 추출", {"ticker": ticker})
        
        # upbit 인스턴스 가져오기
        upbit = get_upbit_instance()
        if not upbit:
            error_msg = "Upbit API 인스턴스를 생성할 수 없습니다. API 키 설정을 확인하세요."
            log_error(None, error_msg, show_tb=False)
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
        log_info(f"buy_coin: 유효한 Upbit 인스턴스 확인")
        
        # 주문 유형 확인
        price_type = parsed_args["price_type"]
        if price_type not in ["market", "limit"]:
            error_msg = f"지원하지 않는 주문 유형: {price_type}. 'market' 또는 'limit'만 사용할 수 있습니다."
            log_error(None, error_msg, show_tb=False)
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
        
        # 금액 검증
        amount = parsed_args["amount"]
        if amount <= 0:
            error_msg = f"유효하지 않은 매수 금액: {amount}. 양수여야 합니다."
            log_error(None, error_msg, show_tb=False)
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
        
        # 전량 매수 여부 확인 (계좌의 원화 잔고와 동일한 경우)
        krw_balance = 0
        try:
            balances = upbit.get_balances()
            for balance in balances:
                if balance['currency'] == 'KRW':
                    krw_balance = float(balance['balance'])
                    break
            
            # 전량 매수로 판단되는 경우 (원화 잔고의 99% 이상 사용)
            if amount >= krw_balance * 0.99:
                # 수수료를 고려하여 99.95%만 사용
                amount = krw_balance * 0.9995
                log_info(f"buy_coin: 전량 매수로 판단됨. 수수료 고려하여 금액 조정", {"original": krw_balance, "adjusted": amount})
        except Exception as e:
            log_error(e, "buy_coin: 원화 잔고 확인 중 오류")
            # 오류가 발생해도 계속 진행 (조정 없이)
        
        order_type = None
        order_result = None
        
        # 마켓 주문과 리밋 주문의 분리 처리
        if price_type == "market":
            log_info(f"buy_coin: 시장가 매수 시도", {"ticker": ticker, "amount": amount})
            print(f"시장가 매수 주문: {ticker}, {amount}KRW")
            order_type = "시장가"
            try:
                order_result = upbit.buy_market_order(ticker, amount)
                log_info(f"buy_coin: 주문 결과", {"result": order_result})
            except Exception as e:
                error_msg = f"시장가 매수 중 오류 발생: {str(e)}"
                log_error(e, error_msg)
                return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
                
        else:  # limit order
            limit_price = parsed_args["limit_price"]
            if not limit_price or limit_price <= 0:
                error_msg = "지정가 주문에는 유효한 'limit_price'가 필요합니다."
                log_error(None, error_msg, show_tb=False)
                return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
            
            # 수량 계산 (금액 / 지정가)
            volume = amount / limit_price
            
            log_info(f"buy_coin: 지정가 매수 시도", {"ticker": ticker, "price": limit_price, "volume": volume})
            print(f"지정가 매수 주문: {ticker}, 가격: {limit_price}KRW, 수량: {volume}")
            order_type = "지정가"
            try:
                order_result = upbit.buy_limit_order(ticker, limit_price, volume)
                log_info(f"buy_coin: 주문 결과", {"result": order_result})
            except Exception as e:
                error_msg = f"지정가 매수 중 오류 발생: {str(e)}"
                log_error(e, error_msg)
                return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
        
        # 주문 결과 반환
        if order_result and 'uuid' in order_result:
            result = {
                'success': True,
                'message': f"{ticker} {order_type} 매수 주문이 접수되었습니다. 주문 ID: {order_result['uuid']}\n주문 체결 결과는 '거래내역' 탭에서 확인하실 수 있습니다.",
                'order_id': order_result['uuid'],
                'order_info': order_result
            }
            return json.dumps(result, ensure_ascii=False)
        else:
            error_msg = f"주문은 성공했으나 주문 ID를 받지 못했습니다.: {order_result}"
            log_error(None, error_msg, show_tb=False)
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
            
    except Exception as e:
        error_msg = f"매수 주문 중 예기치 않은 오류 발생: {str(e)}"
        log_error(e, error_msg)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)

async def sell_coin_func(ctx, args):
    """
    코인 매도 함수
    ticker: 코인 티커 (예: 'BTC')
    price_type: 'market' 또는 'limit'
    amount: 매도량 (코인 수량)
    limit_price: 지정가 주문 시 가격
    """
    try:
        # 로깅 시작
        log_info(f"sell_coin 함수 호출", {"args": args})
        print(f"매도 함수 호출: {args}")
        
        # args가 문자열인 경우 JSON으로 파싱
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError as e:
                error_msg = f"매개변수 파싱 오류: {str(e)}"
                log_error(e, error_msg)
                return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
        
        # 인자 파싱
        parsed_args = {}
        parsed_args["ticker"] = args.get("ticker", "").upper()
        parsed_args["price_type"] = args.get("price_type", "market").lower()
        parsed_args["amount"] = args.get("amount", "")
        parsed_args["limit_price"] = float(args.get("limit_price", 0)) if args.get("limit_price") else None
        
        log_info(f"sell_coin: 파라미터 파싱 완료", parsed_args)
        
        # 티커 검증
        if not parsed_args["ticker"]:
            error_msg = "티커(ticker)가 지정되지 않았습니다."
            log_error(None, error_msg, show_tb=False)
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
        
        # KRW 마켓 프리픽스가 없으면 추가
        ticker = parsed_args["ticker"]
        if not ticker.startswith("KRW-"):
            ticker = f"KRW-{ticker}"
        log_info(f"sell_coin: 코인명 추출", {"ticker": ticker})
        
        # upbit 인스턴스 가져오기
        upbit = get_upbit_instance()
        if not upbit:
            error_msg = "Upbit API 인스턴스를 생성할 수 없습니다. API 키 설정을 확인하세요."
            log_error(None, error_msg, show_tb=False)
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
        log_info(f"sell_coin: 유효한 Upbit 인스턴스 확인")
        
        # 주문 유형 확인
        price_type = parsed_args["price_type"]
        if price_type not in ["market", "limit"]:
            error_msg = f"지원하지 않는 주문 유형: {price_type}. 'market' 또는 'limit'만 사용할 수 있습니다."
            log_error(None, error_msg, show_tb=False)
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
        
        # 보유량 확인 - 포트폴리오 기준으로 확인
        coin_currency = ticker.replace("KRW-", "")
        coin_balance = 0
        try:
            balances = upbit.get_balances()
            for balance in balances:
                if balance['currency'] == coin_currency:
                    coin_balance = float(balance['balance'])
                    break
            
            log_info(f"sell_coin: 코인 잔고 조회", {"ticker": ticker, "balance": coin_balance})
            
            if coin_balance <= 0:
                error_msg = f"{coin_currency} 코인을 보유하고 있지 않습니다. 매도할 수 없습니다."
                log_error(None, error_msg, show_tb=False)
                return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
        except Exception as e:
            error_msg = f"코인 잔고 조회 중 오류 발생: {str(e)}"
            log_error(e, error_msg)
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
        
        # 수량 파싱
        amount = parsed_args["amount"]
        amount_value = None
        
        # 전체 수량 매도인 경우
        if isinstance(amount, str) and amount.lower() in ["all", "전체", "전량"]:
            amount_value = coin_balance
            log_info(f"sell_coin: 전체 매도 요청", {"coin_balance": coin_balance})
        else:
            try:
                amount_value = float(amount)
                # 보유량보다 많은 경우 오류
                if amount_value > coin_balance:
                    error_msg = f"매도 수량({amount_value})이 보유량({coin_balance})보다 많습니다."
                    log_error(None, error_msg, show_tb=False)
                    return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
            except ValueError:
                error_msg = f"유효하지 않은 매도 수량: {amount}. 숫자 또는 'all'로 지정해주세요."
                log_error(None, error_msg, show_tb=False)
                return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
        
        # 유효한 수량인지 확인
        if amount_value <= 0:
            error_msg = f"유효하지 않은 매도 수량: {amount_value}. 양수여야 합니다."
            log_error(None, error_msg, show_tb=False)
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
        
        order_type = None
        order_result = None
        
        # 마켓 주문과 리밋 주문의 분리 처리
        if price_type == "market":
            log_info(f"sell_coin: 시장가 매도 시도", {"ticker": ticker, "amount": amount_value})
            print(f"시장가 매도 주문: {ticker}, {amount_value}BTC")
            order_type = "시장가"
            try:
                order_result = upbit.sell_market_order(ticker, amount_value)
                log_info(f"sell_coin: 주문 결과", {"result": order_result})
            except Exception as e:
                error_msg = f"시장가 매도 중 오류 발생: {str(e)}"
                log_error(e, error_msg)
                return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
                
        else:  # limit order
            limit_price = parsed_args["limit_price"]
            if not limit_price or limit_price <= 0:
                error_msg = "지정가 주문에는 유효한 'limit_price'가 필요합니다."
                log_error(None, error_msg, show_tb=False)
                return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
            
            log_info(f"sell_coin: 지정가 매도 시도", {"ticker": ticker, "price": limit_price, "amount": amount_value})
            print(f"지정가 매도 주문: {ticker}, 가격: {limit_price}KRW, 수량: {amount_value}")
            order_type = "지정가"
            try:
                order_result = upbit.sell_limit_order(ticker, limit_price, amount_value)
                log_info(f"sell_coin: 주문 결과", {"result": order_result})
            except Exception as e:
                error_msg = f"지정가 매도 중 오류 발생: {str(e)}"
                log_error(e, error_msg)
                return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
        
        # 주문 결과 반환
        if order_result and 'uuid' in order_result:
            result = {
                'success': True,
                'message': f"{ticker} {order_type} 매도 주문이 접수되었습니다. 주문 ID: {order_result['uuid']}\n주문 체결 결과는 '거래내역' 탭에서 확인하실 수 있습니다.",
                'order_id': order_result['uuid'],
                'order_info': order_result
            }
            return json.dumps(result, ensure_ascii=False)
        else:
            error_msg = f"주문은 성공했으나 주문 ID를 받지 못했습니다.: {order_result}"
            log_error(None, error_msg, show_tb=False)
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
            
    except Exception as e:
        error_msg = f"매도 주문 중 예기치 않은 오류 발생: {str(e)}"
        log_error(e, error_msg)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)

async def check_order_status_func(ctx, args):
    """
    주문 상태를 확인합니다.
    """
    function_name = "check_order_status"
    log_info(f"{function_name} 함수 호출", {"args": args})
    
    try:
        args_dict = json.loads(args)
        order_id = args_dict.get('order_id', '')
        log_info(f"{function_name}: 파라미터 파싱 완료", {"order_id": order_id})
        
        st.write(f"주문 상태를 확인하는 중...")
        upbit_trade = get_upbit_trade_instance()
        
        if upbit_trade and upbit_trade.is_valid:
            log_info(f"{function_name}: 유효한 Upbit 인스턴스 확인")
            # 주문 상태 조회
            order_result = upbit_trade.get_order(order_id)
            log_info(f"{function_name}: 주문 조회 결과", {"result": order_result})
            
            if order_result and 'uuid' in order_result:
                # 주문 정보 가공
                order_info = {
                    'order_id': order_result['uuid'],
                    'status': order_result['state'],
                    'side': '매수' if order_result['side'] == 'bid' else '매도',
                    'price': float(order_result['price']) if order_result['price'] else None,
                    'volume': float(order_result['volume']) if order_result['volume'] else None,
                    'executed_volume': float(order_result['executed_volume']) if order_result['executed_volume'] else 0,
                    'remaining_volume': float(order_result['remaining_volume']) if order_result['remaining_volume'] else 0,
                    'created_at': order_result['created_at'],
                    'market': order_result['market'],
                    'order_type': order_result['ord_type']
                }
                
                # 주문 상태 한글화
                status_map = {
                    'wait': '대기',
                    'watch': '예약',
                    'done': '완료',
                    'cancel': '취소'
                }
                order_info['status_korean'] = status_map.get(order_result['state'], order_result['state'])
                
                # 체결 여부 및 체결률 계산
                if order_info['executed_volume'] > 0:
                    order_info['is_executed'] = True
                    if order_info['volume'] > 0:
                        order_info['execution_rate'] = (order_info['executed_volume'] / order_info['volume']) * 100
                    else:
                        order_info['execution_rate'] = 0
                else:
                    order_info['is_executed'] = False
                    order_info['execution_rate'] = 0
                
                log_info(f"{function_name}: 주문 정보 가공 완료", {"processed_info": order_info})
                
                result = {
                    'success': True,
                    'message': f"주문 조회 성공: {order_info['status_korean']}",
                    'order_info': order_info
                }
                return json.dumps(result, ensure_ascii=False)
            else:
                log_info(f"{function_name}: 주문 조회 실패", {"order_id": order_id})
                result = {
                    'success': False,
                    'message': f"주문 조회 실패: {order_result}",
                    'order_info': None
                }
                return json.dumps(result, ensure_ascii=False)
        
        # API 키가 없거나 유효하지 않은 경우
        log_info(f"{function_name}: API 키 없음 또는 유효하지 않음")
        result = {
            'success': False,
            'message': "API 키가 설정되지 않았거나 유효하지 않습니다. API 설정 페이지에서 키를 확인해주세요.",
            'order_info': None,
            'is_demo': True
        }
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        log_error(e, f"{function_name} 함수 실행 중 오류 발생")
        result = {
            'success': False,
            'message': f"주문 상태 확인 중 오류 발생: {str(e)}",
            'order_info': None
        }
        return json.dumps(result, ensure_ascii=False)

# 도구 스키마 정의
GET_AVAILABLE_COINS_SCHEMA = {
    "type": "object",
    "properties": {},
    "required": [],
    "additionalProperties": False
}

GET_COIN_PRICE_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "조회할 코인의 티커 (예: 'KRW-BTC' 또는 'BTC')"
        }
    },
    "required": ["ticker"],
    "additionalProperties": False
}

BUY_COIN_SCHEMA = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "구매할 코인의 티커 (예: 'KRW-BTC' 또는 'BTC')"
        },
        "price": {
            "type": ["number", "null"],
            "description": "지정가 매수 시 주문 가격. null이면 시장가 주문."
        },
        "amount": {
            "type": ["number", "null"],
            "description": "구매할 금액(KRW) 또는 수량. 시장가 주문은 KRW 금액, 지정가 주문은 코인 수량."
        }
    },
    "required": ["ticker", "price", "amount"],
    "additionalProperties": False
}

SELL_COIN_SCHEMA = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "판매할 코인의 티커 (예: 'KRW-BTC' 또는 'BTC')"
        },
        "price": {
            "type": ["number", "null"],
            "description": "지정가 매도 시 주문 가격. null이면 시장가 주문."
        },
        "amount": {
            "type": ["number", "null"],
            "description": "판매할 코인 수량. null이면 전체 보유량 매도."
        }
    },
    "required": ["ticker", "price", "amount"],
    "additionalProperties": False
}

CHECK_ORDER_STATUS_SCHEMA = {
    "type": "object",
    "properties": {
        "order_id": {
            "type": "string",
            "description": "확인할 주문의 ID (UUID)"
        }
    },
    "required": ["order_id"],
    "additionalProperties": False
}

# 도구 함수에 대한 래퍼
async def tool_wrapper(func, ctx, args, retries=2):
    """
    도구 함수 호출에 대한 래퍼 - 오류 처리 및 재시도를 제공
    """
    function_name = func.__name__
    attempt = 0
    last_error = None
    
    while attempt <= retries:
        try:
            if attempt > 0:
                log_info(f"{function_name}: 재시도 {attempt}/{retries}")
                
            return await func(ctx, args)
        except Exception as e:
            last_error = e
            log_error(e, f"{function_name} 함수 실행 중 오류 발생 (시도 {attempt+1}/{retries+1})")
            attempt += 1
            
            # 마지막 시도가 아니면 잠시 대기 후 재시도
            if attempt <= retries:
                await asyncio.sleep(1)  # 1초 대기
    
    # 모든 재시도 실패 시
    log_error(last_error, f"{function_name} 함수 실행 실패 - 최대 재시도 횟수 초과")
    
    # 기본 오류 응답
    error_response = {
        'success': False,
        'message': f"함수 실행 실패: {str(last_error)} (최대 재시도 횟수 초과)",
        'error': str(last_error)
    }
    return json.dumps(error_response, ensure_ascii=False)

# 디버그 모드 토글 함수
async def toggle_debug_mode_func(ctx, args):
    """
    디버그 모드를 켜거나 끕니다.
    """
    function_name = "toggle_debug_mode"
    log_info(f"{function_name} 함수 호출", {"args": args})
    
    try:
        args_dict = json.loads(args)
        enable = args_dict.get('enable', True)
        
        set_debug_mode(enable)
        
        # 현재 실행 환경 정보 수집
        environment_info = {
            'python_version': sys.version,
            'streamlit_version': st.__version__,
            'upbit_api_available': get_upbit_instance() is not None,
            'debug_mode': st.session_state.get('debug_mode', False),
            'session_keys': list(st.session_state.keys()),
        }
        
        result = {
            'success': True,
            'message': f"디버그 모드: {'켜짐' if enable else '꺼짐'}",
            'debug_info': environment_info
        }
        
        # 세션에 디버그 정보 저장
        st.session_state.debug_info = environment_info
        
        if enable:
            # 디버그 모드가 켜져 있으면 디버그 정보 표시
            with st.expander("디버그 정보"):
                st.json(environment_info)
                
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        log_error(e, f"{function_name} 함수 실행 중 오류 발생")
        result = {
            'success': False,
            'message': f"디버그 모드 설정 중 오류 발생: {str(e)}",
            'error': str(e)
        }
        return json.dumps(result, ensure_ascii=False)

# 도구 스키마 정의에 디버그 모드 토글 스키마 추가
TOGGLE_DEBUG_MODE_SCHEMA = {
    "type": "object",
    "properties": {
        "enable": {
            "type": "boolean",
            "description": "디버그 모드 활성화 여부 (true: 켜기, false: 끄기)"
        }
    },
    "required": [],
    "additionalProperties": False
}

# Agent 객체 생성 함수
def create_agent(model_options):
    """
    Agent 객체를 생성합니다.
    """
    # 시작 로그
    log_info(f"Agent 생성 시작", {"model": model_options})
    
    # 디버그 모드 초기화
    if 'debug_mode' not in st.session_state:
        set_debug_mode(False)
    
    # 세션 상태에서 API 키 설정
    if 'openai_key' in st.session_state and st.session_state.openai_key:
        set_default_openai_key(st.session_state.openai_key)
        log_info("OpenAI API 키 설정됨")
    else:
        log_error(None, "OpenAI API 키 설정되지 않음", show_tb=False)
        st.error("OpenAI API 키가 설정되지 않았습니다. API 설정 페이지에서 키를 입력해주세요.")
        return None
    
    # 투자 성향 정보 가져오기
    user_requirement = st.session_state.get('user_requirement', '')
    risk_style = st.session_state.get('risk_style', '중립적')
    trading_period = st.session_state.get('trading_period', '스윙')
    
    log_info("사용자 투자 설정 로드됨", {
        "user_requirement": user_requirement,
        "risk_style": risk_style,
        "trading_period": trading_period
    })
    
    # 이전 메시지 가져오기
    previous_messages = st.session_state.get('messages', [])
    context = ""
    
    # 최근 대화 기록을 context에 추가 (최대 5개 메시지)
    if len(previous_messages) > 1:  # 첫 메시지는 AI 인사말이므로 건너뜀
        context = "이전 대화 내용:\n"
        for i, msg in enumerate(previous_messages[-6:-1]):  # 최근 5개 메시지만
            if msg["role"] == "user":
                context += f"사용자: {msg['content']}\n"
            elif msg["role"] == "assistant":
                context += f"AI: {msg['content']}\n"
        context += "\n"
    
    log_info(f"이전 대화 기록 로드됨", {"message_count": len(previous_messages)})
    
    # 직접 FunctionTool 객체 생성 - 래퍼 함수를 사용하여 오류 처리 강화
    get_available_coins_tool = FunctionTool(
        name="get_available_coins",
        description="거래 가능한 코인 목록을 조회합니다.",
        params_json_schema=GET_AVAILABLE_COINS_SCHEMA,
        on_invoke_tool=lambda ctx, args: tool_wrapper(get_available_coins_func, ctx, args)
    )
    
    get_coin_price_info_tool = FunctionTool(
        name="get_coin_price_info",
        description="특정 코인의 현재 가격 및 보유 수량 정보를 조회합니다.",
        params_json_schema=GET_COIN_PRICE_INFO_SCHEMA,
        on_invoke_tool=lambda ctx, args: tool_wrapper(get_coin_price_info_func, ctx, args)
    )
    
    buy_coin_tool = FunctionTool(
        name="buy_coin",
        description="특정 코인을 구매합니다. 시장가 또는 지정가 매수 주문을 실행합니다.",
        params_json_schema=BUY_COIN_SCHEMA,
        on_invoke_tool=lambda ctx, args: tool_wrapper(buy_coin_func, ctx, args)
    )
    
    sell_coin_tool = FunctionTool(
        name="sell_coin",
        description="특정 코인을 판매합니다. 시장가 또는 지정가 매도 주문을 실행합니다.",
        params_json_schema=SELL_COIN_SCHEMA,
        on_invoke_tool=lambda ctx, args: tool_wrapper(sell_coin_func, ctx, args)
    )
    
    check_order_status_tool = FunctionTool(
        name="check_order_status",
        description="주문 상태를 확인합니다.",
        params_json_schema=CHECK_ORDER_STATUS_SCHEMA,
        on_invoke_tool=lambda ctx, args: tool_wrapper(check_order_status_func, ctx, args)
    )
    
    # 디버그 모드 토글 도구
    toggle_debug_mode_tool = FunctionTool(
        name="toggle_debug_mode",
        description="디버그 모드를 켜거나 끕니다. 개발용 정보를 확인할 수 있습니다.",
        params_json_schema=TOGGLE_DEBUG_MODE_SCHEMA,
        on_invoke_tool=toggle_debug_mode_func
    )
    
    # Agent 생성 - 도구 추가
    tools = [
        get_available_coins_tool,
        get_coin_price_info_tool,
        buy_coin_tool,
        sell_coin_tool,
        check_order_status_tool,
    ]
    
    # 디버그 모드 도구 추가 (개발자용)
    if st.session_state.get('debug_mode', False) or st.session_state.get('dev_mode', False):
        tools.append(toggle_debug_mode_tool)
        log_info("디버그 모드 도구 추가됨")
    
    # 에이전트에 전달할 시스템 지침
    system_prompt = f"""
    당신은 암호화폐 거래 AI 에이전트입니다. 사용자의 요청을 이해하고, 암호화폐 거래를 도와주세요.

    {context}

    현재 사용자의 위험 성향은 '{st.session_state.get('risk_style', '중립적')}'이며, 
    거래 기간은 '{st.session_state.get('trading_period', '스윙')}'입니다.
    사용자의 추가 요구사항: '{st.session_state.get('user_requirement', '')}'

    중요 지침:
    1. 사용자가 매도(판매)를 요청할 때는 반드시 현재 포트폴리오를 먼저 확인하여 보유 중인 코인만 매도할 수 있습니다.
    2. 매도하려는 코인이 '거래가능코인목록'에 있더라도, 해당 코인을 실제로 보유하고 있는지는 반드시 '포트폴리오'를 통해 확인해야 합니다.
    3. '포트폴리오'에 없는 코인은 보유하고 있지 않은 것이므로 매도할 수 없습니다.
    4. 코인 매도 전에 get_coin_price_info 함수를 호출하여 보유량을 확인하세요.
    5. 매수 주문 시에는 사용자의 위험 성향을 고려하여 적절한 금액을 추천하세요.
    6. 매수/매도 주문 후에는 "상태: 대기 중"과 같은 메시지를 표시하지 말고, 대신 "주문이 접수되었습니다. '거래내역' 탭에서 주문 완료 여부를 확인하실 수 있습니다."와 같은 안내 메시지를 제공하세요.
    7. 전량 매수를 요청받은 경우, 수수료(0.05%)를 고려하여 실제 주문 금액을 계산하세요. 총액의 99.95%로 주문하면 수수료 고려 후 정확하게 전액 사용이 가능합니다.
    8. 매도가능한 코인을 안내할 때는 반드시 '포트폴리오' 기준으로 판단하세요. 거래가능코인목록이 아닌 실제 보유 중인 코인만 매도 가능합니다.

    특정 기능을 사용할 때마다 어떤 기능을 사용하는지 사용자에게 알려주세요.
    예를 들어, "거래 가능한 코인 목록을 불러오겠습니다." 등의 메시지를 먼저 표시합니다.
    
    오류가 발생한 경우, 사용자에게 오류 내용을 명확히 설명하고 해결 방법을 제안해주세요.
    API 키 설정 관련 문제는 API 설정 페이지로 안내하세요.

    도구를 사용하여 작업을 완료하세요.
    """
    
    agent = Agent(
        name="Crypto Trading Assistant",
        instructions=system_prompt,
        model=get_model_name(model_options),
        tools=tools,
    )
    
    log_info("Agent 생성 완료", {"model": model_options, "tool_count": len(tools)})
    return agent

async def stream_openai_response(prompt, model_options, conversation_id=None):
    """
    OpenAI Agent를 사용하여 응답을 스트리밍합니다.
    conversation_id를 사용하여 대화 기록을 유지합니다.
    """
    log_info(f"응답 스트리밍 시작", {"model": model_options, "prompt_length": len(prompt)})
    print(f"스트리밍 시작 - 모델: {model_options}, 프롬프트 길이: {len(prompt)}")
    
    # Agent 생성
    agent = create_agent(model_options)
    if not agent:
        error_msg = "API 키 설정이 필요합니다."
        log_error(None, error_msg, show_tb=False)
        print("API 키 없음 - 응답 생성 중단")
        yield error_msg
        return
    
    try:
        # 대화 기록 유지를 위한 RunConfig 생성
        run_config = None
        if conversation_id:
            run_config = RunConfig(
                workflow_name="Crypto Trading Assistant",
                group_id=conversation_id,  # 대화 그룹 ID 설정
            )
            log_info(f"RunConfig 생성됨", {"conversation_id": conversation_id})
            print(f"RunConfig 생성 - 대화ID: {conversation_id}")
        
        # 대화 기록이 있는 경우 full_prompt에 포함
        if len(st.session_state.get('messages', [])) > 1 and prompt:
            full_prompt = f"{prompt}"
        else:
            full_prompt = prompt
        
        log_info(f"Runner.run_streamed 호출 준비 완료")
        print(f"Runner.run_streamed 호출 전")
        
        # 적절한 인자로 run_streamed 호출
        if run_config:
            result = Runner.run_streamed(
                agent, 
                input=full_prompt,
                run_config=run_config
            )
        else:
            result = Runner.run_streamed(
                agent, 
                input=full_prompt
            )
        
        log_info(f"스트리밍 시작됨")
        print(f"스트리밍 시작")
        chunk_count = 0
        
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                chunk_count += 1
                if chunk_count % 10 == 0:  # 10개마다 로그 출력
                    log_info(f"청크 수신 중", {"count": chunk_count})
                    print(f"청크 {chunk_count}개 수신 중")
                yield event.data.delta
            elif event.type == "tool_call" or event.type == "tool_call_event":
                # 도구 호출 이벤트 로깅
                log_info(f"도구 호출 이벤트 발생", {"event_type": event.type, "event_data": str(event.data)})
        
        log_info(f"스트리밍 완료", {"total_chunks": chunk_count})
        print(f"스트리밍 완료 - 총 {chunk_count}개 청크")
                
    except Exception as e:
        error_msg = f"응답 생성 중 오류 발생: {str(e)}"
        log_error(e, "응답 스트리밍 중 오류 발생")
        print(f"ERROR: {error_msg}")
        st.error(error_msg)
        yield error_msg

def stream_response(prompt, model_options):
    """
    비동기 스트리밍 함수를 Streamlit에서 사용할 수 있는 형태로 변환
    """
    async def process_stream():
        response_chunks = []
        async for chunk in stream_openai_response(prompt, model_options):
            response_chunks.append(chunk)
            yield chunk
    
    return process_stream()

# 메인 함수 - 디버그 모드 테스트용
if __name__ == "__main__":
    # 디버그 모드 테스트 코드
    st.title("암호화폐 거래 AI 에이전트 디버그 모드")
    
    # 디버그 모드 토글
    if st.button("디버그 모드 " + ("끄기" if st.session_state.get('debug_mode', False) else "켜기")):
        set_debug_mode(not st.session_state.get('debug_mode', False))
        st.rerun()
    
    st.write(f"현재 디버그 모드: {'켜짐' if st.session_state.get('debug_mode', False) else '꺼짐'}")
    
    # 에이전트 설정
    with st.form("디버그 모드 설정"):
        model_options = st.selectbox(
            "모델 선택",
            ["gpt 4o mini", "claude 3.7 sonnet", "claude 3 haiku"],
            index=0
        )
        
        api_key = st.text_input("OpenAI API 키", type="password")
        if api_key:
            st.session_state.openai_key = api_key
        
        if st.form_submit_button("에이전트 생성"):
            agent = create_agent(model_options)
            if agent:
                st.success("에이전트가 성공적으로 생성되었습니다!")
                st.session_state.agent = agent
            else:
                st.error("에이전트 생성에 실패했습니다.")
    
    # 도구 테스트
    if 'agent' in st.session_state:
        with st.form("도구 테스트"):
            tool_to_test = st.selectbox(
                "테스트할 도구",
                ["get_available_coins", "get_coin_price_info", "buy_coin", "sell_coin", "check_order_status"]
            )
            
            args = {}
            if tool_to_test == "get_coin_price_info":
                args['ticker'] = st.text_input("티커 (예: BTC 또는 KRW-BTC)", "BTC")
            elif tool_to_test == "buy_coin":
                args['ticker'] = st.text_input("티커", "BTC")
                price_type = st.radio("주문 유형", ["시장가", "지정가"])
                if price_type == "지정가":
                    args['price'] = st.number_input("가격", value=50000000)
                args['amount'] = st.number_input("금액 또는 수량", value=10000)
            elif tool_to_test == "sell_coin":
                args['ticker'] = st.text_input("티커", "BTC")
                price_type = st.radio("주문 유형", ["시장가", "지정가"])
                if price_type == "지정가":
                    args['price'] = st.number_input("가격", value=50000000)
                use_all = st.checkbox("전량 매도")
                if not use_all:
                    args['amount'] = st.number_input("수량", value=0.001)
            elif tool_to_test == "check_order_status":
                args['order_id'] = st.text_input("주문 ID (UUID)")
            
            if st.form_submit_button("도구 실행"):
                st.write(f"{tool_to_test} 도구 실행 중...")
                
                # 직접 함수 실행 (테스트용)
                try:
                    import asyncio
                    
                    # 적절한 함수 선택
                    if tool_to_test == "get_available_coins":
                        func = get_available_coins_func
                        args_str = "{}"
                    elif tool_to_test == "get_coin_price_info":
                        func = get_coin_price_info_func
                        args_str = json.dumps({"ticker": args['ticker']})
                    elif tool_to_test == "buy_coin":
                        func = buy_coin_func
                        if price_type == "시장가":
                            args_str = json.dumps({"ticker": args['ticker'], "amount": args['amount']})
                        else:
                            args_str = json.dumps({"ticker": args['ticker'], "price": args['price'], "amount": args['amount']})
                    elif tool_to_test == "sell_coin":
                        func = sell_coin_func
                        if price_type == "시장가":
                            if use_all:
                                args_str = json.dumps({"ticker": args['ticker']})
                            else:
                                args_str = json.dumps({"ticker": args['ticker'], "amount": args['amount']})
                        else:
                            if use_all:
                                args_str = json.dumps({"ticker": args['ticker'], "price": args['price']})
                            else:
                                args_str = json.dumps({"ticker": args['ticker'], "price": args['price'], "amount": args['amount']})
                    elif tool_to_test == "check_order_status":
                        func = check_order_status_func
                        args_str = json.dumps({"order_id": args['order_id']})
                    
                    # 함수 실행
                    result = asyncio.run(func(None, args_str))
                    
                    # 결과 표시
                    st.write("결과:")
                    st.json(json.loads(result))
                except Exception as e:
                    st.error(f"도구 실행 중 오류 발생: {str(e)}")
                    st.code(traceback.format_exc())
    
    # 로그 파일 목록
    st.subheader("로그 파일")
    log_files = [f for f in os.listdir(LOG_DIR) if f.endswith('.log')]
    log_files.sort(reverse=True)  # 최신 파일 먼저
    
    if log_files:
        selected_log = st.selectbox("로그 파일 선택", log_files)
        
        # 선택한 로그 파일 내용 표시
        if selected_log:
            log_path = os.path.join(LOG_DIR, selected_log)
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                
                with st.expander("로그 내용", expanded=True):
                    st.text_area("로그", log_content, height=500)
                    
                # 로그 파일 다운로드 버튼
                st.download_button(
                    "로그 파일 다운로드",
                    log_content,
                    file_name=selected_log,
                    mime="text/plain"
                )
            except Exception as e:
                st.error(f"로그 파일 읽기 실패: {str(e)}")
    else:
        st.write("로그 파일이 없습니다.")