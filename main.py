import uvicorn
from fastapi import FastAPI
from app.routers import extraction

app = FastAPI(
    title="PDF Extraction Comparison API",
    description="data extraction libraries.",
    version="2.0.0",
)

app.include_router(extraction.router)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/", tags=["Root"])
async def read_root():
    """A welcome message to confirm the server is running."""
    return {"message": "Welcome to the PDF Extraction API. Go to /docs to see the endpoints."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)