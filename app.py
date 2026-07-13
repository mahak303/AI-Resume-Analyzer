"""
app.py
──────
Main entry point for the AI Resume Analyzer Streamlit application.

This is the first working version of the app (Phase 4).
It covers:
  - Resume file upload (PDF / DOCX)
  - Text extraction via pdf_parser.extract_text()
  - Skill extraction via skill_extractor.extract_skills()
  - Display of extracted text, skill counts, skills by category,
    and a flat skill list

Run with:
    streamlit run app.py
"""

import logging
import streamlit as st

from config import (
    APP_TITLE,
    APP_ICON,
    APP_DESCRIPTION,
    PAGE_LAYOUT,
    SIDEBAR_STATE,
    ALLOWED_FILE_TYPES,
    MAX_FILE_SIZE_MB,
)
from src.pdf_parser import extract_text, get_file_info
from src.skill_extractor import extract_skills


# ── Logging Configuration ─────────────────────────────────────────────────────
# Configure logging once at the top of the entry point.
# All modules (pdf_parser, skill_extractor) use getLogger(__name__),
# so their messages will flow through this root configuration.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Page Configuration ────────────────────────────────────────────────────────

def configure_page() -> None:
    """
    Set Streamlit page metadata and layout.

    Must be the very first Streamlit call in the script.
    Values come from config.py so they never need to be changed here.
    """
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout=PAGE_LAYOUT,
        initial_sidebar_state=SIDEBAR_STATE,
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar() -> None:
    """
    Render the left sidebar with app information and usage instructions.

    Keeping sidebar content in its own function makes it easy to update
    without touching the main page layout.
    """
    with st.sidebar:
        st.title(f"{APP_ICON} {APP_TITLE}")
        st.markdown("---")

        st.markdown("### How to use")
        st.markdown(
            """
            1. Upload your resume (PDF or DOCX)
            2. Wait for text and skill extraction
            3. Review detected skills by category
            """
        )

        st.markdown("---")

        st.markdown("### Supported formats")
        for fmt in ALLOWED_FILE_TYPES:
            st.markdown(f"- `.{fmt.upper()}`")

        st.markdown(f"**Max file size:** {MAX_FILE_SIZE_MB} MB")

        st.markdown("---")
        st.caption("Built with Python · Streamlit · spaCy")


# ── File Upload Section ───────────────────────────────────────────────────────

def render_upload_section() -> object:
    """
    Render the file upload widget and return the uploaded file object.

    Returns:
        The uploaded file object from st.file_uploader,
        or None if no file has been uploaded yet.
    """
    st.header("Upload Your Resume")
    st.markdown(APP_DESCRIPTION)
    st.markdown("")  # Spacing

    uploaded_file = st.file_uploader(
        label="Choose a PDF or DOCX file",
        type=ALLOWED_FILE_TYPES,           # Streamlit enforces allowed types in the dialog
        help=f"Maximum file size: {MAX_FILE_SIZE_MB} MB",
    )

    return uploaded_file


# ── Extracted Text Section ────────────────────────────────────────────────────

def render_extracted_text(resume_text: str, file_name: str) -> None:
    """
    Display the extracted resume text inside a collapsible expander.

    Showing the raw text lets the user verify that extraction worked
    correctly before trusting the analysis results.

    Args:
        resume_text : The cleaned text extracted from the resume.
        file_name   : Original file name, shown in the expander label.
    """
    char_count = len(resume_text)
    word_count = len(resume_text.split())

    with st.expander(f"📄 Extracted Text from `{file_name}`", expanded=False):
        # Show basic stats above the raw text
        col1, col2 = st.columns(2)
        col1.metric("Characters", f"{char_count:,}")
        col2.metric("Words", f"{word_count:,}")

        st.markdown("---")
        # Display raw text in a fixed-height scrollable area
        st.text_area(
            label="Raw extracted text",
            value=resume_text,
            height=300,
            disabled=True,          # Read-only — user should not edit this
            label_visibility="collapsed",
        )


