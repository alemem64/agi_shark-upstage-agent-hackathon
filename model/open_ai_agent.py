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
import threading
from datetime import datetime as dt, timedelta

from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent, Runner, ModelSettings, function_tool, set_default_openai_key, RunConfig, WebSearchTool, FunctionTool
from tools.document_parser.document_parser import DocumentParser
from tools.information_extract.informaton_extract import information_extract

# UpbitTrader를 직접 가져옵니다
try:
    from upbit.upbit_trader import UpbitTrader
except ImportError:
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

logger = logging.getLogger("crypto_agent")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

def set_debug_mode(enable=True):
    if 'debug_mode' not in st.session_state:
        st.session_state.debug_mode = enable
    else:
        st.session_state.debug_mode = enable
    logger.info(f"디버그 모드: {enable}")

def log_error(error, context=None, show_tb=True):
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

def log_info(message, data=None):
    logger.info(message)
    if data:
        logger.debug(f"{message} - 데이터: {json.dumps(data, ensure_ascii=False)}")
    if st.session_state.get('debug_mode', False) and data:
        with st.expander(f"디버그 정보: {message}"):
            st.json(data)

def get_upbit_instance():
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

def get_upbit_trade_instance():
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
    return model_options

# 도구 함수 정의
async def get_available_coins_func(ctx, args=None):
    log_info("get_available_coins 함수 호출")
    action_type = ""
    if args and isinstance(args, dict):
        action_type = args.get("action_type", "").lower()
    elif isinstance(args, str):
        try:
            args_dict = json.loads(args)
            action_type = args_dict.get("action_type", "").lower()
        except:
            pass
    
    try:
        upbit = get_upbit_instance()
        if upbit:
            portfolio_coins = []
            try:
                balances = upbit.get_balances()
                for balance in balances:
                    if balance['currency'] != 'KRW' and float(balance['balance']) > 0:
                        portfolio_coins.append({
                            'ticker': f"KRW-{balance['currency']}",
                            'korean_name': balance['currency'],
                            'balance': float(balance['balance']),
                            'avg_buy_price': float(balance['avg_buy_price'])
                        })
            except Exception as e:
                log_error(e, "보유 코인 목록 조회 중 오류 발생")
            
            if action_type == "sell":
                if not portfolio_coins:
                    return json.dumps({"success": True, "message": "보유 중인 코인 없음", "coins": []}, ensure_ascii=False)
                return json.dumps({"success": True, "message": f"보유 코인 {len(portfolio_coins)}개", "coins": portfolio_coins}, ensure_ascii=False)
            
            import pyupbit
            markets = pyupbit.get_tickers(fiat="KRW")[:20]
            market_info = [{"market": m, "korean_name": m.replace('KRW-', '')} for m in markets]
            risk_style = st.session_state.get('risk_style', '중립적')
            risk_filters = {
                '보수적': lambda m: m['market'] in ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-ADA', 'KRW-DOGE'],
                '중립적': lambda m: True,
                '공격적': lambda m: True
            }
            filtered_markets = [m for m in market_info if risk_filters.get(risk_style, lambda x: True)(m)][:10]
            coins = [{"ticker": m['market'], "korean_name": m['korean_name']} for m in filtered_markets]
            return json.dumps({"success": True, "message": f"코인 {len(coins)}개", "coins": coins, "portfolio": portfolio_coins}, ensure_ascii=False)
        else:
            demo_portfolio = [
                {'ticker': 'KRW-BTC', 'korean_name': '비트코인', 'balance': 0.001, 'avg_buy_price': 65000000},
                {'ticker': 'KRW-ETH', 'korean_name': '이더리움', 'balance': 0.05, 'avg_buy_price': 3500000}
            ]
            if action_type == "sell":
                return json.dumps({"success": True, "message": "데모 보유 코인", "coins": demo_portfolio, "is_demo": True}, ensure_ascii=False)
            demo_coins = [
                {'ticker': 'KRW-BTC', 'korean_name': '비트코인'}, {'ticker': 'KRW-ETH', 'korean_name': '이더리움'},
                {'ticker': 'KRW-XRP', 'korean_name': '리플'}, {'ticker': 'KRW-ADA', 'korean_name': '에이다'}
            ]
            return json.dumps({"success": True, "message": "데모 코인", "coins": demo_coins, "portfolio": demo_portfolio, "is_demo": True}, ensure_ascii=False)
    except Exception as e:
        log_error(e, "get_available_coins 오류")
        return json.dumps({"success": False, "message": str(e), "coins": []}, ensure_ascii=False)

