import json
from typing import Dict, Any, List, Callable, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import BaseTool, StructuredTool, tool
from langchain_core.tools import Tool
from langchain_community.callbacks import get_openai_callback
from model.trading_tools import (
    get_available_coins_func,
    get_coin_price_info_func,
    buy_coin_func,
    sell_coin_func,
    check_order_status_func
)
from model.logging_utils import log_info, log_error

# 도구 스키마 정의
TOOLS_SCHEMA = {
    "get_available_coins": {
        "name": "get_available_coins",
        "description": """
        거래 가능한 코인 목록을 반환합니다.
        매수할 코인을 탐색할 때 사용하세요.
        매도하려는 경우에는 action_type을 'sell'로 지정하여 보유 중인 코인 목록만 볼 수 있습니다.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "enum": ["buy", "sell"],
                    "description": "거래 의도 (buy: 매수용 코인 목록, sell: 매도용 보유 코인 목록)"
                }
            }
        }
    },
    "get_coin_price_info": {
        "name": "get_coin_price_info",
        "description": """
        특정 코인의 가격 정보를 조회합니다.
        코인의 현재 가격, 거래량, 변동성 등의 정보를 얻을 수 있습니다.
        이 정보를 기반으로 사용자에게 코인 구매 또는 판매에 대한 조언을 제공할 수 있습니다.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "코인 티커 (예: 'BTC', 'ETH', 'XRP' 등)"
                }
            },
            "required": ["ticker"]
        }
    },
    "buy_coin": {
        "name": "buy_coin",
        "description": """
        지정된 코인을 매수합니다. 시장가 또는 지정가 주문을 지원합니다.
        매수 주문을 실행하기 전에 사용자에게 확인하세요.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "코인 티커 (예: 'BTC', 'ETH', 'XRP' 등)"
                },
                "price_type": {
                    "type": "string",
                    "enum": ["market", "limit"],
                    "description": "주문 유형 (market: 시장가, limit: 지정가)"
                },
                "amount": {
                    "type": "number",
                    "description": "매수할 금액 (KRW)"
                },
                "limit_price": {
                    "type": "number",
                    "description": "지정가 주문 시 1개당 가격 (KRW)"
                }
            },
            "required": ["ticker", "price_type", "amount"]
        }
    },
    "sell_coin": {
        "name": "sell_coin",
        "description": """
        보유한 코인을 매도합니다. 시장가 또는 지정가 주문을 지원합니다.
        매도 주문을 실행하기 전에 사용자에게 확인하세요.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "코인 티커 (예: 'BTC', 'ETH', 'XRP' 등)"
                },
                "price_type": {
                    "type": "string",
                    "enum": ["market", "limit"],
                    "description": "주문 유형 (market: 시장가, limit: 지정가)"
                },
                "amount": {
                    "type": "string",
                    "description": "매도할 수량 (코인 단위) 또는 'all'(전량 매도)"
                },
                "limit_price": {
                    "type": "number",
                    "description": "지정가 주문 시 1개당 가격 (KRW)"
                }
            },
            "required": ["ticker", "price_type", "amount"]
        }
    },
    "check_order_status": {
        "name": "check_order_status",
        "description": """
        주문 상태를 확인합니다.
        매수 또는 매도 주문 후 주문의 체결 상태를 확인할 때 사용합니다.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "조회할 주문 ID (uuid)"
                }
            },
            "required": ["order_id"]
        }
    }
}

def create_tools() -> List[Tool]:
    """
    에이전트가 사용할 도구(Tool) 목록을 생성합니다.
    """
    try:
        tools = []
        
        # 거래 가능 코인 목록 조회 도구
        get_available_coins_tool = Tool(
            name="get_available_coins",
            func=get_available_coins_func,
            description=TOOLS_SCHEMA["get_available_coins"]["description"],
            args_schema=get_arguments_type("get_available_coins")
        )
        tools.append(get_available_coins_tool)
        
        # 코인 가격 정보 조회 도구
        get_coin_price_info_tool = Tool(
            name="get_coin_price_info",
            func=get_coin_price_info_func,
            description=TOOLS_SCHEMA["get_coin_price_info"]["description"],
            args_schema=get_arguments_type("get_coin_price_info")
        )
        tools.append(get_coin_price_info_tool)
        
        # 코인 매수 도구
        buy_coin_tool = Tool(
            name="buy_coin",
            func=buy_coin_func,
            description=TOOLS_SCHEMA["buy_coin"]["description"],
            args_schema=get_arguments_type("buy_coin")
        )
        tools.append(buy_coin_tool)
        
        # 코인 매도 도구
        sell_coin_tool = Tool(
            name="sell_coin",
            func=sell_coin_func,
            description=TOOLS_SCHEMA["sell_coin"]["description"],
            args_schema=get_arguments_type("sell_coin")
        )
        tools.append(sell_coin_tool)
        
        # 주문 상태 확인 도구
        check_order_status_tool = Tool(
            name="check_order_status",
            func=check_order_status_func,
            description=TOOLS_SCHEMA["check_order_status"]["description"],
            args_schema=get_arguments_type("check_order_status")
        )
        tools.append(check_order_status_tool)
        
        return tools
    except Exception as e:
        log_error(e, "도구 생성 중 오류 발생")
        return []

def get_arguments_type(tool_name: str) -> Optional[Dict[str, Any]]:
    """
    도구 이름에 해당하는 매개변수 스키마를 반환합니다.
    """
    if tool_name in TOOLS_SCHEMA:
        return TOOLS_SCHEMA[tool_name]["parameters"]
    return None

def get_tool_descriptions() -> List[Dict[str, str]]:
    """
    모든 도구의 설명을 반환합니다.
    """
    descriptions = []
    for name, schema in TOOLS_SCHEMA.items():
        descriptions.append({
            "name": name,
            "description": schema["description"].strip()
        })
    return descriptions 