import re
from langchain_text_splitters import RecursiveCharacterTextSplitter

def clean_text(text: str) -> str:
    """
    Preprocess raw text before chunking:
    - Normalizes line breaks (converts CRLF to LF)
    - Removes page headers and footers matching typical patterns (e.g. "Page 1 of 5", "Page 1", lone numbers on a line)
    - Replaces excessive consecutive whitespace/newlines with clean separators
    - Collapses multiple horizontal spaces or tabs into a single space
    """
    if not text:
        return ""

    # 1. Normalize line endings to Unix style (\n)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Split into lines to apply line-by-line filters (like headers/footers)
    lines = text.split("\n")
    cleaned_lines = []

    # Heuristic pattern to match headers/footers:
    # - "Page 1", "Page 1 of 5", "Page [number]"
    # - Just a number on a line (common page number footer)
    # - "Confidential", "Draft", "Contract Agreement" repeated on page boundaries
    page_marker_pattern = re.compile(
        r"^\s*(?:"
        r"(?i:page)\s*\d+(?:\s+(?i:of)\s*\d+)?"  # "Page X" or "Page X of Y" (case-insensitive)
        r"|\d+"                                   # Single standalone numbers
        r"|(?i:confidential)"                     # Standalone "Confidential"
        r")\s*$"
    )

    for line in lines:
        stripped = line.strip()
        # Skip lines that look like page numbers, headers, footers
        if page_marker_pattern.match(stripped):
            continue
        
        # Collapse multiple horizontal whitespaces (spaces/tabs) to a single space
        collapsed_line = re.sub(r"[ \t]+", " ", line)
        cleaned_lines.append(collapsed_line)

    # Reassemble text
    text = "\n".join(cleaned_lines)

    # 3. Clean up vertical spacing:
    # - Replace 3 or more consecutive newlines with exactly 2 newlines (preserve paragraph separation)
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # - Strip leading/trailing whitespaces of the entire document
    return text.strip()

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    """
    Preprocesses the input text and splits it into overlapping chunks of a target token length
    using RecursiveCharacterTextSplitter with a tiktoken encoder.
    """
    cleaned = clean_text(text)
    if not cleaned:
        return []

    # Initialize the text splitter configured to count lengths by token using the cl100k_base encoder (used by GPT-4/modern models)
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    return text_splitter.split_text(cleaned)
