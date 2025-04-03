import requests
import streamlit as st
import os
from typing import List, Dict, Any

class DocumentParser:
    def __init__(self):
        self.name = "document_parser"
        self.description = "Parse and extract text from PDF documents"
        self.api_key = st.session_state.get('upstage_api_key', None)
        self.url = "https://api.upstage.ai/v1/document-ai/document-parse"
        self.base_path = "tools/web2pdf/always_see_doc_storage/"
    
    def __call__(self, file_names: List[str]) -> Dict[str, Any]:
        """Tool interface required for agents library"""
        return self.parse_document(file_names)
        
    def parse_document(self, file_names: List[str]) -> Dict[str, Any]:
        """
        문서 파싱을 수행하는 메서드 - 파일명 리스트를 처리
        
        Args:
            file_names: 파싱할 PDF 파일 이름 목록 (확장자 없이)
            
        Returns:
            Dict: 파싱 결과를 담은 딕셔너리
        """
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

        # 입력이 리스트가 아닌 경우 리스트로 변환
        if not isinstance(file_names, list):
            if isinstance(file_names, str):
                file_names = [file_names]
            else:
                return {
                    'success': False,
                    'error': '파일명 리스트를 제공해주세요.'
                }

        all_results = []
        for file_name in file_names:
            # 리스트에 None이나 빈 문자열이 있는 경우 건너뛰기
            if not file_name:
                continue
                
            # 확장자 처리 (.pdf가 이미 있는지 확인)
            if not file_name.lower().endswith('.pdf'):
                file_path = os.path.join(self.base_path, f"{file_name}.pdf")
            else:
                file_path = os.path.join(self.base_path, file_name)
            
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
                "document": (os.path.basename(file_path), file_content)
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
                            'file_name': os.path.basename(file_path),
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
        
        return {
            'success': True,
            'results': all_results,
            'count': len(all_results),
            'successful_count': sum(1 for r in all_results if r.get('success', False))
        }