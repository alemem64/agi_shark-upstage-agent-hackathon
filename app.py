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
        color: #333333 !important;
        font-weight: bold;
        background-color: rgba(255, 255, 255, 0.9);
        padding: 5px;
        border-radius: 5px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    [data-testid="stMetricLabel"] {
        font-weight: bold;
        color: #333333 !important;
    }
    
    [data-testid="stMetricDelta"] {
        font-weight: bold;
        background-color: rgba(255, 255, 255, 0.8);
        padding: 2px 5px;
        border-radius: 3px;
    }
    
    /* HTML 렌더링 개선 핵심 설정 */
    .element-container div.markdown-text-container p {
        margin-bottom: 0px;
    }
    
    /* HTML 태그 직접 렌더링 처리 */
    .stMarkdown {
        display: block !important;
    }
    
    .stMarkdown p, .stMarkdown div, .stMarkdown span, 
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, 
    .stMarkdown h4, .stMarkdown h5, .stMarkdown h6,
    .stMarkdown ul, .stMarkdown ol, .stMarkdown li,
    .stMarkdown table, .stMarkdown tr, .stMarkdown td, .stMarkdown th {
        display: block !important;
        white-space: normal !important;
        overflow: visible !important;
    }
    
    /* Markdown 내부 태그 특수 처리 */
    .stMarkdown div p {
        white-space: normal !important;
        display: block !important;
    }
    
    /* stMarkdown에서 HTML이 텍스트로 표시되는 문제 해결 */
    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] div,
    div[data-testid="stMarkdownContainer"] span {
        display: block !important;
        white-space: normal !important;
    }
    
    /* HTML 요소가 태그로 표시되지 않고 정상 렌더링되도록 함 */
    div[data-testid="stMarkdownContainer"] > div > p {
        overflow: visible !important;
        white-space: normal !important;
        display: block !important;
    }
    
    /* 버튼 스타일 개선 - 텍스트 잘림 방지 */
    .stButton > button {
        min-height: 2.5rem;
        overflow: visible !important;
        white-space: normal !important;
        height: auto !important;
        padding: 0.75rem 1rem;
        font-size: 1rem;
        width: 100%;
    }
    
    /* HTML 테이블 스타일 */
    table {
        width: 100%;
        border-collapse: collapse;
        display: table !important;
    }
    
    th, td {
        padding: 8px;
        text-align: left;
        display: table-cell !important;
    }
    
    tr {
        display: table-row !important;
    }
    
    thead {
        display: table-header-group !important;
    }
    
    tbody {
        display: table-row-group !important;
    }
    
    thead tr {
        border-bottom: 1px solid #ddd;
    }
    
    /* 격자 스타일 컨테이너 */
    .grid-container {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
    
    /* 데이터 컨테이너 스타일 - 가독성 향상 */
    .data-container {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        border: 1px solid #e6e6e6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* 가격 정보 카드 스타일 - 가독성 향상 */
    .price-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #e6e6e6;
    }
    
    /* 차트 및 데이터 설명 레이블 */
    .data-label {
        font-weight: bold;
        margin-bottom: 0.25rem;
        color: #444;
    }
    
    .data-value {
        font-size: 1.2rem;
        margin-bottom: 0.5rem;
    }
    
    /* 프로그레스 바 스타일 */
    .progress-container {
        height: 8px;
        background-color: #f0f2f6;
        border-radius: 4px;
        overflow: hidden;
        margin-top: 10px;
    }
    
    .progress-bar {
        height: 100%;
        border-radius: 4px;
    }
    
    /* HTML 이스케이프 특수 처리 - 모든 곳에 적용 */
    div[data-testid="stMarkdownContainer"] > div.markdown-text-container > p {
        display: block !important;
    }
    
    /* 모든 HTML 요소 표시 강제 처리 */
    div, span, p, h1, h2, h3, h4, h5, h6, ul, li, table, tr, td, th {
        white-space: normal !important;
        overflow: visible !important;
    }
    
    /* 추가 렌더링 문제 해결을 위한 스타일 */
    .stMarkdownContainer, .element-container {
        overflow: visible !important;
    }
    
    /* Streamlit HTML 특수 처리 */
    span[data-testid="stMarkdownContainer"] div {
        display: block !important;
        white-space: normal !important;
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

# 탭 버튼 생성 - 너비 조정으로 텍스트 잘림 방지
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

    
