import requests

api_key = "up_IANAGmcf5Z0MK40wgyiNBYJAlFMTe" # 여러분의 API Key를 입력하세요.
url = "https://api.upstage.ai/v1/document-ai/document-parse"
headers = {
"Authorization": f"Bearer {api_key}"
}

filename = "20250328_company_751823000.pdf" # 분석할 파일명을 입력하세요.
files = {"document": open(filename, "rb")}
data = {
"ocr": "force", # OCR을 강제로 수행하도록 설정 ("auto"로 설정 시 이미지 문서에서만 OCR 수행)
"coordinates": True, # 각 레이아웃 요소의 위치 정보 반환 여부
"chart_recognition": True, # 차트 인식 여부 (bar, line, pie 차트를 표로 변환)
"output_formats": "html", # 결과를 HTML 형식으로 반환 ("text", "markdown"도 가능)
"base64_encoding": "['table']", # 표에 대한 base64 인코딩 요청
"model": "document-parse" # 사용할 모델 지정 (가장 최신 모델 사용)
}
response = requests.post(url, headers=headers, files=files, data=data)
print(response.json())