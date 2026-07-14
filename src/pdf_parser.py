"""
Handles reading resume files (PDF and DOCX) and extracting clean text from them.

This module does two things:
  1. Extract raw text from the uploaded file based on its type.
  2. Clean that raw text so the rest of the pipeline receives consistent input.

No NLP or skill matching happens here — this module only deals with files and text.
"""

import re
import logging
import pdfplumber
import docx

from config import ALLOWED_FILE_TYPES, MAX_FILE_SIZE_MB

# ── Logger Setup ──────────────────────────────────────────────────────────────
# Each module gets its own logger named after the module.
# This makes it easy to trace which module produced a log message.
logger = logging.getLogger(__name__)


# ── Main Entry Point ──────────────────────────────────────────────────────────

def extract_text(uploaded_file) -> str:
    """
    Extract and clean text from an uploaded resume file.

    This is the only function the rest of the app needs to call.
    It automatically detects the file type and routes to the
    correct extractor.

    Args:
        uploaded_file: The file object from Streamlit's st.file_uploader.

    Returns:
        A clean string of text extracted from the resume.

    Raises:
        ValueError: If the file type is not supported or the file is too large.
        RuntimeError: If text extraction fails for any reason.
    """
    logger.info("Starting text extraction for file: %s", uploaded_file.name)

    # Validate the file before attempting to read it
    _validate_file(uploaded_file)

    # Get the file extension in lowercase (e.g. "pdf" or "docx")
    file_extension = uploaded_file.name.split(".")[-1].lower()

    try:
        if file_extension == "pdf":
            raw_text = _extract_from_pdf(uploaded_file)
        elif file_extension == "docx":
            raw_text = _extract_from_docx(uploaded_file)
        else:
            raise ValueError(f"Unsupported file type: .{file_extension}")

        # Clean the extracted text before returning it
        cleaned_text = _clean_text(raw_text)

        # Make sure we actually got some content
        if not cleaned_text.strip():
            raise RuntimeError(
                "No text could be extracted from this file. "
                "The resume may be scanned as an image or the file may be corrupted."
            )

        logger.info(
            "Successfully extracted %d characters from %s",
            len(cleaned_text),
            uploaded_file.name,
        )
        return cleaned_text

    except (ValueError, RuntimeError):
        # Re-raise our own exceptions without wrapping them
        raise
    except Exception as e:
        logger.error("Unexpected error extracting text from %s: %s", uploaded_file.name, str(e))
        raise RuntimeError(f"Failed to extract text from resume: {str(e)}")


# ── File Validation ───────────────────────────────────────────────────────────

def _validate_file(uploaded_file) -> None:
    """
    Check that the uploaded file meets our requirements before processing.

    Checks:
      - File extension is in ALLOWED_FILE_TYPES (from config.py)
      - File size does not exceed MAX_FILE_SIZE_MB (from config.py)

    Args:
        uploaded_file: The file object from Streamlit's st.file_uploader.

    Raises:
        ValueError: If the file type or size is not acceptable.
    """
    if uploaded_file is None:
        raise ValueError("No file was uploaded.")

    # Check file extension
    file_extension = uploaded_file.name.split(".")[-1].lower()
    if file_extension not in ALLOWED_FILE_TYPES:
        logger.warning("Rejected unsupported file type: .%s", file_extension)
        raise ValueError(
            f"File type '.{file_extension}' is not supported. "
            f"Please upload a {' or '.join(ALLOWED_FILE_TYPES).upper()} file."
        )

    # Check file size — uploaded_file.size is in bytes, so convert to MB
    file_size_mb = uploaded_file.size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        logger.warning(
            "Rejected oversized file: %.2f MB (limit: %d MB)",
            file_size_mb,
            MAX_FILE_SIZE_MB,
        )
        raise ValueError(
            f"File size ({file_size_mb:.1f} MB) exceeds the maximum "
            f"allowed size of {MAX_FILE_SIZE_MB} MB."
        )

    logger.debug("File validation passed for: %s (%.2f MB)", uploaded_file.name, file_size_mb)


# ── PDF Extraction ────────────────────────────────────────────────────────────

