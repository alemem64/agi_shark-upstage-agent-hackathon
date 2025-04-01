from anthropic import Anthropic
import streamlit as st

def get_model_name(model_options):
    if model_options == "claude 3.7 sonnet":
        return "claude-3-7-sonnet-latest"
    elif model_options == "claude 3 haiku":
        return "claude-3-haiku-20240307"
    elif model_options == "gpt 4o mini":
        return "gpt-4o-mini"

def stream_anthropic_response(prompt, model_options):
    """Anthropic API 스트리밍 응답 생성기"""
    api_key = st.session_state.get('anthropic_key', '')
    
    if not api_key:
        yield "API 키가 설정되지 않았습니다. API 설정 탭에서 API 키를 입력해주세요."
        return
    
    try:
        client = Anthropic(api_key=api_key)
        
        # 시스템 프롬프트에 사용자 맞춤 지시와 투자 성향 포함
        system_prompt = f"""당신은 암호화폐 투자 전문가입니다.

사용자 투자 성향:
- 투자 요구사항: {st.session_state.get('user_requirement', '')}
- 위험 성향: {st.session_state.get('risk_style', '중립적')}
- 거래 기간: {st.session_state.get('trading_period', '스윙')}

다음과 같은 원칙을 따라 조언해주세요:
1. 사용자가 업로드한 문서가 있다면 해당 내용을 분석하여 참고합니다.
2. 문서의 내용과 현재 시장 상황을 연계하여 분석합니다.
3. 위 사용자 성향을 고려하여 맞춤형 조언을 제공합니다.
4. 투기성 조언은 지양하고, 기술적/펀더멘탈 분석에 기반한 조언을 합니다.
5. 투자의 위험성을 항상 고지합니다.
6. 명확한 진입/청산 가격과 손절 기준을 제시합니다.
7. 포트폴리오 분산의 중요성을 강조합니다.

투자 조언시 다음 형식을 따릅니다:
- 문서 분석 (관련 문서가 있는 경우)
- 시장 상황 분석
- 추천 전략
- 위험 관리 방안
- 구체적인 실행 계획"""
        
        with client.messages.stream(
            model=get_model_name(model_options),
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
        ) as stream:
            for text in stream.text_stream:
                yield text
                
    except Exception as e:
        yield f"API 요청 오류: {str(e)}"