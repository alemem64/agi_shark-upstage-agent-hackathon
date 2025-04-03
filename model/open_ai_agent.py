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

# upbit 관련 모듈 추가
sys.path.append("tools/upbit")
from UPBIT import Trade
from page.api_setting import get_upbit_trade_instance

def get_model_name(model_options):
    if model_options == "claude 3.7 sonnet":
        return "claude-3-7-sonnet-latest"
    elif model_options == "claude 3 haiku":
        return "claude-3-haiku-20240307"
    elif model_options == "gpt 4o mini":
        return "gpt-4o-mini"

# 도구 함수 구현
async def get_available_coins_func(ctx, args):
    """
    거래 가능한 코인 목록을 조회합니다.
    """
    function_name = "get_available_coins"
    log_info(f"{function_name} 함수 호출")
    
    st.write("거래 가능 코인 목록을 불러오는 중...")
    upbit_trade = get_upbit_trade_instance()
    
    try:
        if upbit_trade and upbit_trade.is_valid:
            log_info(f"{function_name}: 유효한 Upbit 인스턴스로 실제 데이터 조회 시도")
            # 실제 데이터 가져오기
            market_info = upbit_trade.get_market_all()
            
            if market_info:
                # KRW 마켓만 필터링
                krw_markets = [item for item in market_info if item['market'].startswith('KRW-')]
                log_info(f"{function_name}: {len(krw_markets)}개의 KRW 마켓 코인 조회됨")
                
                # 결과 포맷팅
                result = []
                for market in krw_markets:
                    result.append({
                        'ticker': market['market'],
                        'korean_name': market.get('korean_name', ''),
                        'english_name': market.get('english_name', '')
                    })
                
                response = json.dumps(result, ensure_ascii=False)
                log_info(f"{function_name}: 성공", {"coin_count": len(result)})
                return response
        
        # API 키가 없거나 유효하지 않은 경우 샘플 데이터 반환
        log_info(f"{function_name}: API 키 없음 또는 유효하지 않음, 샘플 데이터 사용")
        sample_data = [
            {'ticker': 'KRW-BTC', 'korean_name': '비트코인', 'english_name': 'Bitcoin'},
            {'ticker': 'KRW-ETH', 'korean_name': '이더리움', 'english_name': 'Ethereum'},
            {'ticker': 'KRW-XRP', 'korean_name': '리플', 'english_name': 'Ripple'},
            {'ticker': 'KRW-SOL', 'korean_name': '솔라나', 'english_name': 'Solana'},
            {'ticker': 'KRW-DOGE', 'korean_name': '도지코인', 'english_name': 'Dogecoin'}
        ]
        return json.dumps(sample_data, ensure_ascii=False)
    
    except Exception as e:
        log_error(e, f"{function_name} 함수 실행 중 오류 발생")
        # 기본 샘플 데이터 반환
        sample_data = [
            {'ticker': 'KRW-BTC', 'korean_name': '비트코인', 'english_name': 'Bitcoin'},
            {'ticker': 'KRW-ETH', 'korean_name': '이더리움', 'english_name': 'Ethereum'},
            {'ticker': 'KRW-XRP', 'korean_name': '리플', 'english_name': 'Ripple'}
        ]
        return json.dumps(sample_data, ensure_ascii=False)

