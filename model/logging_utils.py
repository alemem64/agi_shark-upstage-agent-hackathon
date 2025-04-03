import logging
import traceback
import json
from typing import Dict, Any, Optional
import streamlit as st

def setup_logging():
    """
    애플리케이션의 로깅을 설정합니다.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def log_info(message: str, data: Optional[Dict[str, Any]] = None) -> None:
    """
    정보 로깅 함수
    """
    logger = logging.getLogger("shark5")
    if data:
        logger.info(f"{message} - {json.dumps(data, ensure_ascii=False)}")
    else:
        logger.info(message)

def log_error(error: Optional[Exception], message: str, show_tb: bool = True) -> None:
    """
    오류 로깅 함수
    """
    logger = logging.getLogger("shark5")
    if error and show_tb:
        logger.error(f"{message}\n{traceback.format_exc()}")
    else:
        logger.error(message)

def log_warning(message: str, data: Optional[Dict[str, Any]] = None) -> None:
    """
    경고 로깅 함수
    """
    logger = logging.getLogger("shark5")
    if data:
        logger.warning(f"{message} - {json.dumps(data, ensure_ascii=False)}")
    else:
        logger.warning(message)

def log_debug(message: str, data: Optional[Dict[str, Any]] = None) -> None:
    """
    디버그 로깅 함수
    """
    logger = logging.getLogger("shark5")
    if data:
        logger.debug(f"{message} - {json.dumps(data, ensure_ascii=False)}")
    else:
        logger.debug(message)

def display_error(message: str, exception: Optional[Exception] = None):
    """
    에러 메시지를 사용자에게 보여주고 로깅합니다.
    """
    st.error(message)
    if exception:
        log_error(exception, message)
    else:
        log_error(None, message, show_tb=False)

def display_warning(message: str):
    """
    경고 메시지를 사용자에게 보여주고 로깅합니다.
    """
    st.warning(message)
    log_warning(message)

def display_success(message: str):
    """
    성공 메시지를 사용자에게 보여주고 로깅합니다.
    """
    st.success(message)
    log_info(message) 