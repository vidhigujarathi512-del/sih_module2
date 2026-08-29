# tasks.py
from typing import Dict, Any

from schemas.consolidated import ConsolidatedBidderExtraction, DocumentForensics
from schemas.gst import GSTCertExtraction
from schemas.pan import PANITRExtraction
from schemas.udyam import UdyamExtraction
from schemas.balance_sheet import BalanceSheetExtraction
from schemas.ca_udin import CAUDINExtraction
from schemas.mca import MCA21Extraction
from schemas.mii import MakeInIndiaExtraction
from schemas.epfo_esic import EPFOESICExtraction

from regex_patterns import extract_statutory_tokens
from llm_extractor import (
    extract_balance_sheet_structured,
    extract_mii_declaration,
    extract_signatory_name,
)
from bbox_mapper import map_field_to_bbox
from grounding import calculate_grounding_score


def process_entity_extraction_job(ocr_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orchestrates Path A (Deterministic Regex) and Path B (Structured Extraction)
    to assemble a unified, grounded bidder extraction payload.
    """
    submission_id = ocr_payload.get("submission_id", "sub_default")
    pages = ocr_payload.get("pages", [])
    raw_forensics = ocr_payload.get("metadata", {})
    full_text = " \n ".join([p.get("raw_text", "") for p in pages])

    # 1. Path A: Regex Fast-Path (Statutory IDs + Network/Collusion Signals)
    fast_ids = extract_statutory_tokens(full_text)

    # 2. Path B: Structured Variable & Semantic Extraction (with safe defaults)
    bs_data = extract_balance_sheet_structured(full_text) or BalanceSheetExtraction()
    mii_data = extract_mii_declaration(full_text) or MakeInIndiaExtraction()
    signatory = extract_signatory_name(full_text)

    # 3. Assemble Consolidated Model
    consolidated = ConsolidatedBidderExtraction(
        submission_id=submission_id,
        gst=GSTCertExtraction(
            gstin=fast_ids.get("gstin")
        ),
        pan_itr=PANITRExtraction(
            pan_number=fast_ids.get("pan"),
            pan_aadhaar_linked=True if (
                "aadhaar linked" in full_text.lower() or "pan linked" in full_text.lower()
            ) else None
        ),
        udyam=UdyamExtraction(
            udyam_registration_number=fast_ids.get("udyam"),
            enterprise_category="Micro" if "micro" in full_text.lower() else (
                "Small" if "small" in full_text.lower() else "Medium"
            )
        ),
        balance_sheet=bs_data,
        ca_udin=CAUDINExtraction(
            ca_udin=fast_ids.get("udin")
        ),
        mca21=MCA21Extraction(
            cin=fast_ids.get("cin"),
            active_director_dins=fast_ids.get("dins", [])
        ),
        make_in_india=mii_data,
        epfo_esic=EPFOESICExtraction(
            epfo_establishment_code=fast_ids.get("epfo"),
            esic_code=fast_ids.get("esic")
        ),
        # Network & Collusion Signals for Module 4
        registered_pincode=fast_ids.get("registered_pincode"),
        registered_email=fast_ids.get("registered_email"),
        registered_phone=fast_ids.get("registered_phone"),
        signatory_name=signatory,
        # Document Forensics
        document_forensics=DocumentForensics(
            pdf_producer=raw_forensics.get("producer", "Standard PDF Engine"),
            has_digital_signature=bool(
                raw_forensics.get("has_dsc", False) or "digilocker" in full_text.lower()
            ),
            font_anomaly_detected=bool(raw_forensics.get("font_anomaly", False))
        ),
        startup_india_number=fast_ids.get("startup_india_number"),
        digilocker_verified=bool("digilocker" in full_text.lower())
    )

    # 4. Map Coordinates for Highlight Viewer
    bboxes = {
        "pan": map_field_to_bbox(consolidated.pan_itr.pan_number, pages),
        "gstin": map_field_to_bbox(consolidated.gst.gstin, pages),
        "udin": map_field_to_bbox(consolidated.ca_udin.ca_udin, pages),
        "udyam": map_field_to_bbox(consolidated.udyam.udyam_registration_number, pages),
        "cin": map_field_to_bbox(consolidated.mca21.cin, pages)
    }

    # 5. Calculate Hallucination / Grounding Score
    grounding_report = calculate_grounding_score(consolidated.model_dump(), full_text)

    return {
        "status": "SUCCESS",
        "extracted_entities": consolidated.model_dump(),
        "bounding_boxes": bboxes,
        "grounding": grounding_report
    }