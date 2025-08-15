# app/services/pdf_processor.py
from typing import List, Dict
import io

# Try to import PyMuPDF at module load; raise a clear error if missing
try:
    import fitz  # PyMuPDF
except ImportError as e:
    raise RuntimeError(
        "PyMuPDF is required for process_with_pymupdf(). "
        "Install with: pip install PyMuPDF"
    ) from e


async def process_with_pymupdf(contents: bytes) -> List[Dict]:
    """
    Extract plain text per page using PyMuPDF.
    Returns: [{'page_number': int, 'text': str}, ...]
    """
    pdf_document = fitz.open(stream=contents, filetype="pdf")
    pages_content: List[Dict] = []
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pages_content.append({
            "page_number": page_num + 1,
            "text": page.get_text()
        })
    return pages_content


async def process_with_unstructured(contents: bytes, filename: str) -> List[Dict]:
    """
    Extract structured 'elements' using Unstructured.
    This uses a lazy import so the app can start without unstructured/pdfminer installed.
    Returns: [element_dict, ...]
    """
    try:
        # Lazy import avoids crashing the whole app if extras aren't installed
        from unstructured.partition.pdf import partition_pdf
    except ImportError as e:
        # Give a helpful, actionable message
        raise RuntimeError(
            "Unstructured PDF support not installed. "
            "Install with ONE of the following:\n"
            "  pip install \"unstructured[pdf]\"\n"
            "  (or)\n"
            "  pip install unstructured pdfminer.six pillow"
        ) from e

    # Unstructured inspects the file-like object .name for filetype hints
    pdf_file_like = io.BytesIO(contents)
    setattr(pdf_file_like, "name", filename)

    # On Windows, if you ever hit multiprocessing issues, you can pass:
    # partition_pdf(..., strategy="auto", multiprocessing=False)
    elements = partition_pdf(file=pdf_file_like, strategy="auto")
    return [el.to_dict() for el in elements]
