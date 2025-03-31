from anthropic import Anthropic
import streamlit as st

def model_name(model_options):
    if model_options == "claude 3.7 sonnet":
        return "claude-3-7-sonnet-latest"
    elif model_options == "claude 3 haiku":
        return "claude-3-haiku-20240307"

def stream_anthropic_response(prompt, model_options):
    """Anthropic API 스트리밍 응답 생성기"""
    api_key = st.session_state.get('anthropic_key', '')
    
    if not api_key:
        yield "API 키가 설정되지 않았습니다. API 설정 탭에서 API 키를 입력해주세요."
        return
    
    try:
        # 직접 Anthropic 객체 생성
        client = Anthropic(api_key=api_key)
        
        with client.messages.stream(
            model=model_name(model_options),
            max_tokens=1024,
            messages=[
                {
                    "role": "user", 
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
        ) as stream:
            for text in stream.text_stream:
                yield text
                
    except Exception as e:
        yield f"API 요청 오류: {str(e)}"