# ── Skills Summary Section ────────────────────────────────────────────────────

def render_skills_summary(skill_results: dict) -> None:
    """
    Display a top-level summary of how many skills were detected.

    Args:
        skill_results: The dictionary returned by extract_skills(),
                       with keys "all_skills" and "by_category".
    """
    all_skills      = skill_results["all_skills"]
    by_category     = skill_results["by_category"]
    total_skills    = len(all_skills)
    total_categories = len(by_category)

    st.markdown("---")
    st.header("🔍 Skill Detection Results")

    # Top-level metric cards
    col1, col2 = st.columns(2)
    col1.metric(
        label="Total Skills Detected",
        value=total_skills,
        help="Number of unique skills found in your resume",
    )
    col2.metric(
        label="Skill Categories",
        value=total_categories,
        help="Number of distinct skill categories represented",
    )

    if total_skills == 0:
        st.warning(
            "⚠️ No skills were detected in this resume. "
            "Make sure your resume contains a dedicated skills section "
            "and uses standard skill names."
        )


# ── Skills by Category Section ────────────────────────────────────────────────

def render_skills_by_category(by_category: dict[str, list]) -> None:
    """
    Display detected skills grouped by their category.

    Each category is shown as a labelled section with skill tags (badges).
    Categories are sorted alphabetically for consistency.

    Args:
        by_category: Dict mapping category name → list of skill name strings.
    """
    if not by_category:
        return

    st.subheader("Skills by Category")

    # Sort categories alphabetically so the order is consistent across runs
    for category in sorted(by_category.keys()):
        skills_in_category = by_category[category]

        # Format each skill as a small inline badge using markdown
        # st.markdown renders these as bold inline text separated by gaps
        badges = "  ".join([f"`{skill}`" for skill in sorted(skills_in_category)])

        st.markdown(f"**{category}** ({len(skills_in_category)})")
        st.markdown(badges)
        st.markdown("")   # Small visual gap between categories


# ── Flat Skills List Section ──────────────────────────────────────────────────

def render_all_skills_flat(all_skills: list[str]) -> None:
    """
    Display all detected skills as a single flat sorted list inside an expander.

    This gives the user a quick copy-paste reference of every skill found.

    Args:
        all_skills: Flat list of all matched skill name strings.
    """
    if not all_skills:
        return

    with st.expander("📋 Full Skill List (alphabetical)", expanded=False):
        # Sort and display as a comma-separated list for easy scanning
        sorted_skills = sorted(all_skills)
        st.markdown(", ".join([f"`{s}`" for s in sorted_skills]))


# ── File Info Banner ──────────────────────────────────────────────────────────

def render_file_info(uploaded_file) -> None:
    """
    Display a small info banner showing the uploaded file's metadata.

    Args:
        uploaded_file: The Streamlit uploaded file object.
    """
    info = get_file_info(uploaded_file)
    st.success(
        f"✅ File uploaded: **{info['name']}** "
        f"({info['extension']} · {info['size_mb']} MB)"
    )


# ── Analysis Pipeline ─────────────────────────────────────────────────────────