async def get_coin_price_info_func(ctx, args):
    log_info("get_coin_price_info 함수 호출")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except:
            return json.dumps({"success": False, "message": "잘못된 매개변수 형식"}, ensure_ascii=False)
    ticker = args.get("ticker", "").upper()
    if not ticker:
        return json.dumps({"success": False, "message": "티커 필요"}, ensure_ascii=False)
    if not ticker.startswith("KRW-"):
        ticker = f"KRW-{ticker}"
    try:
        import pyupbit
        current_price = pyupbit.get_current_price(ticker)
        upbit = get_upbit_instance()
        balance_info = {"balance": 0, "avg_buy_price": 0}
        if upbit:
            coin_currency = ticker.replace("KRW-", "")
            balances = upbit.get_balances()
            for balance in balances:
                if balance['currency'] == coin_currency:
                    balance_info = {"balance": float(balance['balance']), "avg_buy_price": float(balance['avg_buy_price'])}
                    break
        df = pyupbit.get_ohlcv(ticker, interval="day", count=7)
        ohlcv_data = [{"date": idx.strftime("%Y-%m-%d"), "open": float(row['open']), "high": float(row['high']), "low": float(row['low']), "close": float(row['close']), "volume": float(row['volume'])} for idx, row in df.iterrows()]
        return json.dumps({"success": True, "ticker": ticker, "current_price": current_price, "balance_info": balance_info, "ohlcv_data": ohlcv_data}, ensure_ascii=False)
    except Exception as e:
        log_error(e, "get_coin_price_info 오류")
        return json.dumps({"success": False, "message": str(e), "ticker": ticker}, ensure_ascii=False)

async def buy_coin_func(ctx, args):
    log_info(f"buy_coin 함수 호출", {"args": args})
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except:
            return json.dumps({"success": False, "message": "파싱 오류"}, ensure_ascii=False)
    ticker = args.get("ticker", "").upper()
    price_type = args.get("price_type", "market").lower()
    amount = float(args.get("amount", 0))
    limit_price = float(args.get("limit_price", 0)) if args.get("limit_price") else None
    if not ticker:
        return json.dumps({"success": False, "message": "티커 필요"}, ensure_ascii=False)
    if not ticker.startswith("KRW-"):
        ticker = f"KRW-{ticker}"
    upbit = get_upbit_instance()
    if not upbit:
        return json.dumps({"success": False, "message": "Upbit API 오류"}, ensure_ascii=False)
    if price_type not in ["market", "limit"]:
        return json.dumps({"success": False, "message": f"잘못된 주문 유형: {price_type}"}, ensure_ascii=False)
    if amount <= 0:
        return json.dumps({"success": False, "message": "유효하지 않은 금액"}, ensure_ascii=False)
    try:
        krw_balance = next((float(b['balance']) for b in upbit.get_balances() if b['currency'] == 'KRW'), 0)
        if amount >= krw_balance * 0.99:
            amount = krw_balance * 0.9995
        if price_type == "market":
            order_result = upbit.buy_market_order(ticker, amount)
        else:
            if not limit_price or limit_price <= 0:
                return json.dumps({"success": False, "message": "지정가 필요"}, ensure_ascii=False)
            volume = amount / limit_price
            order_result = upbit.buy_limit_order(ticker, limit_price, volume)
        if order_result and 'uuid' in order_result:
            trade_info = {
                "timestamp": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
                "action": "buy",
                "ticker": ticker,
                "amount": amount,
                "price_type": price_type,
                "limit_price": limit_price,
                "result": order_result
            }
            if 'auto_trader' in st.session_state:
                st.session_state.auto_trader.notify_trade(trade_info)
            return json.dumps({"success": True, "message": f"{ticker} {price_type} 매수 접수", "order_id": order_result['uuid'], "order_info": order_result}, ensure_ascii=False)
        return json.dumps({"success": False, "message": "주문 ID 수신 실패"}, ensure_ascii=False)
    except Exception as e:
        log_error(e, "buy_coin 오류")
        return json.dumps({"success": False, "message": str(e)}, ensure_ascii=False)

