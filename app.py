import streamlit as st
import sys
sys.path.append("tools/upbit")

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
        padding-top: 3rem;
        padding-bottom: 1rem;
    }
    
    /* 상단 탭 버튼 스타일링 - 가시성 향상 */
    .stButton > button[data-testid="baseButton-secondary"] {
        background-color: #f0f2f6;
        margin-top: 10px;
    }
    
    .stButton > button[data-testid="baseButton-primary"] {
        margin-top: 10px;
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

    /* 전체 앱 컨테이너 스타일링 */
    .main .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* 카드 컨테이너 스타일링 */
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 1rem;
    }

    /* 거래내역 카드 컨테이너 */
    .trade-cards-container {
        margin-top: 1rem;
        margin-bottom: 1rem;
        padding: 15px;
        height: auto;
        max-height: 650px;
        overflow-y: auto;
        border-radius: 10px;
        background-color: rgba(255, 255, 255, 0.02);
    }

    /* 페이지네이션 스타일링 */
    .pagination-controls {
        margin-top: 1rem;
        display: flex;
        justify-content: center;
        align-items: center;
    }

    /* 탭 스타일링 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        border-radius: 4px 4px 0 0;
    }

    /* 테이블 헤더 스타일링 */
    .stDataFrame th {
        font-weight: bold !important;
        background-color: #f0f2f6 !important;
    }

    /* 필터 영역 스타일링 */
    .filter-section {
        background-color: #f7f7f7;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }

    /* 상태 배지 스타일링 */
    .status-badge {
        padding: 4px 8px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
    }

    /* 버튼 스타일링 */
    .stButton button {
        border-radius: 20px;
        padding: 4px 15px;
        font-weight: 500;
    }

    /* 채팅 메시지 스타일링 - 긴 텍스트 처리 */
    [data-testid="stChatMessageContent"] {
        overflow-x: auto !important;
        max-width: 100% !important;
        word-wrap: break-word !important;
        white-space: pre-wrap !important;
    }

    /* 채팅 컨테이너 스타일링 */
    [data-testid="stChatMessageContainer"] {
        max-width: 100% !important;
        width: 100% !important;
        padding: 0.5rem !important;
    }

    /* 코드 블록 내부 텍스트 처리 */
    code {
        white-space: pre-wrap !important;
        overflow-x: auto !important;
        max-width: 100% !important;
        display: block !important;
        padding: 0.5rem !important;
    }

    /* 긴 단어 처리 */
    * {
        overflow-wrap: break-word !important;
        word-wrap: break-word !important;
        word-break: break-word !important;
        hyphens: auto !important;
    }

    /* 사이드바 채팅 컨테이너 스타일링 */
    [data-testid="stSidebar"] [data-testid="stChatMessageContainer"],
    [data-testid="stSidebar"] [data-testid="stChatInputContainer"] {
        max-width: 100% !important;
        width: 100% !important;
    }

    /* 모바일 대응 */
    @media (max-width: 768px) {
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 6px 10px;
            font-size: 0.9rem;
        }
        
        .trade-cards-container {
            padding: 10px;
            max-height: 500px;
        }

        /* 모바일에서 채팅 컨테이너 조정 */
        [data-testid="stChatMessageContainer"] {
            padding: 0.3rem !important;
        }
    }

    /* 채팅 UI 개선 */
    [data-testid="stChatContainer"] {
        height: 550px !important;
        overflow-y: auto !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 10px !important;
        background-color: #f9f9f9 !important;
        padding: 15px !important;
        margin-bottom: 15px !important;
    }
    
    [data-testid="stChatMessage"] {
        padding: 8px !important;
        margin-bottom: 10px !important;
    }
    
    [data-testid="stChatMessageContent"] {
        padding: 10px !important;
        border-radius: 15px !important;
        max-width: 85% !important;
        word-wrap: break-word !important;
    }
    
    [data-testid="stChatMessage"][data-testid="user"] [data-testid="stChatMessageContent"] {
        background-color: #e1f5fe !important;
        float: right !important;
        text-align: right !important;
    }
    
    [data-testid="stChatMessage"][data-testid="assistant"] [data-testid="stChatMessageContent"] {
        background-color: #ffffff !important;
        float: left !important;
        border: 1px solid #e0e0e0 !important;
    }
    
    [data-testid="stChatInput"] {
        border-radius: 20px !important;
        padding: 10px 15px !important;
        background-color: white !important;
        border: 1px solid #e0e0e0 !important;
        margin-top: 10px !important;
    }
    
    /* 채팅 스크롤바 스타일 */
    [data-testid="stChatContainer"]::-webkit-scrollbar {
        width: 6px !important;
    }
    
    [data-testid="stChatContainer"]::-webkit-scrollbar-track {
        background: #f1f1f1 !important;
        border-radius: 10px !important;
    }
    
    [data-testid="stChatContainer"]::-webkit-scrollbar-thumb {
        background: #888 !important;
        border-radius: 10px !important;
    }
    
    [data-testid="stChatContainer"]::-webkit-scrollbar-thumb:hover {
        background: #555 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 필요한 모듈 가져오기
from page.sidebar import show_sidebar
from page.trade_market import show_trade_market
from page.portfolio import show_portfolio
from page.trade_history import show_trade_history
from page.api_setting import show_api_settings, init_api_session_state, reset_api_warning, check_api_keys
from model.api_anthropic import stream_anthropic_response

# API 연동 성공 후 모든 캐시 초기화
def refresh_all_data():
    """모든 데이터 캐시를 초기화하고 앱을 재실행합니다."""
    st.cache_data.clear()
    st.rerun()


from init import init_app

init_app()


# 사이드바 표시
with st.sidebar:
    show_sidebar()

# 탭 선택 기능 추가
if 'selected_tab' not in st.session_state:
    st.session_state.selected_tab = "API 설정"  # 기본 탭을 API 설정으로 변경

# API 키 확인
has_api_keys = check_api_keys()

# API 키가 없는 경우 강제로 API 설정 탭 표시
if not has_api_keys and st.session_state.selected_tab != "API 설정":
    st.session_state.selected_tab = "API 설정"
    st.rerun()

# 탭 버튼 생성 - API 키 설정에 따라 동적으로 표시
cols = []

# API 설정 탭은 항상 표시
if has_api_keys:
    # API 키가 있으면 모든 탭 표시
    col1, col2, col3, col4 = st.columns(4)
    cols = [col1, col2, col3, col4]
    
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
else:
    # API 키가 없으면 API 설정 탭만 표시
    col = st.columns(1)[0]
    with col:
        st.button("🔑 API 설정", use_container_width=True, type="primary")
        st.info("API 키를 설정하면 거래소, 포트폴리오, 거래 내역 기능을 사용할 수 있습니다.")

st.markdown("---")

# 탭 내용 표시
# 선택된 탭에 따라 해당 페이지 렌더링
if st.session_state.selected_tab == "거래소":
    show_trade_market()
elif st.session_state.selected_tab == "포트폴리오":
    show_portfolio()
elif st.session_state.selected_tab == "거래 내역":
    show_trade_history()
elif st.session_state.selected_tab == "API 설정":
    show_api_settings()

# API 연동 성공 후 새로고침 수행 
if 'refresh_data' in st.session_state and st.session_state.refresh_data:
    # 새로고침 상태 초기화
    st.session_state.refresh_data = False
    # 캐시 초기화 및 앱 재실행
    refresh_all_data()

    
