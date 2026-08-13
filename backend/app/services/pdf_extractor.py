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

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp",
    ".docx", ".doc", ".txt", ".md", ".rtf"
}


def _ensure_genai_configured():
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
    genai.configure(api_key=settings.GEMINI_API_KEY)


def ocr_image_with_gemini(pil_image: Image.Image) -> str:
    """
    Passes a PIL Image object to Google Gemini 3.5 Flash Vision API for high-precision legal OCR.
    """
    try:
        _ensure_genai_configured()
        settings = get_settings()
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        prompt = (
            "You are an expert high-accuracy legal document OCR and vision analysis system. "
            "Extract all readable text verbatim from this document, contract photo, or scan. "
            "Maintain paragraph structures, legal clause numbers, section titles, tables, financial figures, "
            "party names, dates, and signature blocks accurately. "
            "Do NOT summarize or skip any legal text. Return ONLY the raw extracted text."
        )
        
        response = model.generate_content([pil_image, prompt])
        if response and response.text:
            return response.text.strip()
        return ""
    except Exception as e:
        logger.error(f"Gemini Vision OCR failed: {str(e)}")
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
        # Render page to PNG pixmap (200 DPI for high OCR accuracy)
        pix = page.get_pixmap(dpi=200)
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
    using Gemini 3.5 Flash Vision OCR.
    """
    logger.info(f"Extracting text from image file via Gemini Vision OCR: {filepath}")
    try:
        pil_img = Image.open(filepath)
        text = ocr_image_with_gemini(pil_img)
        if not text:
            raise ValueError("Gemini Vision OCR returned empty text for image.")
        
        return {
            "text": text,
            "page_count": 1,
            "is_scanned": True,
            "strategy": "gemini_vision_ocr"
        }
    except Exception as e:
        logger.error(f"Image extraction failed for {filepath}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
