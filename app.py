import streamlit as st

# 페이지 설정 최적화
st.set_page_config(
    page_title="AI 투자 채팅봇",
    page_icon="🦈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "AI 기반 암호화폐 트레이딩 봇"
    }
)

# 성능 향상을 위한 CSS 최적화
st.markdown("""
    <style>
    /* 불필요한 마진 줄이기 */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* metrics 스타일 개선 */
    [data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-weight: bold;
        background-color: rgba(0, 0, 0, 0.2);
        padding: 5px;
        border-radius: 5px;
    }
    
    [data-testid="stMetricLabel"] {
        font-weight: bold;
        color: #FFFFFF !important;
    }
    
    [data-testid="stMetricDelta"] {
        font-weight: bold;
        background-color: rgba(0, 0, 0, 0.1);
        padding: 2px 5px;
        border-radius: 3px;
    }
    </style>
""", unsafe_allow_html=True)

# 필요한 모듈 가져오기
from page.sidebar import show_sidebar
from page.trade_market import show_trade_market
from page.portfolio import show_portfolio
from page.trade_history import show_trade_history
from page.api_setting import show_api_settings, init_api_session_state, reset_api_warning
from model.api_anthropic import stream_anthropic_response

# 세션 상태 초기화
init_api_session_state()

# 채팅 기록 초기화
if 'messages' not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 투자에 관해 무엇을 도와드릴까요?"}]

# 사이드바 표시
with st.sidebar:
    show_sidebar()

# 탭 선택 기능 추가
if 'selected_tab' not in st.session_state:
    st.session_state.selected_tab = "거래소"

# 탭 버튼 생성
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("📊 거래소", use_container_width=True, 
                type="primary" if st.session_state.selected_tab == "거래소" else "secondary"):
        st.session_state.selected_tab = "거래소"
        reset_api_warning()
        st.rerun()
with col2:
    if st.button("💼 포트폴리오", use_container_width=True,
                type="primary" if st.session_state.selected_tab == "포트폴리오" else "secondary"):
        st.session_state.selected_tab = "포트폴리오"
        reset_api_warning()
        st.rerun()
with col3:
    if st.button("📝 거래 내역", use_container_width=True,
                type="primary" if st.session_state.selected_tab == "거래 내역" else "secondary"):
        st.session_state.selected_tab = "거래 내역"
        reset_api_warning()
        st.rerun()
with col4:
    if st.button("🔑 API 설정", use_container_width=True,
                type="primary" if st.session_state.selected_tab == "API 설정" else "secondary"):
        st.session_state.selected_tab = "API 설정"
        reset_api_warning()
        st.rerun()

# 선택된 탭에 따라 내용 표시
st.markdown(f"## {st.session_state.selected_tab}")
st.markdown("---")

if st.session_state.selected_tab == "거래소":
    show_trade_market()
elif st.session_state.selected_tab == "포트폴리오":
    show_portfolio()
elif st.session_state.selected_tab == "거래 내역":
    show_trade_history()
elif st.session_state.selected_tab == "API 설정":
    show_api_settings()

    