async def sell_coin_func(ctx, args):
    log_info(f"sell_coin 함수 호출", {"args": args})
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except:
            return json.dumps({"success": False, "message": "파싱 오류"}, ensure_ascii=False)
    ticker = args.get("ticker", "").upper()
    price_type = args.get("price_type", "market").lower()
    amount = args.get("amount", "")
    limit_price = float(args.get("limit_price", 0)) if args.get("limit_price") else None
    if not ticker:
        return json.dumps({"success": False, "message": "티커 필요"}, ensure_ascii=False)
    if not ticker.startswith("KRW-"):
        ticker = f"KRW-{ticker}"
    upbit = get_upbit_instance()
    if not upbit:
        return json.dumps({"success": False, "message": "Upbit API 오류"}, ensure_ascii=False)
    if price_type not in ["market", "limit"]:
        return json.dumps({"success": False, "message": f"잘못된 주문 유형: {price_type}"}, ensure_ascii=False)
    coin_currency = ticker.replace("KRW-", "")
    coin_balance = next((float(b['balance']) for b in upbit.get_balances() if b['currency'] == coin_currency), 0)
    if coin_balance <= 0:
        return json.dumps({"success": False, "message": f"{coin_currency} 보유 없음"}, ensure_ascii=False)
    if isinstance(amount, str) and amount.lower() in ["all", "전체", "전량"]:
        amount_value = coin_balance
    else:
        try:
            amount_value = float(amount)
            if amount_value > coin_balance:
                return json.dumps({"success": False, "message": f"매도 수량 초과: {amount_value} > {coin_balance}"}, ensure_ascii=False)
        except ValueError:
            return json.dumps({"success": False, "message": "유효하지 않은 수량"}, ensure_ascii=False)
    if amount_value <= 0:
        return json.dumps({"success": False, "message": "양수 필요"}, ensure_ascii=False)
    try:
        if price_type == "market":
            order_result = upbit.sell_market_order(ticker, amount_value)
        else:
            if not limit_price or limit_price <= 0:
                return json.dumps({"success": False, "message": "지정가 필요"}, ensure_ascii=False)
            order_result = upbit.sell_limit_order(ticker, limit_price, amount_value)
        if order_result and 'uuid' in order_result:
            trade_info = {
                "timestamp": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
                "action": "sell",
                "ticker": ticker,
                "amount": amount_value,
                "price_type": price_type,
                "limit_price": limit_price,
                "result": order_result
            }
            if 'auto_trader' in st.session_state:
                st.session_state.auto_trader.notify_trade(trade_info)
            return json.dumps({"success": True, "message": f"{ticker} {price_type} 매도 접수", "order_id": order_result['uuid'], "order_info": order_result}, ensure_ascii=False)
        return json.dumps({"success": False, "message": "주문 ID 수신 실패"}, ensure_ascii=False)
    except Exception as e:
        log_error(e, "sell_coin 오류")
        return json.dumps({"success": False, "message": str(e)}, ensure_ascii=False)