async def get_coin_price_info_func(ctx, args):
    """
    특정 코인의 현재 가격 및 보유 수량 정보를 조회합니다.
    """
    function_name = "get_coin_price_info"
    log_info(f"{function_name} 함수 호출", {"args": args})
    
    try:
        args_dict = json.loads(args)
        ticker = args_dict.get('ticker', '')
        log_info(f"{function_name}: 티커 파싱 완료", {"ticker": ticker})
        
        st.write(f"{ticker} 가격 및 수량 정보를 불러오는 중...")
        upbit_trade = get_upbit_trade_instance()
        
        if not ticker.startswith('KRW-'):
            old_ticker = ticker
            ticker = f"KRW-{ticker}"
            log_info(f"{function_name}: 티커 형식 변환", {"old": old_ticker, "new": ticker})
            
        coin_name = ticker.split('-')[1]
        
        if upbit_trade and upbit_trade.is_valid:
            log_info(f"{function_name}: 유효한 Upbit 인스턴스 확인, 실제 데이터 조회 시도")
            # 현재가 조회
            current_price = upbit_trade.get_current_price(ticker)
            log_info(f"{function_name}: 현재가 조회 결과", {"ticker": ticker, "price": current_price})
            
            # 보유수량 조회
            coin_balance = upbit_trade.get_balance(coin_name)
            krw_balance = upbit_trade.get_balance("KRW")
            log_info(f"{function_name}: 잔고 조회 결과", {"coin": coin_name, "balance": coin_balance, "krw": krw_balance})
            
            # 일봉 데이터로 24시간 변동률 계산
            try:
                ohlcv = upbit_trade.get_ohlcv(ticker, interval="day", count=2)
                log_info(f"{function_name}: OHLCV 데이터 조회 성공")
                
                if ohlcv is not None and len(ohlcv) > 0:
                    prev_close = ohlcv.iloc[-2]['close'] if len(ohlcv) > 1 else ohlcv.iloc[0]['open']
                    change_rate = ((current_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0
                    
                    result = {
                        'ticker': ticker,
                        'coin_name': coin_name,
                        'current_price': current_price,
                        'change_rate_24h': round(change_rate, 2),
                        'coin_balance': coin_balance,
                        'coin_balance_krw': coin_balance * current_price if coin_balance and current_price else 0,
                        'available_krw': krw_balance
                    }
                    log_info(f"{function_name}: 성공", {"result": result})
                    return json.dumps(result, ensure_ascii=False)
            except Exception as ohlcv_err:
                log_error(ohlcv_err, f"{function_name}: OHLCV 데이터 조회 실패", show_tb=False)
        
        # API 키가 없거나 유효하지 않은 경우 샘플 데이터 반환
        log_info(f"{function_name}: API 키 없음 또는 API 호출 실패, 샘플 데이터 사용")
        sample_prices = {
            'KRW-BTC': 50000000,
            'KRW-ETH': 3000000,
            'KRW-XRP': 500,
            'KRW-SOL': 150000,
            'KRW-DOGE': 100
        }
        
        current_price = sample_prices.get(ticker, 1000)
        change_rate = 2.5 if ticker == 'KRW-BTC' else -1.2 if ticker == 'KRW-ETH' else 0.8
        
        result = {
            'ticker': ticker,
            'coin_name': coin_name,
            'current_price': current_price,
            'change_rate_24h': change_rate,
            'coin_balance': 0.01 if ticker == 'KRW-BTC' else 0.5 if ticker == 'KRW-ETH' else 0,
            'coin_balance_krw': 0.01 * current_price if ticker == 'KRW-BTC' else 0.5 * current_price if ticker == 'KRW-ETH' else 0,
            'available_krw': 1000000
        }
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        log_error(e, f"{function_name} 함수 실행 중 오류 발생")
        
        # 기본 오류 응답
        try:
            coin_name = ticker.split('-')[1] if 'ticker' in locals() else "unknown"
        except:
            coin_name = "unknown"
            
        result = {
            'ticker': ticker if 'ticker' in locals() else "unknown",
            'coin_name': coin_name,
            'current_price': 0,
            'change_rate_24h': 0,
            'coin_balance': 0,
            'coin_balance_krw': 0,
            'available_krw': 0,
            'error': str(e)
        }
        return json.dumps(result, ensure_ascii=False)

async def buy_coin_func(ctx, args):
    """
    특정 코인을 구매합니다. 시장가 또는 지정가 매수 주문을 실행합니다.
    """
    function_name = "buy_coin"
    log_info(f"{function_name} 함수 호출", {"args": args})
    
    try:
        args_dict = json.loads(args)
        ticker = args_dict.get('ticker', '')
        price = args_dict.get('price')
        amount = args_dict.get('amount')
        
        log_info(f"{function_name}: 파라미터 파싱 완료", {"ticker": ticker, "price": price, "amount": amount})
        
        st.write(f"{ticker} 매수 주문을 실행하는 중...")
        upbit_trade = get_upbit_trade_instance()
        
        if not ticker.startswith('KRW-'):
            old_ticker = ticker
            ticker = f"KRW-{ticker}"
            log_info(f"{function_name}: 티커 형식 변환", {"old": old_ticker, "new": ticker})
            
        # amount가 None이면 기본값 설정
        if amount is None:
            amount = 0
            log_info(f"{function_name}: amount가 None, 0으로 설정")
            
        if upbit_trade and upbit_trade.is_valid:
            log_info(f"{function_name}: 유효한 Upbit 인스턴스 확인")
            # KRW 잔고 확인
            krw_balance = upbit_trade.get_balance("KRW")
            log_info(f"{function_name}: KRW 잔고 조회", {"balance": krw_balance})
            
            if amount <= 0:
                log_info(f"{function_name}: 주문 금액이 0 이하", {"amount": amount})
                result = {
                    'success': False,
                    'message': f"주문 실패: 주문 금액은 0보다 커야 합니다.",
                    'order_id': None
                }
                return json.dumps(result, ensure_ascii=False)
                
            if krw_balance < amount and price is None:
                log_info(f"{function_name}: 잔고 부족", {"krw_balance": krw_balance, "amount": amount})
                result = {
                    'success': False,
                    'message': f"주문 실패: 주문 금액({amount}원)이 보유 KRW({krw_balance}원)보다 큽니다.",
                    'order_id': None
                }
                return json.dumps(result, ensure_ascii=False)
            
            # 시장가 주문 실행
            if price is None:
                log_info(f"{function_name}: 시장가 매수 시도", {"ticker": ticker, "amount": amount})
                order_result = upbit_trade.buy_market_order(ticker, amount)
                order_type = "시장가"
            else:
                # 지정가 주문 실행
                log_info(f"{function_name}: 지정가 매수 시도", {"ticker": ticker, "price": price, "amount": amount})
                order_result = upbit_trade.buy_limit_order(ticker, price, amount)
                order_type = "지정가"
            
            log_info(f"{function_name}: 주문 결과", {"result": order_result})
            
            if order_result and 'uuid' in order_result:
                result = {
                    'success': True,
                    'message': f"{ticker} {order_type} 매수 주문 성공",
                    'order_id': order_result['uuid'],
                    'order_info': order_result
                }
                return json.dumps(result, ensure_ascii=False)
            else:
                result = {
                    'success': False,
                    'message': f"{ticker} {order_type} 매수 주문 실패: {order_result}",
                    'order_id': None
                }
                return json.dumps(result, ensure_ascii=False)
        
        # API 키가 없거나 유효하지 않은 경우
        log_info(f"{function_name}: API 키 없음 또는 유효하지 않음")
        result = {
            'success': False,
            'message': "API 키가 설정되지 않았거나 유효하지 않습니다. API 설정 페이지에서 키를 확인해주세요.",
            'order_id': None,
            'is_demo': True
        }
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        log_error(e, f"{function_name} 함수 실행 중 오류 발생")
        result = {
            'success': False,
            'message': f"주문 중 오류 발생: {str(e)}",
            'order_id': None
        }
        return json.dumps(result, ensure_ascii=False)

async def sell_coin_func(ctx, args):
    """
    특정 코인을 판매합니다. 시장가 또는 지정가 매도 주문을 실행합니다.
    """
    function_name = "sell_coin"
    log_info(f"{function_name} 함수 호출", {"args": args})
    
    try:
        args_dict = json.loads(args)
        ticker = args_dict.get('ticker', '')
        price = args_dict.get('price')
        amount = args_dict.get('amount')
        
        log_info(f"{function_name}: 파라미터 파싱 완료", {"ticker": ticker, "price": price, "amount": amount})
        
        st.write(f"{ticker} 매도 주문을 실행하는 중...")
        upbit_trade = get_upbit_trade_instance()
        
        if not ticker.startswith('KRW-'):
            old_ticker = ticker
            ticker = f"KRW-{ticker}"
            log_info(f"{function_name}: 티커 형식 변환", {"old": old_ticker, "new": ticker})
        
        coin_name = ticker.split('-')[1]
        log_info(f"{function_name}: 코인명 추출", {"coin_name": coin_name})
            
        if upbit_trade and upbit_trade.is_valid:
            log_info(f"{function_name}: 유효한 Upbit 인스턴스 확인")
            # 보유 코인 수량 확인
            coin_balance = upbit_trade.get_balance(coin_name)
            log_info(f"{function_name}: 코인 잔고 조회", {"coin": coin_name, "balance": coin_balance})
            
            if coin_balance == 0:
                log_info(f"{function_name}: 코인 잔고 없음", {"coin": coin_name})
                result = {
                    'success': False,
                    'message': f"주문 실패: {coin_name} 보유 수량이 없습니다.",
                    'order_id': None
                }
                return json.dumps(result, ensure_ascii=False)
            
            # 매도 수량이 지정되지 않았거나 보유량보다 많으면 보유량 전체로 설정
            orig_amount = amount
            if amount is None or amount > coin_balance:
                amount = coin_balance
                log_info(f"{function_name}: 매도 수량 조정", {"original": orig_amount, "adjusted": amount})
            
            # 시장가 주문 실행
            if price is None:
                log_info(f"{function_name}: 시장가 매도 시도", {"ticker": ticker, "amount": amount})
                order_result = upbit_trade.sell_market_order(ticker, amount)
                order_type = "시장가"
            else:
                # 지정가 주문 실행
                log_info(f"{function_name}: 지정가 매도 시도", {"ticker": ticker, "price": price, "amount": amount})
                order_result = upbit_trade.sell_limit_order(ticker, price, amount)
                order_type = "지정가"
            
            log_info(f"{function_name}: 주문 결과", {"result": order_result})
            
            if order_result and 'uuid' in order_result:
                result = {
                    'success': True,
                    'message': f"{ticker} {order_type} 매도 주문 성공",
                    'order_id': order_result['uuid'],
                    'order_info': order_result
                }
                return json.dumps(result, ensure_ascii=False)
            else:
                result = {
                    'success': False,
                    'message': f"{ticker} {order_type} 매도 주문 실패: {order_result}",
                    'order_id': None
                }
                return json.dumps(result, ensure_ascii=False)
        
        # API 키가 없거나 유효하지 않은 경우
        log_info(f"{function_name}: API 키 없음 또는 유효하지 않음")
        result = {
            'success': False,
            'message': "API 키가 설정되지 않았거나 유효하지 않습니다. API 설정 페이지에서 키를 확인해주세요.",
            'order_id': None,
            'is_demo': True
        }
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        log_error(e, f"{function_name} 함수 실행 중 오류 발생")
        result = {
            'success': False,
            'message': f"주문 중 오류 발생: {str(e)}",
            'order_id': None
        }
        return json.dumps(result, ensure_ascii=False)

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
            'upbit_api_available': get_upbit_trade_instance() is not None,
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
    
    agent = Agent(
        name="Crypto Trading Assistant",
        instructions=f"""
        암호화폐 거래에 관한 질문에 답변하는 AI 어시스턴트입니다.
        사용자의 투자 성향과 요구사항을 고려하여 도움을 제공합니다.
        
        {context}
        
        사용자 맞춤 지시: {user_requirement}
        위험 성향: {risk_style}
        거래 기간: {trading_period}

        특정 기능을 사용할 때마다 어떤 기능을 사용하는지 사용자에게 알려주세요.
        예를 들어, "거래 가능한 코인 목록을 불러오겠습니다." 등의 메시지를 먼저 표시합니다.
        
        오류가 발생한 경우, 사용자에게 오류 내용을 명확히 설명하고 해결 방법을 제안해주세요.
        API 키 설정 관련 문제는 API 설정 페이지로 안내하세요.
        """,
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