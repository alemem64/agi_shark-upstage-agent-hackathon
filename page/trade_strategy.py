import streamlit as st
import os
import fitz  # PyMuPDF
from PIL import Image
import io
import base64
from docx import Document  # python-docx 라이브러리 추가 필요
import hashlib
from pathlib import Path

# 파일 캐시 처리를 위한 데코레이터
def cache_file_content(func):
    @st.cache_data
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@cache_file_content
def get_pdf_display(pdf_path):
    """PDF 파일의 첫 페이지를 이미지로 변환 (캐시 적용)"""
    doc = None
    try:
        doc = fitz.open(pdf_path)
        first_page = doc[0]
        pix = first_page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_data = pix.tobytes("png")
        return img_data
    except Exception as e:
        st.error(f"PDF 변환 중 오류 발생: {str(e)}")
        return None
    finally:
        if doc:
            doc.close()

def get_pdf_download_link(pdf_path):
    """PDF 파일의 다운로드 링크 생성"""
    with open(pdf_path, "rb") as file:
        pdf_bytes = file.read()
    b64 = base64.b64encode(pdf_bytes).decode()
    return f'<a href="data:application/pdf;base64,{b64}" download="{os.path.basename(pdf_path)}">다운로드</a>'

def delete_pdf(file_path, storage_dir):
    """PDF 파일 삭제"""
    try:
        # 파일이 존재하는지 확인
        if not os.path.exists(file_path):
            st.error("파일이 존재하지 않습니다.")
            return False
            
        # 파일 삭제 시도
        os.remove(file_path)
        
        # 삭제 상태를 세션 스테이트에 저장
        if 'deleted_files' not in st.session_state:
            st.session_state.deleted_files = set()
        st.session_state.deleted_files.add(f"{storage_dir}_{os.path.basename(file_path)}")
        return True
    except PermissionError:
        st.error("파일이 다른 프로세스에 의해 사용 중입니다. 잠시 후 다시 시도해주세요.")
        return False
    except Exception as e:
        st.error(f"파일 삭제 중 오류 발생: {str(e)}")
        return False

def get_file_preview(file_path):
    """파일 미리보기 생성"""
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.pdf':
        return get_pdf_display(file_path)
    elif file_ext == '.png':
        return Image.open(file_path)
    elif file_ext == '.txt':
        return get_text_content(file_path)
    elif file_ext in ['.doc', '.docx']:
        return get_word_content(file_path)
    return None

