"""
OCR Service — extracts number plate text from uploaded images.

Uses EasyOCR which works well on Indian number plates.
Model is downloaded on first use (~100MB) and cached in
/home/appuser/.EasyOCR inside the container.

Design decisions:
- OCR runs synchronously (not async) — EasyOCR is CPU-bound
- If OCR fails for any reason, complaint is still accepted
  (user description is still valid evidence)
- Plate text is normalised: spaces removed, uppercase
- Confidence threshold of 0.4 — below this we return None
  rather than a confidently-wrong plate number

Edge case from blueprint 4.2:
  "Image with no readable plate → store complaint with plate_number=null"
  This is handled here by returning None when confidence is low.
"""
import io
import logging
import re
from typing import Optional

logger = logging.getLogger("complaint-service.ocr")

# Indian number plate pattern: 2 letters + 2 digits + 1-2 letters + 4 digits
# e.g. UK07BC1234, DL01AB9999, MH12CD5678
PLATE_PATTERN = re.compile(r"[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}")


def _normalise_plate(text: str) -> str:
    """Remove spaces, uppercase, strip non-alphanumeric."""
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def extract_plate(image_bytes: bytes, use_ocr: bool = True) -> tuple[Optional[str], Optional[float]]:
    """
    Returns (plate_number, confidence) or (None, None) if extraction fails.

    use_ocr=False skips model loading for unit tests.
    """
    if not use_ocr:
        return None, None

    try:
        import easyocr
        import numpy as np
        from PIL import Image

        # Load image from bytes
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(image)

        # Initialise reader — cached after first call
        reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        results = reader.readtext(img_array)

        # Find the result that best matches an Indian plate pattern
        best_plate = None
        best_confidence = 0.0

        for (bbox, text, confidence) in results:
            normalised = _normalise_plate(text)
            if PLATE_PATTERN.match(normalised) and confidence > best_confidence:
                best_plate = normalised
                best_confidence = confidence

        # If no pattern match, try the highest-confidence result anyway
        if not best_plate and results:
            results_sorted = sorted(results, key=lambda r: r[2], reverse=True)
            text, confidence = results_sorted[0][1], results_sorted[0][2]
            if confidence >= 0.4:
                best_plate = _normalise_plate(text)
                best_confidence = confidence

        if best_plate and best_confidence >= 0.4:
            logger.info(f"OCR extracted plate: {best_plate} (confidence: {best_confidence:.2f})")
            return best_plate, round(best_confidence, 3)

        logger.info("OCR: no plate detected with sufficient confidence")
        return None, None

    except Exception as e:
        # Never let OCR failure block complaint submission
        logger.warning(f"OCR extraction failed: {e}. Complaint accepted without plate.")
        return None, None