async def check_order_status_func(ctx, args):
    log_info("check_order_status 함수 호출", {"args": args})
    try:
        args_dict = json.loads(args)
        order_id = args_dict.get('order_id', '')
        upbit_trade = get_upbit_trade_instance()
        if upbit_trade and upbit_trade.is_valid:
            order_result = upbit_trade.get_order(order_id)
            if order_result and 'uuid' in order_result:
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
                    'order_type': order_result['ord_type'],
                    'status_korean': {'wait': '대기', 'watch': '예약', 'done': '완료', 'cancel': '취소'}.get(order_result['state'], order_result['state']),
                    'is_executed': order_result['executed_volume'] > 0,
                    'execution_rate': (order_result['executed_volume'] / order_result['volume'] * 100) if order_result['volume'] > 0 else 0
                }
                return json.dumps({"success": True, "message": f"주문 조회: {order_info['status_korean']}", "order_info": order_info}, ensure_ascii=False)
            return json.dumps({"success": False, "message": "주문 조회 실패"}, ensure_ascii=False)
        return json.dumps({"success": False, "message": "API 키 오류", "is_demo": True}, ensure_ascii=False)
    except Exception as e:
        log_error(e, "check_order_status 오류")
        return json.dumps({"success": False, "message": str(e)}, ensure_ascii=False)

