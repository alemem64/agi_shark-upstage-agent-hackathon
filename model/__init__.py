"""
암호화폐 트레이딩 AI 모델 패키지
"""

# 기본 로깅 설정 로드
from model.logging_utils import setup_logging

# 주요 클래스와 함수를 패키지 레벨로 노출
from model.agents import (
    RunContextWrapper,
    function_tool,
    create_function_tools,
    create_agent,
    create_openai_client,
    generate_agent_response
)

# 암호화폐 거래 관련 함수
from model.trading_tools import (
    get_available_coins_func,
    get_coin_price_info_func,
    buy_coin_func,
    sell_coin_func,
    check_order_status_func
)

# 업비트 API 관련 유틸리티
from model.upbit_api import (
    get_upbit_instance,
    get_portfolio_coins,
    get_wallet_status,
    get_coin_price
)

# 시작 시 로깅 설정
setup_logging()

# 노출할 함수 및 클래스 목록
__all__ = [
    # agents에서 노출
    'RunContextWrapper',
    'function_tool',
    'create_function_tools',
    'create_agent',
    'create_openai_client',
    'generate_agent_response',
    
    # trading_tools에서 노출
    'get_available_coins_func',
    'get_coin_price_info_func',
    'buy_coin_func',
    'sell_coin_func',
    'check_order_status_func',
    
    # upbit_api에서 노출
    'get_upbit_instance',
    'get_portfolio_coins',
    'get_wallet_status',
    'get_coin_price'
] 