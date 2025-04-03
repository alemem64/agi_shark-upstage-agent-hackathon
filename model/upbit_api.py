import streamlit as st
import logging
import traceback
import json
from typing import List, Dict, Union, Optional, Tuple, Any
import time

# 로깅 함수
def log_info(message: str, data: Optional[Dict[str, Any]] = None) -> None:
    """
    정보 로깅 함수
    """
    logger = logging.getLogger("upbit_api")
    if data:
        logger.info(f"{message} - {json.dumps(data, ensure_ascii=False)}")
    else:
        logger.info(message)

def log_error(error: Optional[Exception], message: str, show_tb: bool = True) -> None:
    """
    오류 로깅 함수
    """
    logger = logging.getLogger("upbit_api")
    if error and show_tb:
        logger.error(f"{message}\n{traceback.format_exc()}")
    else:
        logger.error(message)

def import_pyupbit():
    """
    pyupbit 라이브러리를 임포트하는 도우미 함수
    """
    try:
        import pyupbit
        return pyupbit
    except ImportError:
        log_error(None, "pyupbit 라이브러리가 설치되어 있지 않습니다. 'pip install pyupbit' 명령어로 설치하세요.", show_tb=False)
        st.error("pyupbit 라이브러리가 설치되어 있지 않습니다. 'pip install pyupbit' 명령어로 설치하세요.")
        return None

class UpbitTrader:
    """
    업비트 트레이딩 관련 유틸리티 클래스
    """
    @staticmethod
    def get_balances():
        """
        보유 자산 정보를 조회합니다.
        """
        try:
            pyupbit = import_pyupbit()
            if not pyupbit:
                return []
            
            upbit = get_upbit_instance()
            if not upbit:
                return []
            
            balances = upbit.get_balances()
            return balances
        except Exception as e:
            log_error(e, "보유 자산 정보 조회 중 오류 발생")
            return []

# 업비트 API 인스턴스 관련 함수
def get_upbit_instance():
    """
    Upbit API 인스턴스를 반환합니다.
    """
    try:
        pyupbit = import_pyupbit()
        if not pyupbit:
            return None
            
        # 세션 상태에서 API 키 정보 가져오기
        api_key = st.session_state.get('upbit_api_key', '')
        api_secret = st.session_state.get('upbit_api_secret', '')
        
        # API 키가 없으면 None 반환
        if not api_key or not api_secret:
            log_error(None, "Upbit API 키가 설정되지 않았습니다.", show_tb=False)
            return None
            
        # Upbit 인스턴스 생성
        upbit = pyupbit.Upbit(api_key, api_secret)
        return upbit
    except Exception as e:
        log_error(e, "Upbit API 인스턴스 생성 중 오류 발생")
        return None

def get_upbit_trade_instance():
    """
    거래용 Upbit API 인스턴스를 반환합니다.
    """
    return get_upbit_instance()

# 시장 정보 조회 함수
def get_market_info(limit: int = 100) -> List[Dict[str, str]]:
    """
    KRW 마켓의 코인 정보를 조회합니다.
    """
    try:
        pyupbit = import_pyupbit()
        if not pyupbit:
            return []
            
        # 마켓 정보 조회
        markets = pyupbit.get_tickers(fiat="KRW")
        
        # 마켓 이름 조회
        market_info_all = pyupbit.get_market_all()
        
        # KRW 마켓 정보만 필터링
        market_info = []
        for info in market_info_all:
            if info['market'].startswith('KRW-'):
                market_info.append(info)
                
        # 결과 제한
        if limit > 0 and len(market_info) > limit:
            market_info = market_info[:limit]
            
        return market_info
    except Exception as e:
        log_error(e, "마켓 정보 조회 중 오류 발생")
        return []

# 포트폴리오 조회 함수
def get_portfolio_coins() -> List[Dict[str, Union[str, float]]]:
    """
    사용자의 보유 코인 목록을 조회합니다.
    """
    try:
        upbit = get_upbit_instance()
        if not upbit:
            return []
            
        balances = upbit.get_balances()
        
        # KRW를 제외한 코인만 추출
        coins = []
        for balance in balances:
            if balance['currency'] != 'KRW' and float(balance['balance']) > 0:
                coins.append({
                    'ticker': f"KRW-{balance['currency']}",
                    'korean_name': balance['currency'],  # 한글 이름은 나중에 필요하면 추가
                    'balance': float(balance['balance']),
                    'avg_buy_price': float(balance['avg_buy_price']) if 'avg_buy_price' in balance else 0
                })
        
        return coins
    except Exception as e:
        log_error(e, "포트폴리오 조회 중 오류 발생")
        return []

