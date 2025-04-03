import inspect
import asyncio
from typing import TypeVar, Generic, Any, Callable, Dict, List, Optional, Union, Awaitable
from functools import wraps
import json

# 컨텍스트 래퍼 타입 정의
T = TypeVar('T')

class RunContextWrapper(Generic[T]):
    """
    에이전트 함수의 실행 컨텍스트를 래핑하는 클래스
    """
    def __init__(self, context: T):
        self.context = context
        
    def get_context(self) -> T:
        """컨텍스트 객체를 반환합니다."""
        return self.context

# Function 도구 데코레이터
def function_tool(func):
    """
    일반 함수를 에이전트가 사용할 수 있는 Function Tool로 변환하는 데코레이터
    
    이 데코레이터는 다음 기능을 제공합니다:
    1. 함수 시그니처를 기반으로 자동으로 파라미터 스키마 생성
    2. 비동기 및 동기 함수 모두 지원
    3. 다양한 입력 형식 처리 (dict, 문자열 등)
    """
    @wraps(func)
    async def wrapper(ctx, args=None):
        # 함수 시그니처 분석
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        
        # 첫 번째 매개변수가 컨텍스트인지 확인
        has_ctx = len(params) > 0 and params[0].name == 'ctx'
        
        # 파라미터 준비
        kwargs = {}
        if isinstance(args, dict):
            kwargs = args
        elif isinstance(args, str):
            try:
                kwargs = json.loads(args)
            except json.JSONDecodeError:
                # 단일 문자열 파라미터인 경우
                if len(params) == 2 and has_ctx:  # ctx + 1개 파라미터
                    kwargs = {params[1].name: args}
                elif len(params) == 1 and not has_ctx:  # 1개 파라미터만
                    kwargs = {params[0].name: args}
        
        # 함수 호출
        if has_ctx:
            if asyncio.iscoroutinefunction(func):
                return await func(ctx, **kwargs)
            else:
                return func(ctx, **kwargs)
        else:
            if asyncio.iscoroutinefunction(func):
                return await func(**kwargs)
            else:
                return func(**kwargs)
    
    return wrapper

def create_function_tools(functions: List[Callable]) -> List[Dict[str, Any]]:
    """
    함수 목록을 OpenAI Function Calling 형식의 도구 목록으로 변환합니다.
    """
    tools = []
    
    for func in functions:
        # 함수가 데코레이터를 가진 경우 원본 함수 가져오기
        if hasattr(func, '__wrapped__'):
            func_to_inspect = func.__wrapped__
        else:
            func_to_inspect = func
        
        # 함수 메타데이터 추출
        sig = inspect.signature(func_to_inspect)
        params = list(sig.parameters.values())
        doc = inspect.getdoc(func_to_inspect) or ""
        
        # 첫 번째 파라미터가 컨텍스트인 경우 제외
        if params and params[0].name == 'ctx':
            params = params[1:]
        
        # 파라미터 스키마 생성
        properties = {}
        required = []
        
        for param in params:
            param_name = param.name
            param_type = param.annotation
            param_default = param.default
            
            # 필수 파라미터 여부 결정
            if param_default is inspect.Parameter.empty:
                required.append(param_name)
            
            # 파라미터 타입 결정
            properties[param_name] = {
                "type": get_json_type(param_type),
                "description": f"{param_name} 파라미터"
            }
            
            # 기본값 추가
            if param_default is not inspect.Parameter.empty and param_default is not None:
                properties[param_name]["default"] = param_default
        
        # 도구 정의 생성
        tool = {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": doc.split("\n\n")[0] if doc else f"{func.__name__} 함수",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
        
        tools.append(tool)
    
    return tools

def get_json_type(annotation):
    """
    파이썬 타입 어노테이션을 JSON 스키마 타입으로 변환합니다.
    """
    if annotation is inspect.Parameter.empty:
        return "string"
    
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        Any: "string"
    }
    
    # 기본 타입
    for py_type, json_type in type_map.items():
        if annotation is py_type:
            return json_type
    
    # 타입 이름 문자열로 비교
    type_name = str(annotation)
    if "str" in type_name or "string" in type_name.lower():
        return "string"
    elif "int" in type_name or "integer" in type_name.lower():
        return "integer"
    elif "float" in type_name or "number" in type_name.lower() or "double" in type_name.lower():
        return "number"
    elif "bool" in type_name or "boolean" in type_name.lower():
        return "boolean"
    elif "list" in type_name or "array" in type_name.lower():
        return "array"
    elif "dict" in type_name or "object" in type_name.lower():
        return "object"
    
    # 기본값은 문자열
    return "string" 