# AutoTrader 클래스 정의
class AutoTrader:
    def __init__(self, model_options="gpt-4o-mini", interval_seconds=300, max_investment=100000, max_trading_count=3):
        self.model_options = model_options
        self.interval_seconds = interval_seconds
        self.max_investment = max_investment
        self.max_trading_count = max_trading_count
        self.trading_history = []
        self.daily_trading_count = 0
        self.last_trading_date = None
        self.is_running = False
        self.thread = None
        self.status = "준비됨"
        self.last_check_time = None
        self.next_check_time = None
        self.target_coins = ["BTC", "ETH", "XRP", "SOL", "ADA"]
        self.risk_level = "중립적"
        self.logs = []
        self.trade_callback = None

    def log(self, message, level="INFO"):
        timestamp = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {"timestamp": timestamp, "level": level, "message": message}
        self.logs.append(log_entry)
        logger.info(f"[{level}] {timestamp}: {message}")
        if len(self.logs) > 1000:
            self.logs = self.logs[-1000:]

    def get_portfolio(self):
        try:
            upbit = get_upbit_instance()
            if not upbit:
                return []
            portfolio = []
            krw_balance = next((float(b['balance']) for b in upbit.get_balances() if b['currency'] == 'KRW'), 0)
            if krw_balance:
                portfolio.append({"ticker": "KRW", "amount": krw_balance, "value": krw_balance})
            for coin in self.target_coins:
                ticker = f"KRW-{coin}"
                amount = next((float(b['balance']) for b in upbit.get_balances() if b['currency'] == coin), 0)
                if amount > 0:
                    price = pyupbit.get_current_price(ticker)
                    value = price * amount if price else 0
                    portfolio.append({"ticker": coin, "amount": amount, "value": value})
            return portfolio
        except Exception as e:
            self.log(f"포트폴리오 오류: {str(e)}", "ERROR")
            return []

    def get_market_info(self):
        try:
            import pyupbit
            market_info = {}
            for coin in self.target_coins:
                ticker = f"KRW-{coin}"
                current_price = pyupbit.get_current_price(ticker)
                ohlcv = pyupbit.get_ohlcv(ticker, interval="day", count=2)
                if ohlcv is not None and not ohlcv.empty:
                    prev_close = ohlcv['close'].iloc[-2]
                    change_rate = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0
                    market_info[coin] = {
                        "current_price": current_price,
                        "open_price": ohlcv['open'].iloc[-1],
                        "high_price": ohlcv['high'].iloc[-1],
                        "low_price": ohlcv['low'].iloc[-1],
                        "volume": ohlcv['volume'].iloc[-1],
                        "change_rate": round(change_rate, 2)
                    }
            return market_info
        except Exception as e:
            self.log(f"시장 정보 오류: {str(e)}", "ERROR")
            return {}

    async def check_and_trade(self, agent):
        self.status = "분석 중..."
        self.last_check_time = dt.now()
        self.next_check_time = self.last_check_time + timedelta(seconds=self.interval_seconds)
        self.log("시장 분석 및 거래 결정 시작", "INFO")
        
        current_date = dt.now().date()
        if self.last_trading_date != current_date:
            self.last_trading_date = current_date
            self.daily_trading_count = 0
        
        if self.daily_trading_count >= self.max_trading_count:
            self.log(f"일일 최대 거래 횟수({self.max_trading_count}) 초과", "WARNING")
            self.status = "대기 중"
            return
        
        portfolio = self.get_portfolio()
        market_info = self.get_market_info()
        portfolio_str = "\n".join([f"- {item['ticker']}: {item['amount']} ({item['value']}원)" for item in portfolio])
        market_info_str = "\n".join([f"- {coin}: 현재가 {info['current_price']}원, 변동률 {info['change_rate']}%" for coin, info in market_info.items()])
        
        prompt = f"""
        현재 시장 상황과 포트폴리오를 분석하여 매수/매도 결정을 내리고, 필요하다면 거래를 실행하세요.
        
        # 설정 정보
        - 최대 투자 금액: {self.max_investment}원
        - 일일 최대 거래 횟수: {self.max_trading_count}회 (현재 {self.daily_trading_count}회 사용)
        - 위험 성향: {self.risk_level}
        - 관심 코인: {', '.join(self.target_coins)}
        
        # 현재 포트폴리오
        {portfolio_str}
        
        # 현재 시장 상황
        {market_info_str}
        
        # 거래 지침
        1. 매수/매도 결정을 내리고 이유를 설명하세요.
        2. 매수 시 buy_coin_func, 매도 시 sell_coin_func를 호출하세요.
        3. 일일 거래 횟수 제한을 고려하세요.
        """
        
        try:
            result = await Runner.run(
                agent,
                input=prompt,
                run_config=RunConfig(
                    workflow_name="Auto Trading Decision",
                    group_id=f"auto_trading_{dt.now().strftime('%Y%m%d_%H%M%S')}"
                )
            )
            self.log(f"거래 결정 결과: {str(result)[:100]}...", "INFO")
            self.status = "대기 중"
        except Exception as e:
            self.log(f"거래 결정 실패: {str(e)}", "ERROR")
            self.status = "오류 발생"

    async def run_loop(self, agent):
        self.log("자동 거래 루프 시작", "INFO")
        while self.is_running:
            try:
                await self.check_and_trade(agent)
                wait_seconds = self.interval_seconds
                self.log(f"{wait_seconds}초 후 다음 분석 예정", "INFO")
                # 대기 시간을 한 번에 처리하되, 중간에 루프가 중지될 경우 빠르게 종료할 수 있도록 함
                wait_chunk = min(wait_seconds, 5)  # 최대 5초 단위로 분할
                chunks_count = wait_seconds // wait_chunk
                
                for i in range(chunks_count):
                    if not self.is_running:
                        break
                    await asyncio.sleep(wait_chunk)
                
                # 나머지 시간 처리
                remainder = wait_seconds % wait_chunk
                if self.is_running and remainder > 0:
                    await asyncio.sleep(remainder)
            except Exception as e:
                self.log(f"루프 오류: {str(e)}", "ERROR")
                await asyncio.sleep(60)

    def start(self, agent):
        if self.is_running:
            return False
        if not st.session_state.get('upbit_access_key') or not st.session_state.get('upbit_secret_key'):
            self.log("Upbit API 키 필요", "ERROR")
            return False
        if not st.session_state.get('openai_key'):
            self.log("OpenAI API 키 필요", "ERROR")
            return False
        import pyupbit
        if not pyupbit.get_tickers(fiat="KRW"):
            self.log("시장 정보 오류", "ERROR")
            return False
        
        self.is_running = True
        self.status = "시작됨"
        self.log("자동 거래 시작", "INFO")
        
        async def start_loop():
            await self.run_loop(agent)
        
        def run_async_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(start_loop())
        
        self.thread = threading.Thread(target=run_async_loop)
        self.thread.daemon = True
        self.thread.start()
        return True

    def stop(self):
        if not self.is_running:
            return False
        self.is_running = False
        self.status = "중지됨"
        self.log("자동 거래 중지", "INFO")
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)
        self.thread = None
        return True

    def get_status(self):
        return {
            "is_running": self.is_running,
            "status": self.status,
            "last_check": self.last_check_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_check_time else None,
            "next_check": self.next_check_time.strftime("%Y-%m-%d %H:%M:%S") if self.next_check_time else None,
            "daily_trading_count": self.daily_trading_count,
            "max_trading_count": self.max_trading_count,
            "trading_history_count": len(self.trading_history),
            "model": self.model_options,
            "interval_seconds": self.interval_seconds
        }

    def notify_trade(self, trade_info):
        self.trading_history.append(trade_info)
        self.daily_trading_count += 1
        if self.trade_callback:
            try:
                self.trade_callback(trade_info)
                self.log(f"거래 알림: {trade_info.get('timestamp')} {trade_info.get('action')} {trade_info.get('ticker')}", "INFO")
            except Exception as e:
                self.log(f"알림 오류: {str(e)}", "ERROR")