# 지갑 정보 조회 함수
def get_wallet_status() -> Dict[str, Any]:
    """
    업비트 지갑 상태를 조회합니다.
    """
    try:
        upbit = get_upbit_instance()
        if not upbit:
            return {
                "success": False,
                "message": "Upbit API 인스턴스를 생성할 수 없습니다. API 키 설정을 확인하세요.",
                "wallet_state": "UNAVAILABLE"
            }
            
        # 잔고 조회를 통해 API 키 유효성 확인
        try:
            balances = upbit.get_balances()
            total_krw = 0
            total_asset_value = 0
            
            # KRW 잔고 추출
            for balance in balances:
                if balance['currency'] == 'KRW':
                    total_krw = float(balance['balance'])
                    break
                    
            # 보유 자산의 원화 가치 계산
            pyupbit = import_pyupbit()
            if pyupbit:
                for balance in balances:
                    if balance['currency'] != 'KRW' and float(balance['balance']) > 0:
                        ticker = f"KRW-{balance['currency']}"
                        price = pyupbit.get_current_price(ticker)
                        if price:
                            value = float(balance['balance']) * price
                            total_asset_value += value
            
            # 전체 자산 가치 계산
            total_value = total_krw + total_asset_value
            
            return {
                "success": True,
                "wallet_state": "ACTIVE",
                "krw_balance": total_krw,
                "asset_value": total_asset_value,
                "total_value": total_value
            }
        except Exception as e:
            log_error(e, "지갑 상태 조회 중 오류 발생")
            return {
                "success": False,
                "message": f"지갑 상태 조회 중 오류 발생: {str(e)}",
                "wallet_state": "ERROR"
            }
            
    except Exception as e:
        log_error(e, "지갑 상태 조회 중 예상치 못한 오류 발생")
        return {
            "success": False,
            "message": f"지갑 상태 조회 중 예상치 못한 오류 발생: {str(e)}",
            "wallet_state": "ERROR"
        }

# 코인 가격 정보 조회 함수
def get_coin_price(ticker: str) -> Dict[str, Any]:
    """
    특정 코인의 현재가를 조회합니다.
    """
    try:
        pyupbit = import_pyupbit()
        if not pyupbit:
            return {
                "success": False,
                "message": "pyupbit 라이브러리가 설치되어 있지 않습니다."
            }
            
        # KRW 프리픽스 추가
        if not ticker.startswith("KRW-"):
            ticker = f"KRW-{ticker}"
            
        # 현재가 조회
        current_price = pyupbit.get_current_price(ticker)
        
        if current_price:
            return {
                "success": True,
                "ticker": ticker,
                "price": current_price
            }
        else:
            return {
                "success": False,
                "message": f"{ticker} 코인의 가격 정보를 찾을 수 없습니다.",
                "ticker": ticker
            }
            
    except Exception as e:
        log_error(e, f"{ticker} 코인 가격 조회 중 오류 발생")
        return {
            "success": False,
            "message": f"코인 가격 조회 중 오류 발생: {str(e)}",
            "ticker": ticker
        }

# 오더북 조회 함수
def get_orderbook(ticker: str) -> Dict[str, Any]:
    """
    특정 코인의 호가창 정보를 조회합니다.
    """
    try:
        pyupbit = import_pyupbit()
        if not pyupbit:
            return {
                "success": False,
                "message": "pyupbit 라이브러리가 설치되어 있지 않습니다."
            }
            
        # KRW 프리픽스 추가
        if not ticker.startswith("KRW-"):
            ticker = f"KRW-{ticker}"
            
        # 호가 정보 조회
        orderbook = pyupbit.get_orderbook(ticker)
        
        if orderbook:
            return {
                "success": True,
                "ticker": ticker,
                "orderbook": orderbook
            }
        else:
            return {
                "success": False,
                "message": f"{ticker} 코인의 호가 정보를 찾을 수 없습니다.",
                "ticker": ticker
            }
            
    except Exception as e:
        log_error(e, f"{ticker} 코인 호가 정보 조회 중 오류 발생")
        return {
            "success": False,
            "message": f"호가 정보 조회 중 오류 발생: {str(e)}",
            "ticker": ticker
        }

# 주문 취소 함수
def cancel_order(order_id: str) -> Dict[str, Any]:
    """
    주문을 취소합니다.
    """
    try:
        upbit = get_upbit_instance()
        if not upbit:
            return {
                "success": False,
                "message": "Upbit API 인스턴스를 생성할 수 없습니다. API 키 설정을 확인하세요."
            }
            
        # 주문 취소
        result = upbit.cancel_order(order_id)
        
        if result and 'uuid' in result:
            return {
                "success": True,
                "message": f"주문이 성공적으로 취소되었습니다. 주문 ID: {result['uuid']}",
                "order_id": result['uuid']
            }
        else:
            return {
                "success": False,
                "message": f"주문 취소 결과가 유효하지 않습니다: {result}",
                "order_id": order_id
            }
            
    except Exception as e:
        log_error(e, f"주문 취소 중 오류 발생 (ID: {order_id})")
        return {
            "success": False,
            "message": f"주문 취소 중 오류 발생: {str(e)}",
            "order_id": order_id
        } 