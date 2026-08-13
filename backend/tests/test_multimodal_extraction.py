import os
import pytest
from app.services.pdf_extractor import extract_document_text, SUPPORTED_EXTENSIONS

def test_supported_extensions_registered():
 assert ".pdf" in SUPPORTED_EXTENSIONS
 assert ".png" in SUPPORTED_EXTENSIONS
 assert ".jpg" in SUPPORTED_EXTENSIONS
 assert ".jpeg" in SUPPORTED_EXTENSIONS
 assert ".docx" in SUPPORTED_EXTENSIONS
 assert ".txt" in SUPPORTED_EXTENSIONS

def test_extract_plain_text_file(tmp_path):
 txt_file = tmp_path / "sample_contract.txt"
 txt_file.write_text("THIS IS A FREELANCE SERVICES AGREEMENT BETWEEN PARTY A AND PARTY B.")
 
 result = extract_document_text(str(txt_file))
 assert result["text"].strip() == "THIS IS A FREELANCE SERVICES AGREEMENT BETWEEN PARTY A AND PARTY B."
 assert result["strategy"] == "plain_text"
 assert result["is_scanned"] is False

def test_extract_docx_file(tmp_path):
 import docx
 docx_file = tmp_path / "sample_contract.docx"
 doc = docx.Document()
 doc.add_heading("NON-DISCLOSURE AGREEMENT", level=1)
 doc.add_paragraph("This NDA is entered into on August 13, 2026.")
 doc.save(str(docx_file))

 result = extract_document_text(str(docx_file))
 assert "NON-DISCLOSURE AGREEMENT" in result["text"]
 assert "August 13, 2026" in result["text"]
 assert result["strategy"] == "python_docx"
