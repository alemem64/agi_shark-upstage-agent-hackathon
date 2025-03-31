import streamlit as st

def show_portfolio():
    st.title("포트폴리오")
    
    # 포트폴리오 페이지 콘텐츠
    st.write("현재 보유 중인 자산")
    
    # 예시 데이터
    portfolio_data = {
        "BTC": {"amount": 0.5, "value_krw": 35000000},
        "ETH": {"amount": 2.0, "value_krw": 8000000},
        "XRP": {"amount": 1000, "value_krw": 700000},
    }
    
    # 포트폴리오 테이블 표시
    df_data = {
        "코인": list(portfolio_data.keys()),
        "보유량": [data["amount"] for data in portfolio_data.values()],
        "평가금액(KRW)": [data["value_krw"] for data in portfolio_data.values()]
    }
    
    st.dataframe(df_data)
    
    # 총 평가금액 계산
    total_value = sum(data["value_krw"] for data in portfolio_data.values())
    st.metric("총 평가금액", f"{total_value:,} KRW")