def _extract_from_pdf(uploaded_file) -> str:
    """
    Extract text from a PDF file using pdfplumber.

    pdfplumber reads each page of the PDF and extracts the text content.
    We join all pages together with a newline between them.
    Pages that contain only images (no selectable text) are skipped gracefully.

    Args:
        uploaded_file: The PDF file object from Streamlit.

    Returns:
        Raw text string extracted from all readable pages of the PDF.

    Raises:
        RuntimeError: If the PDF cannot be opened or has no readable pages.
    """
    text_pages = []

    try:
        # pdfplumber can read from a file-like object directly
        with pdfplumber.open(uploaded_file) as pdf:
            total_pages = len(pdf.pages)
            logger.debug("PDF has %d page(s)", total_pages)

            if total_pages == 0:
                raise RuntimeError("The PDF file has no pages.")

            for page_number, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()

                if page_text and page_text.strip():
                    text_pages.append(page_text)
                    logger.debug("Extracted text from page %d/%d", page_number, total_pages)
                else:
                    # This page may be an image — log and skip
                    logger.warning(
                        "Page %d/%d yielded no text (possibly an image)",
                        page_number,
                        total_pages,
                    )

    except RuntimeError:
        raise
    except Exception as e:
        logger.error("pdfplumber failed to open the file: %s", str(e))
        raise RuntimeError(f"Could not read PDF file: {str(e)}")

    if not text_pages:
        raise RuntimeError(
            "Could not extract text from any page in this PDF. "
            "The file may contain scanned images instead of selectable text."
        )

    logger.info("Extracted text from %d/%d PDF page(s)", len(text_pages), total_pages)
    return "\n".join(text_pages)


# ── DOCX Extraction ───────────────────────────────────────────────────────────

def _extract_from_docx(uploaded_file) -> str:
    """
    Extract text from a DOCX file using python-docx.

    A DOCX file is structured as paragraphs. We read each paragraph
    and join them with newlines to preserve the resume's structure.

    Args:
        uploaded_file: The DOCX file object from Streamlit.

    Returns:
        Raw text string extracted from all paragraphs in the document.

    Raises:
        RuntimeError: If the DOCX file cannot be read or is empty.
    """
    try:
        document = docx.Document(uploaded_file)
    except Exception as e:
        logger.error("python-docx failed to open the file: %s", str(e))
        raise RuntimeError(f"Could not open DOCX file: {str(e)}")

    # Extract text from each paragraph, skipping empty ones
    paragraphs = [
        paragraph.text
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    if not paragraphs:
        raise RuntimeError("The DOCX file appears to be empty.")

    logger.info("Extracted %d paragraph(s) from DOCX", len(paragraphs))
    return "\n".join(paragraphs)


# ── Text Cleaning ─────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """
    Clean and normalize raw extracted text.

    Raw text from PDFs often contains unwanted characters, inconsistent
    spacing, and encoding artifacts. This function standardizes the text
    so that the skill extractor and analyzer receive consistent input.

    Cleaning steps (in order):
      1. Replace non-standard whitespace characters with a regular space
      2. Remove non-printable / control characters
      3. Collapse multiple spaces into one
      4. Collapse more than two consecutive newlines into two
      5. Strip leading and trailing whitespace from each line
      6. Strip overall leading and trailing whitespace

    Args:
        text: Raw text string from the PDF or DOCX extractor.

    Returns:
        Cleaned and normalized text string.
    """
    if not text:
        return ""

    # Step 1: Replace tabs and non-breaking spaces with a regular space
    text = text.replace("\t", " ").replace("\xa0", " ")

    # Step 2: Remove non-printable control characters
    # We keep \x0a (newline) and remove everything else in the control range
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)

    # Step 3: Collapse multiple spaces into a single space
    text = re.sub(r" {2,}", " ", text)

    # Step 4: Collapse more than two consecutive blank lines into two
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Step 5: Strip leading/trailing spaces from each individual line
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)

    # Step 6: Strip the entire text block
    cleaned = text.strip()

    logger.debug("Text cleaning complete. Length: %d → %d characters", len(text), len(cleaned))
    return cleaned


# ── Utility: Get Basic File Info ──────────────────────────────────────────────

def get_file_info(uploaded_file) -> dict:
    """
    Return basic information about the uploaded file.

    Useful for displaying file details in the Streamlit UI before analysis.

    Args:
        uploaded_file: The file object from Streamlit's st.file_uploader.

    Returns:
        Dictionary with keys: name, extension, size_mb.
    """
    return {
        "name":      uploaded_file.name,
        "extension": uploaded_file.name.split(".")[-1].upper(),
        "size_mb":   round(uploaded_file.size / (1024 * 1024), 2),
    }