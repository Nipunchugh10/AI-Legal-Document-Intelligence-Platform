"""
Multimodal Document & Image Extractor Service
----------------------------------------------
Handles raw text extraction and Vision OCR from all legal contract input formats:
1. Standard Digital PDFs (.pdf)
2. Scanned / Photo-based PDFs (.pdf) via Gemini Vision OCR
3. Image & Photo Formats (.png, .jpg, .jpeg, .webp, .tiff, .bmp) via Gemini Vision OCR
4. Word Documents (.docx, .doc) via python-docx
5. Plain Text & Markdown (.txt, .md, .rtf)

Universal Legal Document Extraction & OCR Pipeline
"""

import os
import io
import logging
import warnings
from PIL import Image
from fastapi import HTTPException, status

with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    import google.generativeai as genai

from app.core.config import get_settings
from app.services.ai_usage_monitor import ai_usage_monitor

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp",
    ".docx", ".doc", ".txt", ".md", ".rtf"
}

# Ordered Gemini Vision cascade models utilizing separate Google AI Studio free-tier quota pools.
# Lite models lead: on the current free-tier key they are the buckets actually served,
# while the heavier `*-flash` buckets frequently return 429. Heavier flash models remain
# as deep fallbacks for OCR resilience if the lite buckets are exhausted.
VISION_CASCADE_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-2.5-flash",
]


def _ensure_genai_configured():
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
    genai.configure(api_key=settings.GEMINI_API_KEY)


def _preprocess_image_for_ocr(pil_image: Image.Image, max_dim: int = 2048) -> Image.Image:
    """
    Optimizes a PIL image for fast, token-efficient Gemini Vision OCR:
    - Normalizes color channels (converts RGBA/P/CMYK/LA/1 to RGB with white background).
    - Downscales high-resolution camera photos/scans if max dimension exceeds max_dim,
      preserving crisp legal typography while cutting latency and token consumption by >60%.
    """
    # 1. Color channel normalization
    if pil_image.mode in ("RGBA", "LA"):
        background = Image.new("RGB", pil_image.size, (255, 255, 255))
        background.paste(pil_image, mask=pil_image.split()[-1])
        img = background
    elif pil_image.mode != "RGB":
        img = pil_image.convert("RGB")
    else:
        img = pil_image

    # 2. Downsampling if exceeding max_dim
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        logger.info(f"Downsampled high-res image from ({w}, {h}) to {new_size} for Vision OCR")

    return img


def _extract_text_from_gemini_response(response) -> str:
    """
    Safely extracts text from a Gemini response, handling candidate parts without crashing.
    """
    if not response:
        return ""
    try:
        if hasattr(response, "text") and response.text:
            return response.text.strip()
    except Exception:
        pass

    # Inspect candidates in case .text accessor raised ValueError
    try:
        if hasattr(response, "candidates") and response.candidates:
            parts_text = []
            for candidate in response.candidates:
                if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                    for part in candidate.content.parts:
                        if hasattr(part, "text") and part.text:
                            parts_text.append(part.text)
            if parts_text:
                return "\n".join(parts_text).strip()
    except Exception as e:
        logger.debug(f"Candidate text extraction failed: {e}")

    return ""


