from anthropic import Anthropic
import streamlit as st

def model_name(model_options):
    if model_options == "claude 3.7 sonnet":
        return "claude-3-7-sonnet-latest"
    elif model_options == "claude 3 haiku":
        return "claude-3-haiku-20240307"

def get_anthropic_response(prompt, system_prompt="You are a helpful assistant."):
    """일반적인 Anthropic API 호출"""
    
    api_key = st.session_state.get('anthropic_key', '')
    
    if not api_key:
        return "API 키가 설정되지 않았습니다. API 설정 탭에서 API 키를 입력해주세요."
    
    try:
        # 직접 Anthropic 객체 생성
        client = Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-3-haiku-20240307", 
            max_tokens=1000,
            temperature=0.7,
            system=system_prompt,
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
            ]
        )
        
        # 응답 추출 - API 문서에 따라 처리
        if hasattr(message, 'content') and len(message.content) > 0:
            content_item = message.content[0]
            # content_item이 딕셔너리인 경우
            if isinstance(content_item, dict) and 'text' in content_item:
                return content_item['text']
            # content_item이 객체인 경우
            elif hasattr(content_item, 'type') and content_item.type == 'text':
                if hasattr(content_item, 'text'):
                    return content_item.text
        
        # 직렬화 가능한 형태로 변환
        if hasattr(message, 'model_dump'):
            # Pydantic v2
            return str(message.model_dump())
        elif hasattr(message, 'dict'):
            # Pydantic v1
            return str(message.dict())
        else:
            # 기타 경우
            return "응답을 처리할 수 없습니다."
    except Exception as e:
        return f"API 요청 오류: {str(e)}"

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