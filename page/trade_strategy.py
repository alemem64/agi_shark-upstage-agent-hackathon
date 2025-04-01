import streamlit as st
import os
import fitz  # PyMuPDF
from PIL import Image
import io
import base64
import time

def get_pdf_display(pdf_path):
    """PDF 파일의 첫 페이지를 이미지로 변환"""
    try:
        doc = fitz.open(pdf_path)
        first_page = doc[0]
        # 더 낮은 DPI로 시도
        zoom = 1.0
        mat = fitz.Matrix(zoom, zoom)
        pix = first_page.get_pixmap(matrix=mat, alpha=False)
        
        # RGB 모드로 직접 변환
        img_data = pix.samples
        img = Image.frombytes("RGB", [pix.width, pix.height], img_data)
        
        # 이미지를 바이트로 변환
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        byte_im = buf.getvalue()
        
        doc.close()  # PDF 파일 닫기
        return byte_im
    except Exception as e:
        st.error(f"PDF 미리보기 생성 실패: {str(e)}")
        return None

def get_pdf_url(pdf_path):
    """PDF 파일의 URL 생성"""
    with open(pdf_path, "rb") as file:
        pdf_bytes = file.read()
    b64 = base64.b64encode(pdf_bytes).decode()
    return f"data:application/pdf;base64,{b64}"

def get_pdf_base64(pdf_path):
    """PDF 파일을 base64로 인코딩"""
    with open(pdf_path, "rb") as file:
        pdf_bytes = file.read()
    return base64.b64encode(pdf_bytes).decode()

def show_pdf_content(pdf_path):
    """PDF 전체 내용을 표시"""
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            zoom = 1.0  # 더 낮은 해상도
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_data = pix.samples
            img = Image.frombytes("RGB", [pix.width, pix.height], img_data)
            st.image(img, use_container_width=True)
        doc.close()
        return True
    except Exception as e:
        st.error(f"PDF 표시 중 오류 발생: {str(e)}")
        return False

def show_trade_strategy():
    st.title("투자 전략")
    
    # PDF 저장 디렉토리 설정
    pdf_dir = "webpage_pdfs"
    os.makedirs(pdf_dir, exist_ok=True)
    
    # 파일 업로더 UI 스타일링
    st.markdown("""
        <style>
        /* 파일 업로드 영역 스타일링 */
        .stFileUploader > div:first-child {
            width: 100%;
            height: 100%;
            padding: 1rem;
            border: 2px dashed #4B4B4B;
            border-radius: 0.5rem;
        }
        
        /* "Browse files" 버튼 숨기기 및 한글 텍스트로 대체 */
        .stFileUploader > div:first-child button {
            display: none;
        }
        
        .stFileUploader > div:first-child::after {
            content: "파일 선택하기";
            display: inline-block;
            padding: 0.5rem 1rem;
            background-color: #4B4B4B;
            color: white;
            border-radius: 0.3rem;
            cursor: pointer;
            margin-top: 1rem;
        }
        
        /* 드래그 앤 드롭 텍스트 변경 */
        .stFileUploader > div:first-child::before {
            content: "이곳에 PDF 파일을 끌어다 놓으세요\\A(파일 크기 제한: 200MB)";
            white-space: pre;
            display: block;
            margin-bottom: 0.5rem;
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # 파일 업로더 레이블 숨기기
    uploaded_file = st.file_uploader(
        "PDF 파일 업로드",
        type="pdf",
        label_visibility="collapsed"
    )
    
    if uploaded_file is not None:
        file_path = os.path.join(pdf_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        st.rerun()
    
    # PDF 파일 목록 가져오기
    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
    
    if not pdf_files:
        st.info("저장된 PDF 파일이 없습니다. 파일을 업로드해주세요.")
        return
    
    # 3개의 컬럼으로 PDF 표시
    cols = st.columns(3)
    
    for idx, pdf_file in enumerate(pdf_files):
        pdf_path = os.path.join(pdf_dir, pdf_file)
        col_idx = idx % 3
        
        with cols[col_idx]:
            # PDF 미리보기 이미지 표시
            pdf_image = get_pdf_display(pdf_path)
            if pdf_image:
                st.image(pdf_image, use_container_width=True)
                
                # 파일명을 클릭 가능한 링크로 표시
                safe_filename = pdf_file.replace("http://", "").replace("https://", "")
                b64_pdf = get_pdf_base64(pdf_path)
                
                # PDF 뷰어 링크 생성
                st.markdown(
                    f"""
                    <div style='margin-bottom:10px;'>
                        <a href="data:application/pdf;base64,{b64_pdf}" 
                           target="_blank"
                           rel="noopener noreferrer"
                           style='color: rgba(49, 51, 63, 0.6); text-decoration: none; font-size: 0.8em;'>
                            {safe_filename}
                        </a>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # 다운로드와 삭제 버튼을 가로로 배치
                col1, col2 = st.columns(2)
                with col1:
                    # 다운로드 버튼
                    st.markdown(
                        f"""
                        <a href="data:application/pdf;base64,{b64_pdf}" 
                           download="{safe_filename}"
                           style='text-decoration: none;'>
                            <button style='
                                width: 100%;
                                padding: 0.25rem 0.75rem;
                                border-radius: 0.25rem;
                                border: 1px solid #ccc;
                                background-color: white;
                                color: black;
                                cursor: pointer;
                                font-size: 0.8em;'>
                                다운로드
                            </button>
                        </a>
                        """,
                        unsafe_allow_html=True
                    )
                
                with col2:
                    # 삭제 버튼
                    if st.button("삭제", key=f"delete_{idx}"):
                        try:
                            os.remove(pdf_path)
                            st.success("파일이 삭제되었습니다!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"파일 삭제 중 오류 발생: {str(e)}")