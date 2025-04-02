import requests
import streamlit as st

class DocumentParserAgent:
    def __init__(self):
        self.api_key = st.session_state.upstage_api_key
        self.url = "https://api.upstage.ai/v1/document-ai/document-parse"
        
    def parse_document(self, file_content, file_name):
        """문서 파싱을 수행하는 메서드"""
        if not self.api_key:
            return {
                'success': False,
                'error': 'Upstage API 키가 설정되지 않았습니다. API 설정 탭에서 API 키를 입력해주세요.'
            }
            
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        files = {
            "document": (file_name, file_content)
        }
        
        data = {
            "ocr": "force",
            "coordinates": True,
            "chart_recognition": True,
            "output_formats": "['text']",
            "base64_encoding": "['table']",
            "model": "document-parse"
        }
        
        try:
            response = requests.post(self.url, headers=headers, files=files, data=data)
            response.raise_for_status()  # HTTP 에러 체크
            
            result = response.json()
            if 'content' in result and 'text' in result['content']:
                return {
                    'success': True,
                    'text': result['content']['text'],
                    'metadata': {
                        'file_name': file_name,
                        'parse_time': result.get('parse_time', 0)
                    }
                }
            else:
                return {
                    'success': False,
                    'error': '문서 파싱 결과가 예상된 형식이 아닙니다.'
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'API 요청 오류: {str(e)}'
            } 