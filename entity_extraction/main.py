# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
from tasks import process_entity_extraction_job

app = FastAPI(
    title="GeM Bid AI Entity Extraction Engine",
    version="1.0.0",
    description="Extracts statutory IDs and financial metrics from raw OCR payloads."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/v1/extract-entities")
async def extract_entities_endpoint(payload: Dict[str, Any]):
    try:
        extraction_result = process_entity_extraction_job(payload)
        return {
            "status": "SUCCESS",
            "data": extraction_result["extracted_entities"],
            "bounding_boxes": extraction_result["bounding_boxes"],
            "grounding": extraction_result.get("grounding", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

@app.get("/health")
def health_check():
    return {"status": "HEALTHY", "module": "AI Entity Extraction"}