def run_analysis(uploaded_file) -> None:
    """
    Orchestrate the full analysis pipeline for a given uploaded file.

    Steps:
      1. Display file info banner
      2. Extract text from the file (with a loading spinner)
      3. Render the extracted text in an expandable section
      4. Extract skills from the text (with a loading spinner)
      5. Render skill summary, skills by category, and flat skill list

    All exceptions from the pipeline are caught here and shown to the
    user as friendly error messages rather than raw tracebacks.

    Args:
        uploaded_file: The Streamlit uploaded file object.
    """
    # ── Step 1: File info ──────────────────────────────────────────────────
    render_file_info(uploaded_file)
    logger.info("Processing uploaded file: %s", uploaded_file.name)

    # ── Step 2: Text extraction ────────────────────────────────────────────
    resume_text = _extract_text_with_spinner(uploaded_file)
    if resume_text is None:
        return   # Error was already shown to the user; stop here

    # ── Step 3: Show extracted text ────────────────────────────────────────
    render_extracted_text(resume_text, uploaded_file.name)

    # ── Step 4: Skill extraction ───────────────────────────────────────────
    skill_results = _extract_skills_with_spinner(resume_text)
    if skill_results is None:
        return   # Error was already shown to the user; stop here

    # ── Step 5: Display skill results ──────────────────────────────────────
    render_skills_summary(skill_results)

    if skill_results["all_skills"]:
        render_skills_by_category(skill_results["by_category"])
        render_all_skills_flat(skill_results["all_skills"])

    logger.info(
        "Analysis complete for %s — %d skill(s) found",
        uploaded_file.name,
        len(skill_results["all_skills"]),
    )


def _extract_text_with_spinner(uploaded_file) -> str | None:
    """
    Run extract_text() inside a Streamlit spinner and handle errors.

    Separating spinner logic from render logic keeps run_analysis() clean.

    Args:
        uploaded_file: The Streamlit uploaded file object.

    Returns:
        Extracted text string on success, or None if extraction failed.
    """
    try:
        with st.spinner("Extracting text from your resume…"):
            resume_text = extract_text(uploaded_file)
        return resume_text

    except ValueError as e:
        # ValueError = file validation failure (wrong type, too large)
        st.error(f"❌ Invalid file: {e}")
        logger.warning("File validation failed for %s: %s", uploaded_file.name, str(e))
        return None

    except RuntimeError as e:
        # RuntimeError = extraction failure (corrupted PDF, empty file, etc.)
        st.error(f"❌ Could not extract text: {e}")
        logger.error("Text extraction failed for %s: %s", uploaded_file.name, str(e))
        return None

    except Exception as e:
        # Catch-all for unexpected errors — show a generic message
        st.error("❌ An unexpected error occurred while reading your file.")
        logger.exception("Unexpected error during text extraction: %s", str(e))
        return None


def _extract_skills_with_spinner(resume_text: str) -> dict | None:
    """
    Run extract_skills() inside a Streamlit spinner and handle errors.

    Args:
        resume_text: Cleaned resume text string.

    Returns:
        Skill results dictionary on success, or None if extraction failed.
    """
    try:
        with st.spinner("Detecting skills using NLP…"):
            skill_results = extract_skills(resume_text)
        return skill_results

    except RuntimeError as e:
        # RuntimeError from skill_extractor = spaCy model not loaded, CSV missing, etc.
        st.error(f"❌ Skill extraction failed: {e}")
        logger.error("Skill extraction failed: %s", str(e))
        return None

    except Exception as e:
        st.error("❌ An unexpected error occurred during skill detection.")
        logger.exception("Unexpected error during skill extraction: %s", str(e))
        return None


# ── App Entry Point ───────────────────────────────────────────────────────────

def main() -> None:
    """
    Main function — sets up the page and drives the full app flow.

    Streamlit re-runs this entire function from top to bottom every time
    the user interacts with the app (uploads a file, clicks a button, etc.).
    That is normal Streamlit behaviour — state is managed via st.session_state
    if needed in future phases.
    """
    configure_page()
    render_sidebar()

    # Page title visible in the main content area
    st.title(f"{APP_ICON} {APP_TITLE}")
    st.markdown("---")

    # Render the upload widget and get the file (or None)
    uploaded_file = render_upload_section()

    # Only run the analysis pipeline once a file has been uploaded
    if uploaded_file is not None:
        st.markdown("---")
        run_analysis(uploaded_file)
    else:
        # Show a friendly prompt when no file is uploaded yet
        st.markdown("")
        st.info("👆 Upload a resume above to get started.")


# Standard Python entry point guard
if __name__ == "__main__":
    main()