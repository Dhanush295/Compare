from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services import pdf_processor

router = APIRouter(
    prefix="/extract",
    tags=["PDF Extraction"],
)

@router.post("/pymupdf", summary="Extract text with PyMuPDF")
async def extract_pymupdf_endpoint(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(400, "File must be a PDF.")
    try:
        contents = await file.read()
        data = await pdf_processor.process_with_pymupdf(contents)
        return {"filename": file.filename, "library": "PyMuPDF", "data": data}
    except Exception as e:
        raise HTTPException(500, f"PyMuPDF processing error: {e}")

@router.post("/unstructured", summary="Extract elements with Unstructured")
async def extract_unstructured_endpoint(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(400, "File must be a PDF.")
    try:
        contents = await file.read()
        data = await pdf_processor.process_with_unstructured(contents, file.filename)
        return {"filename": file.filename, "library": "unstructured", "data": data}
    except Exception as e:
        raise HTTPException(500, f"Unstructured processing error: {e}")