# Agent 생성 함수
def create_agent(model_options):
    if 'openai_key' not in st.session_state or not st.session_state.openai_key:
        st.error("OpenAI API 키 필요")
        return None
    set_default_openai_key(st.session_state.openai_key)
    
    user_requirement = st.session_state.get('user_requirement', '')
    risk_style = st.session_state.get('risk_style', '중립적')
    trading_period = st.session_state.get('trading_period', '스윙')
    
    # pdf_files 디렉토리가 없을 경우 대비한 예외 처리
    pdf_files_base = []
    try:
        pdf_files = [f for f in os.listdir("tools/web2pdf/always_see_doc_storage") if f.endswith('.pdf')]
        pdf_files_base = [os.path.splitext(f)[0] for f in pdf_files]
    except (FileNotFoundError, OSError) as e:
        log_error(e, "PDF 파일 목록 조회 오류")
    
    previous_messages = st.session_state.get('messages', [])
    context = ""
    if len(previous_messages) > 1:
        context = "이전 대화 내용:\n" + "\n".join(
            f"{'사용자' if msg['role'] == 'user' else 'AI'}: {msg['content']}"
            for msg in previous_messages[-6:-1]
        ) + "\n"
    
    auto_trader = st.session_state.get('auto_trader')
    auto_trader_info = ""
    if auto_trader:
        auto_trader_info += "\n\n# 자동 거래 에이전트 정보\n"
        if auto_trader.is_running:
            status_info = auto_trader.get_status()
            auto_trader_info += f"상태: 실행 중\n설정: 간격 {auto_trader.interval_seconds}초, 최대 투자 {auto_trader.max_investment:,}원, 최대 거래 {auto_trader.max_trading_count}회 (현재 {status_info['daily_trading_count']}회)\n"
            auto_trader_info += f"전략: 위험 {auto_trader.risk_level}, 코인 {', '.join(auto_trader.target_coins)}\n"
            if auto_trader.trading_history:
                auto_trader_info += "\n## 최근 거래\n" + "\n".join(
                    f"- {t['timestamp']}: {t['action']} {t['ticker']} {t['amount']}"
                    for t in auto_trader.trading_history[-3:]
                ) + "\n"
        else:
            auto_trader_info += "상태: 중지됨\n'자동 거래' 탭에서 시작 가능\n"

    # 도구 목록 준비 - FunctionTool로 래핑
    tools = []
    try:
        tools = [
            WebSearchTool(search_context_size="high"),
            FunctionTool.from_defaults(fn=get_available_coins_func),
            FunctionTool.from_defaults(fn=get_coin_price_info_func),
            FunctionTool.from_defaults(fn=buy_coin_func),
            FunctionTool.from_defaults(fn=sell_coin_func),
            FunctionTool.from_defaults(fn=check_order_status_func)
        ]
        
        # 문서 파서 및 정보 추출 도구 추가
        document_parser = DocumentParser()
        if document_parser:
            tools.append(FunctionTool.from_defaults(fn=document_parser, name="document_parser"))
            
        # 정보 추출 도구 추가
        tools.append(FunctionTool.from_defaults(fn=information_extract, name="information_extract"))
    except Exception as e:
        log_error(e, "도구 생성 오류")
        # 최소한의 도구로 시도
        tools = []

    try:
        agent = Agent(
            name="Crypto Trading Assistant",
            instructions=f"""
            암호화폐 거래를 위한 AI 어시스턴트입니다. 사용자의 투자 성향과 요구사항을 고려하며, 자동 거래를 실행할 수 있습니다.
            
            {context}
            
            사용자 지시: {user_requirement}
            위험 성향: {risk_style}
            거래 기간: {trading_period}
            
            {auto_trader_info}

            사용 가능한 문서: {', '.join(pdf_files_base)}
            
            # 자동 거래 지침
            - get_available_coins_func: 거래 가능 코인 조회
            - get_coin_price_info_func: 코인 가격 정보 조회
            - buy_coin_func: 코인 매수
            - sell_coin_func: 코인 매도
            - 최대 투자 금액과 일일 거래 횟수를 준수하며 거래를 실행하세요.
            """,
            model=get_model_name(model_options),
            tools=tools
        )
        return agent
    except Exception as e:
        log_error(e, "에이전트 생성 오류")
        return None

