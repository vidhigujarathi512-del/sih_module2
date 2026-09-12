import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal, Evaluation, BidderFolder, Document
from tasks import process_entity_extraction_job

app = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. Fetch the latest extracted JSON directly
@app.get("/api/v1/latest-results", summary="Get Latest Extracted Entities JSON")
def get_latest_extracted_json(db: Session = Depends(get_db)):
    record = db.query(Evaluation).order_by(Evaluation.created_at.desc()).first()
    if not record:
        raise HTTPException(status_code=404, detail="No evaluation found. Run ingestion first.")
    
    # If not yet extracted into JSON, run extraction now
    if not record.entities_payload:
        result = process_entity_extraction_job(str(record.id))
        return result
        
    return record.entities_payload

# 2. Trigger Extraction by Evaluation ID
@app.post("/api/v1/extract-entities", summary="Run Entity Extraction on Evaluation ID")
def extract_entities_endpoint(payload: Optional[Dict[str, Any]] = None, db: Session = Depends(get_db)):
    try:
        # If payload is empty or has no ID, pick the latest evaluation record
        target_id = None
        if payload:
            target_id = payload.get("evaluation_id") or payload.get("id")
            
        if not target_id:
            latest_eval = db.query(Evaluation).order_by(Evaluation.created_at.desc()).first()
            if latest_eval:
                target_id = str(latest_eval.id)
            else:
                raise HTTPException(status_code=400, detail="No evaluations exist to process.")

        result = process_entity_extraction_job(target_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction error: {str(e)}")