def ocr_image_with_gemini(pil_image: Image.Image) -> str:
    """
    Passes a PIL Image object to Google Gemini Vision API for high-precision legal OCR.
    Automatically cascades through secondary Gemini models across separate free-tier quota pools
    if a 429 or transient error occurs.
    """
    _ensure_genai_configured()
    settings = get_settings()

    optimized_image = _preprocess_image_for_ocr(pil_image)

    # Candidate models starting with configured model, then cascade list
    candidate_models = [settings.GEMINI_MODEL]
    for m in VISION_CASCADE_MODELS:
        if m not in candidate_models:
            candidate_models.append(m)

    prompt = (
        "You are an expert high-accuracy legal document OCR and vision analysis system. "
        "Extract all readable text verbatim from this document, contract photo, or scan. "
        "Maintain paragraph structures, legal clause numbers, section titles, tables, financial figures, "
        "party names, dates, and signature blocks accurately. "
        "Do NOT summarize or skip any legal text. Return ONLY the raw extracted text."
    )

    last_error = None
    rate_limit_encountered = False

    for model_name in candidate_models:
        try:
            logger.info("Attempting Vision OCR with model: %s", model_name)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                [optimized_image, prompt],
                generation_config=genai.types.GenerationConfig(temperature=0.0)
            )
            extracted = _extract_text_from_gemini_response(response)
            if extracted:
                ai_usage_monitor.record_call("gemini_vision", model_name, "success")
                logger.info("Vision OCR successfully extracted %d characters using %s", len(extracted), model_name)
                return extracted

            logger.warning("Vision OCR model %s returned empty text. Trying next model...", model_name)
        except Exception as e:
            err_str = str(e)
            last_error = e
            is_rate_limit = "429" in err_str or "quota" in err_str.lower() or "ResourceExhausted" in err_str
            if is_rate_limit:
                rate_limit_encountered = True
                status_code = "rate_limited"
            else:
                status_code = "error"
            ai_usage_monitor.record_call("gemini_vision", model_name, status_code, error=err_str[:120])
            logger.warning("Vision OCR model %s failed: %s. Falling over to next model...", model_name, err_str[:120])
            continue

    if rate_limit_encountered:
        logger.error("All Vision OCR models exhausted or rate-limited: %s", last_error)
    elif last_error:
        logger.error("Vision OCR cascade failed across all models: %s", last_error)

    return ""


def extract_with_pymupdf(filepath: str) -> tuple[str, int]:
    """
    Fast extraction strategy using PyMuPDF (fitz), ideal for standard text-based PDFs.
    Returns: (extracted_text, page_count)
    """
    import fitz  # PyMuPDF

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found at {filepath}")

    text_parts = []
    doc = fitz.open(filepath)
    page_count = len(doc)

    for page in doc:
        text = page.get_text()
        if text:
            text_parts.append(text)

    doc.close()
    return "\n".join(text_parts), page_count


