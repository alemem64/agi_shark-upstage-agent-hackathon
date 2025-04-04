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



## 권장 환경 (개발 버전)

- Python 3.11.11

## 필요 API
1. upstage API Key (Document Parser, Information Extracter)
2. OpenAI API Key (Open AI Agent, Websearch, VectorStore)
   - 아레 링크에서 발급
   - https://platform.openai.com/api-keys
3. Upbit Access Key, Secret Key
   - K뱅크 계좌 개설
   - 아래 링크에서 발급 (한 Key는 동시에 한 IP주소에서 사용 가능)
   - https://upbit.com/mypage/open_api_management
4. X Bearer Token (검색)
   - 아래 링크 접속 후 로그인    
   - https://developer.x.com/en/portal/dashboard
   - Project App 내의 열쇠 클릭
   - Authentication Tokens의 Bearer Token 토큰 발급

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

### 문제 해결

1. numpy/pandas 설치 오류 시:
   ```bash
   pip uninstall numpy pandas
   pip install numpy>=1.26.0 pandas>=2.1.0
   ```

2. M1/M2 Mac 사용자:
   ```bash
   pip install --upgrade pip wheel setuptools
   ```
   를 먼저 실행 후 설치를 진행해주세요.
