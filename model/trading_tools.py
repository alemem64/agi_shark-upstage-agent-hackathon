import json
import logging
import traceback
import streamlit as st
from model.upbit_api import get_upbit_instance, log_info, log_error

# 코인 목록 조회 함수
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
        from model.upbit_api import get_portfolio_coins, get_market_info
        
        # 사용자의 보유 코인 목록 조회
        portfolio_coins = get_portfolio_coins()
        
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
        market_info = get_market_info(limit=20)
        log_info(f"get_available_coins: {len(market_info)}개의 KRW 마켓 코인 조회됨")
        
        # 위험 성향에 기반해 추천 코인 필터링 (예시)
        risk_style = st.session_state.get('risk_style', '중립적')
        risk_filters = {
            '보수적': lambda m: m['market'] in ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-ADA', 'KRW-DOGE'],
            '중립적': lambda m: True,  # 모든 코인 허용
            '공격적': lambda m: True   # 모든 코인 허용
        }
        
        filtered_markets = [m for m in market_info if risk_filters.get(risk_style, lambda x: True)(m)]
        
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
           
    except Exception as e:
        error_msg = f"코인 목록 조회 중 오류 발생: {str(e)}"
        log_error(e, error_msg)
        return json.dumps({
            "success": False,
            "message": error_msg,
            "coins": []
        }, ensure_ascii=False)

# 코인 가격 정보 조회 함수
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

# 코인 매수 함수
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

# 코인 매도 함수
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

# 주문 상태 확인 함수
async def check_order_status_func(ctx, args):
    """
    주문 상태를 확인합니다.
    order_id: 조회할 주문 ID (uuid)
    """
    try:
        # 로깅 시작
        log_info(f"check_order_status 함수 호출", {"args": args})
        
        # args가 문자열인 경우 JSON으로 파싱
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError as e:
                error_msg = f"매개변수 파싱 오류: {str(e)}"
                log_error(e, error_msg)
                return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
        
        # 주문 ID 추출
        order_id = args.get("order_id", "")
        
        if not order_id:
            error_msg = "주문 ID(order_id)가 필요합니다."
            log_error(None, error_msg, show_tb=False)
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
        
        # upbit 인스턴스 가져오기
        upbit = get_upbit_instance()
        if not upbit:
            error_msg = "Upbit API 인스턴스를 생성할 수 없습니다. API 키 설정을 확인하세요."
            log_error(None, error_msg, show_tb=False)
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
        
        # 주문 상태 조회
        try:
            order_info = upbit.get_order(order_id)
            log_info(f"check_order_status: 주문 상태 조회 결과", {"order_info": order_info})
            
            # 상태 정보 가공
            if order_info:
                state = order_info.get('state', '')
                market = order_info.get('market', '')
                side = order_info.get('side', '')
                price = order_info.get('price', '0')
                volume = order_info.get('volume', '0')
                executed_volume = order_info.get('executed_volume', '0')
                created_at = order_info.get('created_at', '')
                
                # 주문 상태 한글화
                state_korean = {
                    'wait': '대기',
                    'watch': '예약',
                    'done': '완료',
                    'cancel': '취소'
                }.get(state, state)
                
                # 거래 유형 한글화
                side_korean = {
                    'bid': '매수',
                    'ask': '매도'
                }.get(side, side)
                
                # 인간 친화적 메시지 생성
                friendly_message = f"{market} {side_korean} 주문의 현재 상태는 '{state_korean}'입니다."
                if state == 'done':
                    friendly_message += f" 모든 주문량({volume})이 체결되었습니다."
                elif state == 'wait' or state == 'watch':
                    if float(executed_volume) > 0:
                        exec_rate = (float(executed_volume) / float(volume)) * 100
                        friendly_message += f" 주문량의 {exec_rate:.2f}%가 체결되었습니다."
                    else:
                        friendly_message += " 아직 체결된 수량이 없습니다."
                elif state == 'cancel':
                    if float(executed_volume) > 0:
                        exec_rate = (float(executed_volume) / float(volume)) * 100
                        friendly_message += f" 취소 전 주문량의 {exec_rate:.2f}%가 체결되었습니다."
                    else:
                        friendly_message += " 체결 전에 주문이 취소되었습니다."
                
                result = {
                    'success': True,
                    'message': friendly_message,
                    'order_id': order_id,
                    'state': state,
                    'state_korean': state_korean,
                    'market': market,
                    'side': side,
                    'side_korean': side_korean,
                    'price': price,
                    'volume': volume,
                    'executed_volume': executed_volume,
                    'created_at': created_at,
                    'raw_data': order_info
                }
                
                return json.dumps(result, ensure_ascii=False)
            else:
                error_msg = f"주문 정보를 찾을 수 없습니다. 주문 ID: {order_id}"
                log_error(None, error_msg, show_tb=False)
                return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
                
        except Exception as e:
            error_msg = f"주문 상태 조회 중 오류 발생: {str(e)}"
            log_error(e, error_msg)
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
            
    except Exception as e:
        error_msg = f"주문 상태 확인 중 예상치 못한 오류 발생: {str(e)}"
        log_error(e, error_msg)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False) 