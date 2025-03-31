import asyncio
from playwright.async_api import async_playwright
import os
import time
import nest_asyncio

# Jupyter/IPython 환경에서 asyncio 사용 가능하게 설정
nest_asyncio.apply()

class FastWebScraper:
    def __init__(self):
        self.pdf_dir = 'webpage_pdfs'
        if not os.path.exists(self.pdf_dir):
            os.makedirs(self.pdf_dir)

    async def save_as_pdf(self, url):
        """웹페이지를 PDF로 저장"""
        try:
            async with async_playwright() as p:
                # 브라우저 실행
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # 페이지 로드 및 대기
                await page.goto(url, wait_until='networkidle')  # 네트워크 요청이 완료될 때까지 대기
                await page.wait_for_load_state('domcontentloaded')  # DOM이 로드될 때까지 대기
                await page.wait_for_load_state('load')  # 모든 리소스가 로드될 때까지 대기
                
                # 추가 대기 시간 (동적 콘텐츠를 위해)
                await page.wait_for_timeout(3000)  # 3초 추가 대기
                
                # PDF 파일명 생성 (timestamp_domain.pdf)
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                domain = url.split('/')[2] if len(url.split('/')) > 2 else 'webpage'
                pdf_path = os.path.join(self.pdf_dir, f'{timestamp}_{domain}.pdf')
                
                # PDF로 저장
                await page.pdf(path=pdf_path)
                
                await browser.close()
                return pdf_path
                
        except Exception as e:
            print(f"Error saving PDF: {e}")
            return None

def run_scraper():
    scraper = FastWebScraper()
    
    while True:
        print("\n=== 웹페이지 PDF 저장기 ===")
        print("1. URL 입력")
        print("2. 종료")
        
        choice = input("\n선택하세요 (1-2): ")
        
        if choice == '1':
            url = input("\nURL을 입력하세요: ")
            print("\nPDF 저장 중...")
            start_time = time.time()
            
            # 비동기 함수 실행
            pdf_path = asyncio.get_event_loop().run_until_complete(scraper.save_as_pdf(url))
            
            if pdf_path:
                print(f"\n=== 저장 완료 (소요시간: {time.time() - start_time:.2f}초) ===")
                print(f"PDF 위치: {pdf_path}")
            else:
                print("\n저장 실패!")
                
        elif choice == '2':
            print("\n프로그램을 종료합니다.")
            break
        else:
            print("\n잘못된 선택입니다.")

if __name__ == "__main__":
    run_scraper()