async def stream_openai_response(prompt, model_options, conversation_id=None):
    agent = create_agent(model_options)
    if not agent:
        yield "API 키 설정 필요"
        return
    
    auto_trader = st.session_state.get('auto_trader')
    auto_trader_info = ""
    if auto_trader:
        if auto_trader.is_running:
            status_info = auto_trader.get_status()
            auto_trader_info += f"\n\n## 자동 거래 상태\n- 상태: {status_info['status']}\n- 마지막 분석: {status_info['last_check'] or '없음'}\n- 다음 분석: {status_info['next_check'] or '준비 중'}\n- 거래 횟수: {status_info['daily_trading_count']} / {status_info['max_trading_count']}\n"
            if auto_trader.trading_history:
                auto_trader_info += "\n### 최근 거래\n" + "\n".join(
                    f"- {t['timestamp']}: {t['action']} {t['ticker']} {t['amount']}"
                    for t in auto_trader.trading_history[-3:]
                ) + "\n"
            portfolio = auto_trader.get_portfolio()
            if portfolio:
                auto_trader_info += "\n### 포트폴리오\n" + "\n".join(
                    f"- {item['ticker']}: {item['amount']} (가치: {int(item['value']):,}원)"
                    for item in portfolio
                ) + "\n"
            market_info = auto_trader.get_market_info()
            if market_info:
                auto_trader_info += "\n### 시장 정보\n" + "\n".join(
                    f"- {coin}: 현재가 {int(info['current_price']):,}원, 변동률 {info['change_rate']:.2f}%"
                    for coin, info in market_info.items()
                ) + "\n"
        else:
            auto_trader_info += "\n\n## 자동 거래\n- 상태: 중지됨\n- '자동 거래' 탭에서 시작 가능\n"
    
    run_config = RunConfig(
        workflow_name="Crypto Trading Assistant",
        group_id=conversation_id
    ) if conversation_id else None
    
    full_prompt = f"{prompt}{auto_trader_info}"
    
    result = Runner.run_streamed(
        agent,
        input=full_prompt,
        run_config=run_config
    ) if run_config else Runner.run_streamed(agent, input=full_prompt)
    
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            yield event.data.delta

def stream_response(prompt, model_options):
    async def process_stream():
        async for chunk in stream_openai_response(prompt, model_options):
            yield chunk
    return process_stream()

# 초기화 및 실행
if 'auto_trader' not in st.session_state:
    st.session_state.auto_trader = AutoTrader()

if __name__ == "__main__":
    agent = create_agent("gpt-4o-mini")
    if agent:
        trader = st.session_state.auto_trader
        trader.start(agent)