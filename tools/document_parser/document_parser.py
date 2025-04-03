import requests
import streamlit as st
import os

class DocumentParser:
    def __init__(self):
        self.name = "document_parser"
        self.description = "Parse and extract text from PDF documents"
        self.api_key = st.session_state.get('upstage_api_key', None)
        self.url = "https://api.upstage.ai/v1/document-ai/document-parse"
        self.base_path = "tools/web2pdf/always_see_doc_storage/"
    
    def __call__(self, input_data=None):
        """Tool interface required for agents library"""
        return self.parse_document(input_data)
        
    def parse_document(self, input_data):
        """문서 파싱을 수행하는 메서드 - 파일 내용 또는 파일명 리스트를 처리"""
        if not self.api_key:
            return {
                'success': False,
                'error': 'Upstage API 키가 설정되지 않았습니다. API 설정 탭에서 API 키를 입력해주세요.'
            }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "ocr": "force",
            "coordinates": True,
            "chart_recognition": True,
            "output_formats": "['text']",
            "base64_encoding": "['table']",
            "model": "document-parse"
        }

        # 입력이 리스트인지 확인
        if isinstance(input_data, list):
            all_results = []
            for file_name in input_data:
                file_path = os.path.join(self.base_path, f"{file_name}.pdf")
                
                # 파일 존재 여부 확인
                if not os.path.exists(file_path):
                    all_results.append({
                        'success': False,
                        'error': f'파일을 찾을 수 없습니다: {file_path}',
                        'file_name': file_name
                    })
                    continue
                
                # 파일 읽기
                try:
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                except Exception as e:
                    all_results.append({
                        'success': False,
                        'error': f'파일 읽기 오류: {str(e)}',
                        'file_name': file_name
                    })
                    continue

                # API 요청
                files = {
                    "document": (file_name + ".pdf", file_content)
                }
                
                try:
                    response = requests.post(self.url, headers=headers, files=files, data=data)
                    response.raise_for_status()
                    
                    result = response.json()
                    if 'content' in result and 'text' in result['content']:
                        all_results.append({
                            'success': True,
                            'text': result['content']['text'],
                            'metadata': {
                                'file_name': file_name + ".pdf",
                                'parse_time': result.get('parse_time', 0)
                            }
                        })
                    else:
                        all_results.append({
                            'success': False,
                            'error': '문서 파싱 결과가 예상된 형식이 아닙니다.',
                            'file_name': file_name
                        })
                        
                except requests.exceptions.RequestException as e:
                    all_results.append({
                        'success': False,
                        'error': f'API 요청 오류: {str(e)}',
                        'file_name': file_name
                    })
            
            return all_results

        # 기존 단일 파일 처리 로직
        else:
            file_content, file_name = input_data
            files = {
                "document": (file_name, file_content)
            }
            
            try:
                response = requests.post(self.url, headers=headers, files=files, data=data)
                response.raise_for_status()
                
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

# 사용 예시:
# parser = DocumentParser()
# file_list = ["bitcoin_report", "bitcoin_report2"]  # .pdf 확장자는 자동으로 추가됨
# results = parser.parse_document(file_list)
# for result in results:
#     if result['success']:
#         print(f"File: {result['metadata']['file_name']}")
#         print(f"Text: {result['text'][:100]}...")  # 첫 100자만 출력
#     else:
#         print(f"Error in {result.get('file_name', 'unknown')}: {result['error']}")