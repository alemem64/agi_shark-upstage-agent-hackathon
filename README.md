# 🦈 암호화폐 거래 AI Agent

암호화폐 시장 정보를 확인하고, 거래 전략을 분석하며 실제 거래를 실행할 수 있는 AI 기반 트레이딩 봇입니다.

## ✨ 주요 기능

1. **강력한 AI Agent**
   - 웹 검색
   - x(트위터) 검색
   - 스스로 주문 및 목록 조회
   - 문서 데이터베이스 접근
   - 다양한 모델 선택 가능

2. **Upbit API를 활용한 실시간 거래소 정보**
   - 주요 암호화폐의 시세 및 차트 조회
   - 시장 동향 분석 및 시각화
   - 나의 보유 자산 관리
   - 코인 거래 내역 확인

3. **자동화된 투자 전략**
   - AI Agent의 자동 거래 시스템
   - 사용자 맞춤 투자 지시 및 성향 관리
   - PDF와 RAG 문서를 통한 대용량 투자 지침 관리


## 🚀 시작하기

### 권장 환경 (개발 버전)

- Python 3.12.7 (anaconda)

### 필요 API
- upstage API Key (Document Parser, Information Extracter)
- OpenAI API Key (Open AI Agent, Websearch, VectorStore)
- Upbit Access Key
- Upbit Secret Key
- X Bearer Key (검색)

### 설치 방법

1. 저장소 클론하기:
   ```bash
   git clone https://github.com/alemem64/agi_shark-upstage-agent-hackathon.git agi_shark_trading
   cd agi_shark_trading
   ```

2. 필요한 패키지 설치:
   ```bash
   pip install -r requirements.txt
   ```

3. 애플리케이션 실행:
   ```bash
   streamlit run app.py
   ```
