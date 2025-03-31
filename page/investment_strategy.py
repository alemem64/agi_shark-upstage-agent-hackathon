import streamlit as st

def show_investment_strategy():
    st.title("투자 전략")
    
    # 전략 선택
    strategy = st.selectbox(
        "투자 전략 선택",
        ["단기 매매", "중기 투자", "장기 투자", "자동 매매"]
    )
    
    if strategy == "단기 매매":
        st.markdown("""
        ### 단기 매매 전략
        - 변동성이 높은 코인을 대상으로 합니다
        - 1-2일 이내의 짧은 기간 동안 보유합니다
        - 기술적 지표를 활용한 매매 시그널을 제공합니다
        """)
        
        # 매매 설정
        st.subheader("매매 설정")
        col1, col2 = st.columns(2)
        with col1:
            volatility_threshold = st.slider("변동성 임계값 (%)", 1.0, 10.0, 5.0)
            holding_period = st.number_input("보유 기간 (일)", 1, 7, 2)
        with col2:
            stop_loss = st.number_input("손절 비율 (%)", 1.0, 10.0, 3.0)
            take_profit = st.number_input("익절 비율 (%)", 1.0, 20.0, 5.0)
            
    elif strategy == "중기 투자":
        st.markdown("""
        ### 중기 투자 전략
        - 안정적인 코인을 대상으로 합니다
        - 1-3개월 정도의 기간 동안 보유합니다
        - 기본적 분석을 활용한 투자 결정을 제공합니다
        """)
        
        # 투자 설정
        st.subheader("투자 설정")
        col1, col2 = st.columns(2)
        with col1:
            market_cap_min = st.number_input("최소 시가총액 (억원)", 100, 10000, 1000)
            volume_min = st.number_input("최소 거래량 (억원)", 10, 1000, 100)
        with col2:
            holding_period = st.number_input("보유 기간 (일)", 30, 90, 60)
            rebalance_period = st.number_input("리밸런싱 주기 (일)", 7, 30, 15)
            
    elif strategy == "장기 투자":
        st.markdown("""
        ### 장기 투자 전략
        - 블루칩 코인을 대상으로 합니다
        - 6개월 이상의 기간 동안 보유합니다
        - 분할 매수와 분할 매도를 통한 리스크 관리
        """)
        
        # 투자 설정
        st.subheader("투자 설정")
        col1, col2 = st.columns(2)
        with col1:
            market_cap_min = st.number_input("최소 시가총액 (억원)", 1000, 100000, 10000)
            holding_period = st.number_input("보유 기간 (일)", 180, 365, 180)
        with col2:
            buy_interval = st.number_input("매수 간격 (일)", 30, 90, 30)
            sell_interval = st.number_input("매도 간격 (일)", 30, 90, 30)
            
    else:  # 자동 매매
        st.markdown("""
        ### 자동 매매 전략
        - AI 기반의 자동 매매 시스템
        - 24시간 시장 모니터링
        - 실시간 매매 시그널 생성
        """)
        
        # 자동 매매 설정
        st.subheader("자동 매매 설정")
        col1, col2 = st.columns(2)
        with col1:
            max_positions = st.number_input("최대 포지션 수", 1, 10, 3)
            position_size = st.number_input("포지션 크기 (KRW)", 100000, 10000000, 1000000)
        with col2:
            stop_loss = st.number_input("손절 비율 (%)", 1.0, 10.0, 3.0)
            take_profit = st.number_input("익절 비율 (%)", 1.0, 20.0, 5.0)
    
    # 전략 실행 버튼
    if st.button("전략 실행"):
        st.success(f"{strategy} 전략이 실행되었습니다!")
        st.info("실시간으로 전략 실행 상태를 모니터링할 수 있습니다.") 