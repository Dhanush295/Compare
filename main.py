import uvicorn
from fastapi import FastAPI

# import the router objects directly from their modules
from app.routers.extraction import router as extractor_router
from app.routers.kg import router as kg_router

app = FastAPI(
    title="PDF Extraction Comparison API",
    description="data extraction libraries.",
    version="2.0.0",
)

# use the variables you imported above
app.include_router(extractor_router)
app.include_router(kg_router)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the PDF Extraction API. Go to /docs to see the endpoints."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
