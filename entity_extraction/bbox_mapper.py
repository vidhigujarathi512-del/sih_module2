# bbox_mapper.py
from typing import List, Dict, Any, Optional

def map_field_to_bbox(search_term: str, ocr_pages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Searches page blocks for an extracted term and returns the matching bounding box."""
    if not search_term:
        return None
        
    term_lower = search_term.strip().lower()
    for page in ocr_pages:
        page_num = page.get("page_number", 1)
        for block in page.get("blocks", []):
            block_text = block.get("text", "").lower()
            if term_lower in block_text:
                return {
                    "page": page_num,
                    "bbox": block.get("bbox", [0, 0, 0, 0]),
                    "matched_text": block.get("text")
                }
    return None