@cache_file_content
def get_text_content(file_path):
    """텍스트 파일 내용 읽기 (캐시 적용)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        st.error(f"파일 읽기 오류: {str(e)}")
        return None

@cache_file_content
def get_word_content(file_path):
    """워드 파일 내용 읽기 (캐시 적용)"""
    try:
        doc = Document(file_path)
        return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
    except Exception as e:
        st.error(f"워드 파일 읽기 오류: {str(e)}")
        return None

def get_file_download_link(file_path):
    """파일 다운로드 링크 생성"""
    with open(file_path, "rb") as file:
        file_bytes = file.read()
    b64 = base64.b64encode(file_bytes).decode()
    file_name = os.path.basename(file_path)
    mime_type = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }.get(os.path.splitext(file_path)[1].lower(), 'application/octet-stream')
    
    return f'<a href="data:{mime_type};base64,{b64}" download="{file_name}">다운로드</a>'

@st.cache_data
def get_file_list(storage_dir):
    """저장된 파일 목록 조회 (캐시 적용)"""
    return [f for f in os.listdir(storage_dir) 
            if f.endswith(('.pdf', '.txt', '.doc', '.docx', '.png'))]

def get_file_hash(file_path):
    """파일의 해시값 생성"""
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def display_file_section(title, storage_dir):
    """파일 섹션 표시"""
    st.subheader(title)
    
    # 세션 상태 초기화
    if 'file_states' not in st.session_state:
        st.session_state.file_states = {}
    if storage_dir not in st.session_state.file_states:
        st.session_state.file_states[storage_dir] = {
            'files': get_file_list(storage_dir),
            'deleted': set(),
            'new_files': []
        }
    
    uploaded_file = st.file_uploader(
        f"파일 업로드 ({title})", 
        type=["pdf", "txt", "doc", "docx", "png"], 
        key=f"uploader_{storage_dir}"
    )
    
    # 파일 업로드 처리
    if uploaded_file is not None:
        file_path = os.path.join(storage_dir, uploaded_file.name)
        if uploaded_file.name not in st.session_state.file_states[storage_dir]['files']:
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            # 새 파일을 목록 맨 앞에 추가
            st.session_state.file_states[storage_dir]['files'].insert(0, uploaded_file.name)
            st.session_state.file_states[storage_dir]['new_files'].append(uploaded_file.name)
            st.success(f"파일 '{uploaded_file.name}'이(가) 업로드되었습니다.")
    
    files = st.session_state.file_states[storage_dir]['files']
    if not files:
        st.info("저장된 파일이 없습니다. 파일을 업로드해주세요.")
        return
    
    # 새로 추가된 파일 먼저 표시
    for file in st.session_state.file_states[storage_dir]['new_files']:
        if file in files and file not in st.session_state.file_states[storage_dir]['deleted']:
            display_file(file, storage_dir)
    
    # 기존 파일 표시
    for file in files:
        if (file not in st.session_state.file_states[storage_dir]['new_files'] and 
            file not in st.session_state.file_states[storage_dir]['deleted']):
            display_file(file, storage_dir)

def display_file(file, storage_dir):
    """개별 파일 표시"""
    file_path = os.path.join(storage_dir, file)
    file_key = f"{storage_dir}_{file}"
    
    if not os.path.exists(file_path):
        return
    
    file_ext = os.path.splitext(file)[1].lower()
    
    st.markdown(f"**{file}**")
    
    # 파일 내용 표시
    if file_ext == '.pdf':
        preview = get_pdf_display(file_path)
        if preview:
            st.image(preview, use_container_width=True)
    elif file_ext == '.png':
        st.image(file_path, use_container_width=True)
    elif file_ext == '.txt':
        content = get_text_content(file_path)
        if content is not None:
            st.text_area("파일 내용", value=content, height=200, disabled=True, 
                        key=f"txt_{get_file_hash(file_path)}")
    elif file_ext in ['.doc', '.docx']:
        content = get_word_content(file_path)
        if content is not None:
            st.text_area("파일 내용", value=content, height=200, disabled=True,
                        key=f"docx_{get_file_hash(file_path)}")
    
    # 파일 조작 버튼
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(get_file_download_link(file_path), unsafe_allow_html=True)
    with col2:
        if st.button(f"삭제", key=f"delete_{file_key}"):
            if os.path.exists(file_path):
                os.remove(file_path)
                st.session_state.file_states[storage_dir]['deleted'].add(file)
                st.session_state.file_states[storage_dir]['files'].remove(file)
                if file in st.session_state.file_states[storage_dir]['new_files']:
                    st.session_state.file_states[storage_dir]['new_files'].remove(file)
    
    st.markdown("---")

def show_trade_strategy():
    st.title("투자 전략")
    
    # 저장 디렉토리 설정
    pdf_storage = "tools/web2pdf/always_see_doc_storage"
    rag_storage = "tools/web2pdf/rag_doc_storage"
    os.makedirs(pdf_storage, exist_ok=True)
    os.makedirs(rag_storage, exist_ok=True)
    
    # 2개의 컬럼으로 나누기
    col1, col2 = st.columns(2)
    
    # 왼쪽 컬럼: 항시 참조 문서
    with col1:
        display_file_section("항시 참조 문서", pdf_storage)
    
    # 오른쪽 컬럼: RAG 문서
    with col2:
        display_file_section("RAG 문서", rag_storage)
