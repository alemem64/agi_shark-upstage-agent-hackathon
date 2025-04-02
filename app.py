import streamlit as st

st.set_page_config(
    page_title="AI 투자 채팅봇",
    page_icon="🦈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# import Sidebar
from page.sidebar import show_sidebar

# import Page
from page.trade_market import show_trade_market
from page.trade_strategy import show_trade_strategy
from page.portfolio import show_portfolio
from page.trade_history import show_trade_history
from page.api_setting import show_api_settings, init_api_session_state

# import Model
from model.api_anthropic import stream_anthropic_response

# 세션 상태 초기화
init_api_session_state()

# 채팅 기록 초기화
if 'messages' not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 투자에 관해 무엇을 도와드릴까요?"}]

# 사이드바 표시
with st.sidebar:
    show_sidebar()

trading_market_tab, trade_strategy_tab, portfolio_tab, trade_history_tab, api_tab = st.tabs(["거래소", "투자 전략", "포트폴리오", "거래 내역", "API 설정"])

with trading_market_tab:
    show_trade_market()

with trade_strategy_tab:
    show_trade_strategy()

with portfolio_tab:
    show_portfolio()

with trade_history_tab:
    show_trade_history()

with api_tab:
    show_api_settings()

    
