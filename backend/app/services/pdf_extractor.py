"""
PDF Extractor Service
---------------------
Handles raw text extraction from PDF contracts using PyMuPDF and pdfplumber strategies.
Detects if PDFs are text-based or scanned.

Day 16 — PDF Text Extraction
"""

import os
from fastapi import HTTPException, status


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


def extract_pdf_text(filepath: str, strategy: str = "pymupdf") -> dict:
    """
    Extracts text from a PDF file using the specified strategy.
    Detects if the PDF is scanned (requires OCR) or text-based.
    
    Returns:
        A dictionary containing:
        - text: str (the extracted text)
        - page_count: int
        - is_scanned: bool (True if the PDF contains little/no digital text)
        - strategy: str
    """
    # 1. Verify file exists
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF file not found on disk: {filepath}"
        )

    # 2. Extract using PyMuPDF initially to check page count and get first-draft text
    try:
        raw_text, page_count = extract_with_pymupdf(filepath)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PyMuPDF extraction failed: {str(e)}"
        )

    # 3. Detect if scanned (digital text is negligible relative to page count)
    # Threshold: if average character count per page is less than 15, assume it is scanned
    is_scanned = False
    if page_count > 0:
        char_count = len(raw_text.strip())
        avg_chars = char_count / page_count
        if avg_chars < 15:
            is_scanned = True

    # 4. If the user explicitly requested pdfplumber and it's not scanned, run pdfplumber
    if strategy == "pdfplumber" and not is_scanned:
        try:
            raw_text, page_count = extract_with_pdfplumber(filepath)
        except Exception as e:
            # Fall back to PyMuPDF raw_text instead of failing entirely
            strategy = "pymupdf"

    return {
        "text": raw_text,
        "page_count": page_count,
        "is_scanned": is_scanned,
        "strategy": strategy
    }