def extract_scanned_pdf_with_ocr(filepath: str) -> tuple[str, int]:
    """
    Renders pages of a scanned or photo-based PDF into high-resolution images
    and executes Gemini Vision OCR on each page.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(filepath)
    page_count = len(doc)
    extracted_page_texts = []

    logger.info(f"Executing Gemini Vision OCR on scanned PDF: {filepath} ({page_count} pages)")

    for i, page in enumerate(doc):
        # Render page to PNG pixmap (150 DPI for optimal speed and OCR clarity)
        pix = page.get_pixmap(dpi=150)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        
        page_text = ocr_image_with_gemini(img)
        if page_text:
            extracted_page_texts.append(f"--- Page {i + 1} ---\n{page_text}")

    doc.close()
    combined_text = "\n\n".join(extracted_page_texts)
    return combined_text, page_count


def extract_with_pdfplumber(filepath: str) -> tuple[str, int]:
    """
    Detailed extraction strategy using pdfplumber, optimal for tables and complex layouts.
    Returns: (extracted_text, page_count)
    """
    import pdfplumber

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found at {filepath}")

    text_parts = []
    with pdfplumber.open(filepath) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

    return "\n".join(text_parts), page_count


def extract_image_text(filepath: str) -> dict:
    """
    Extracts verbatim text from raw photos and image files (.png, .jpg, .jpeg, .webp, .tiff, .bmp)
    using Gemini Vision OCR with multi-model failover.
    """
    logger.info(f"Extracting text from image file via Gemini Vision OCR: {filepath}")
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image file not found at {filepath}"
        )

    try:
        pil_img = Image.open(filepath)
    except Exception as e:
        logger.error(f"Cannot open image file {filepath}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or unreadable image file: {str(e)}"
        )

    try:
        text = ocr_image_with_gemini(pil_img)
        if not text:
            logger.warning(f"Gemini Vision OCR returned empty text for image {filepath}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract readable text from the uploaded document image. Please ensure the document is clear, well-lit, and legible, or try again in a few moments."
            )
        
        return {
            "text": text,
            "page_count": 1,
            "is_scanned": True,
            "strategy": "gemini_vision_ocr"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image extraction failed for {filepath}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Image OCR extraction failed: {str(e)}"
        )


def extract_docx_text(filepath: str) -> dict:
    """
    Extracts text from Microsoft Word documents (.docx, .doc).
    """
    logger.info(f"Extracting text from Word document: {filepath}")
    try:
        import docx
        doc = docx.Document(filepath)
        full_text = []

        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text.strip())

        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    full_text.append(" | ".join(row_cells))

        combined_text = "\n".join(full_text)
        return {
            "text": combined_text,
            "page_count": 1,
            "is_scanned": False,
            "strategy": "python_docx"
        }
    except Exception as e:
        logger.error(f"DOCX extraction failed for {filepath}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Word document extraction failed: {str(e)}"
        )


def extract_plain_text(filepath: str) -> dict:
    """
    Extracts text from plain text or markdown files (.txt, .md, .rtf).
    """
    logger.info(f"Extracting plain text file: {filepath}")
    try:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
        except UnicodeDecodeError:
            with open(filepath, "r", encoding="latin-1") as f:
                text = f.read()

        return {
            "text": text,
            "page_count": 1,
            "is_scanned": False,
            "strategy": "plain_text"
        }
    except Exception as e:
        logger.error(f"Plain text extraction failed for {filepath}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text file extraction failed: {str(e)}"
        )


def extract_pdf_text(filepath: str, strategy: str = "pymupdf") -> dict:
    """
    Extracts text from a PDF file using PyMuPDF, pdfplumber, or Vision OCR fallback.
    Automatically handles scanned / photo-based PDFs.
    """
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF file not found on disk: {filepath}"
        )

    try:
        raw_text, page_count = extract_with_pymupdf(filepath)
    except Exception as e:
        logger.error(f"PyMuPDF extraction failed for {filepath}: {str(e)}")
        raw_text, page_count = "", 0

    # Detect if scanned (average characters per page < 15)
    is_scanned = False
    if page_count > 0:
        char_count = len(raw_text.strip())
        avg_chars = char_count / page_count
        if avg_chars < 15:
            is_scanned = True

    # If scanned or missing text, run Gemini Vision OCR
    if is_scanned or not raw_text.strip():
        logger.info(f"Detected scanned/photo PDF for {filepath}. Triggering Vision OCR pipeline.")
        try:
            ocr_text, page_count = extract_scanned_pdf_with_ocr(filepath)
            if ocr_text.strip():
                return {
                    "text": ocr_text,
                    "page_count": page_count,
                    "is_scanned": True,
                    "strategy": "gemini_vision_ocr"
                }
        except Exception as ocr_err:
            logger.warning(f"Vision OCR fallback failed: {str(ocr_err)}")

    if strategy == "pdfplumber" and not is_scanned:
        try:
            raw_text, page_count = extract_with_pdfplumber(filepath)
        except Exception:
            strategy = "pymupdf"

    return {
        "text": raw_text,
        "page_count": page_count,
        "is_scanned": is_scanned,
        "strategy": strategy
    }


def extract_document_text(filepath: str, strategy: str = "auto") -> dict:
    """
    Universal Extractor Entrypoint for all supported input file types:
    - PDFs (digital & scanned)
    - Photos & Image Scans (.png, .jpg, .jpeg, .webp, .tiff, .bmp)
    - Word Documents (.docx, .doc)
    - Text Files (.txt, .md, .rtf)
    """
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found on disk: {filepath}"
        )

    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".pdf":
        return extract_pdf_text(filepath, strategy=strategy)
    elif ext in [".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"]:
        return extract_image_text(filepath)
    elif ext in [".docx", ".doc"]:
        return extract_docx_text(filepath)
    elif ext in [".txt", ".md", ".rtf"]:
        return extract_plain_text(filepath)
    else:
        # Fallback plain text attempt
        return extract_plain_text(filepath)
