import io
import fitz  # PyMuPDF
from unstructured.partition.pdf import partition_pdf
from requests.exceptions import SSLError, ConnectionError, Timeout

async def process_with_pymupdf(contents: bytes) -> list:
    pdf_document = fitz.open(stream=contents, filetype="pdf")
    pages_content = []
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pages_content.append({
            "page_number": page_num + 1,
            "text": page.get_text()
        })
    return pages_content

async def process_with_unstructured(contents: bytes, filename: str) -> list:
    pdf_file_like = io.BytesIO(contents)
    setattr(pdf_file_like, 'name', filename)  # unstructured inspects .name
    elements = partition_pdf(file=pdf_file_like, strategy="auto")
    return [el.to_dict() for el in elements]
