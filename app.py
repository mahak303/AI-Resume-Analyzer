"""
Main entry point for the AI Resume Analyzer Streamlit application.

Phase 4 Part 2 — integrates the ATS scoring engine.
Covers:
  - Job role selection via dropdown (loaded dynamically from job_roles.json)
  - Resume file upload (PDF / DOCX)
  - Text extraction  → pdf_parser.extract_text()
  - Skill extraction → skill_extractor.extract_skills()
  - ATS scoring      → ats_scorer.calculate_ats_score()
  - Display of: ATS score, grade, strengths, missing skills,
                suggestions, and per-category score breakdown

Run with:
    streamlit run app.py
"""

import json
import logging

import streamlit as st

from config import (
    APP_DESCRIPTION,
    APP_ICON,
    APP_TITLE,
    ALLOWED_FILE_TYPES,
    JOB_ROLES_JSON_PATH,
    MAX_FILE_SIZE_MB,
    PAGE_LAYOUT,
    SCORE_COLORS,
    SIDEBAR_STATE,
)
from src.ats_engine import calculate_ats_score
from src.pdf_parser import extract_text, get_file_info
from src.skill_extractor import extract_skills, get_all_skills
from src.suggestions import get_learning_steps

# ── Logging Configuration ─────────────────────────────────────────────────────
# Configured once here at the entry point; all src/ modules inherit this.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Job Roles Loader ──────────────────────────────────────────────────────────

@st.cache_data
def load_job_roles() -> list[str]:
    """
    Load available job role names from job_roles.json.

    Decorated with @st.cache_data so the file is only read once per
    Streamlit session, not on every re-run.

    Returns:
        Sorted list of job role name strings.

    Raises:
        RuntimeError: If the file cannot be found or parsed.
    """
    try:
        with open(JOB_ROLES_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        roles = sorted(data["roles"].keys())
        logger.info("Loaded %d job roles from job_roles.json", len(roles))
        return roles
    except FileNotFoundError:
        logger.error("job_roles.json not found at: %s", JOB_ROLES_JSON_PATH)
        raise RuntimeError(
            "job_roles.json not found. "
            "Make sure the data/ folder exists and contains job_roles.json."
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to parse job_roles.json: %s", str(e))
        raise RuntimeError(f"Could not read job roles: {e}")


# ── Page Configuration ────────────────────────────────────────────────────────

def configure_page() -> None:
    """
    Set Streamlit page metadata and layout.

    Must be the very first Streamlit call in the script.
    All values come from config.py.
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
    Render the left sidebar with usage instructions and app metadata.
    """
    with st.sidebar:
        st.title(f"{APP_ICON} {APP_TITLE}")
        st.markdown("---")

        st.markdown("### How to use")
        st.markdown(
            """
            1. Select a target job role
            2. Upload your resume (PDF or DOCX)
            3. Click **Analyze Resume**
            4. Review your ATS score, role match %, and feedback
            """
        )

        st.markdown("---")
        st.markdown("### Supported formats")
        for fmt in ALLOWED_FILE_TYPES:
            st.markdown(f"- `.{fmt.upper()}`")
        st.markdown(f"**Max file size:** {MAX_FILE_SIZE_MB} MB")

        st.markdown("---")
        st.markdown("### ATS Score Guide")
        st.markdown("🟢 **85–100** Excellent")
        st.markdown("🟡 **70–84**  Good")
        st.markdown("🟠 **50–69**  Fair")
        st.markdown("🔴 **0–49**   Needs Work")

        st.markdown("---")
        st.caption("Built with Python · Streamlit · spaCy")


# ── Job Role Selector ─────────────────────────────────────────────────────────

def render_job_role_selector(job_roles: list[str]) -> str:
    """
    Render a selectbox for the user to choose a target job role.

    The list of roles is loaded dynamically from job_roles.json
    so adding a new role to the JSON file automatically appears here.

    Args:
        job_roles: Sorted list of available job role name strings.

    Returns:
        The selected job role name string.
    """
    st.header("① Select a Target Job Role")
    st.markdown(
        "Choose the role you are applying for. "
        "The ATS score will be calculated against that role's requirements."
    )

    selected_role = st.selectbox(
        label="Target job role",
        options=job_roles,
        index=0,
        help="Your resume will be scored against the skills required for this role.",
        label_visibility="collapsed",
    )

    logger.debug("User selected job role: %s", selected_role)
    return selected_role


# ── File Upload Section ───────────────────────────────────────────────────────

def render_upload_section() -> object:
    """
    Render the resume file upload widget.

    Returns:
        Streamlit uploaded file object, or None if no file uploaded yet.
    """
    st.header("② Upload Your Resume")
    st.markdown(APP_DESCRIPTION)

    uploaded_file = st.file_uploader(
        label="Choose a PDF or DOCX file",
        type=ALLOWED_FILE_TYPES,
        help=f"Maximum file size: {MAX_FILE_SIZE_MB} MB",
    )
    return uploaded_file


# ── File Info Banner ──────────────────────────────────────────────────────────

def render_file_info(uploaded_file) -> None:
    """
    Display a success banner with the uploaded file's name, type, and size.

    Args:
        uploaded_file: The Streamlit uploaded file object.
    """
    info = get_file_info(uploaded_file)
    st.success(
        f"✅ File uploaded: **{info['name']}** "
        f"({info['extension']} · {info['size_mb']} MB)"
    )


# ── Extracted Text Section ────────────────────────────────────────────────────

def render_extracted_text(resume_text: str, file_name: str) -> None:
    """
    Display the extracted resume text in a collapsible expander.

    Lets the user verify the text was read correctly before trusting the score.

    Args:
        resume_text : Cleaned text from the resume.
        file_name   : Original filename shown in the expander label.
    """
    with st.expander(f"📄 Extracted Text from `{file_name}`", expanded=False):
        col1, col2 = st.columns(2)
        col1.metric("Characters", f"{len(resume_text):,}")
        col2.metric("Words", f"{len(resume_text.split()):,}")
        st.markdown("---")
        st.text_area(
            label="extracted_text",
            value=resume_text,
            height=300,
            disabled=True,
            label_visibility="collapsed",
        )


# ── Job Role Match Section ────────────────────────────────────────────────────

def render_job_match_section(ats_result: dict, job_role: str) -> None:
    """
    Render the job role match percentage and preferred skills analysis.

    This section is distinct from the ATS score:
      - ATS Score   = how well the resume is formatted and written overall
      - Match %     = what fraction of THIS role's required skills are present

    Displays:
      - Match percentage metric
      - Skill summary (required/preferred matched vs missing)
      - Preferred skills found / missing

    Args:
        ats_result : Dictionary returned by calculate_ats_score().
        job_role   : Selected job role name string.
    """
    match_pct        = ats_result["match_percentage"]
    matched_required = ats_result["matched_required"]
    missing_required = ats_result["missing_required"]
    matched_preferred = ats_result["matched_preferred"]
    missing_preferred = ats_result["missing_preferred"]
    total_required   = ats_result["total_required"]
    total_preferred  = ats_result["total_preferred"]

    st.markdown("---")
    st.header(f"🎯 Role Match — {job_role}")

    # ── Match percentage + skill summary metrics ───────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)

    match_color = _get_score_color(match_pct)
    col1.markdown(
        f"<h2 style='color:{match_color}; margin:0'>{match_pct}%</h2>"
        f"<p style='color:grey; font-size:0.8rem; margin:0'>Role Match</p>",
        unsafe_allow_html=True,
    )
    col2.metric(
        label="Required Matched",
        value=f"{len(matched_required)} / {total_required}",
        help="Required skills found in your resume vs total required for this role.",
    )
    col3.metric(
        label="Required Missing",
        value=len(missing_required),
        help="Required skills not found in your resume.",
        delta=f"-{len(missing_required)}" if missing_required else None,
        delta_color="inverse",
    )
    col4.metric(
        label="Preferred Matched",
        value=f"{len(matched_preferred)} / {total_preferred}",
        help="Preferred (bonus) skills found in your resume.",
    )
    col5.metric(
        label="Preferred Missing",
        value=len(missing_preferred),
        help="Preferred skills not found — not penalised, but good to add.",
    )

    st.markdown("")

    # ── Preferred skills breakdown ─────────────────────────────────────────
    st.subheader("Preferred Skills Analysis")
    st.caption(
        "Preferred skills are not required but strengthen your application. "
        "They are not penalised if missing."
    )

    pref_col1, pref_col2 = st.columns(2)

    with pref_col1:
        st.markdown("**✓ Preferred Skills Found**")
        if matched_preferred:
            for skill in sorted(matched_preferred):
                st.markdown(f"✅ `{skill}`")
        else:
            st.info("No preferred skills detected.")

    with pref_col2:
        st.markdown("**✗ Preferred Skills Missing**")
        if missing_preferred:
            for skill in sorted(missing_preferred):
                st.markdown(f"➕ `{skill}`")
        else:
            st.success("All preferred skills are present!")

    # ── Required skills detail in expander ────────────────────────────────
    with st.expander("📋 Required Skills Detail", expanded=False):
        req_col1, req_col2 = st.columns(2)

        with req_col1:
            st.markdown("**✓ Required Skills Found**")
            if matched_required:
                for skill in sorted(matched_required):
                    st.markdown(f"✅ `{skill}`")
            else:
                st.warning("No required skills detected.")

        with req_col2:
            st.markdown("**✗ Required Skills Missing**")
            if missing_required:
                for skill in sorted(missing_required):
                    st.markdown(f"❌ `{skill}`")
            else:
                st.success("All required skills are present!")

    logger.debug(
        "Job match rendered — match: %d%% | req matched: %d | pref matched: %d",
        match_pct, len(matched_required), len(matched_preferred),
    )




def _get_score_color(score: int) -> str:
    """
    Return the hex colour associated with an ATS score band.

    Colour thresholds are read from SCORE_COLORS in config.py.

    Args:
        score: ATS score integer 0–100.

    Returns:
        Hex colour string, e.g. "#2ecc71".
    """
    if score >= 85:
        return SCORE_COLORS["excellent"]
    elif score >= 70:
        return SCORE_COLORS["good"]
    elif score >= 50:
        return SCORE_COLORS["fair"]
    else:
        return SCORE_COLORS["poor"]


def render_ats_score(ats_result: dict, job_role: str) -> None:
    """
    Render the full ATS analysis result section.

    Displays in order:
      1. Score headline (large coloured metric + grade badge)
      2. Strengths
      3. Missing skills
      4. Suggestions
      5. Per-category score breakdown

    Args:
        ats_result : Dictionary returned by calculate_ats_score().
        job_role   : Selected job role name, shown in the section header.
    """
    score       = ats_result["ats_score"]
    grade       = ats_result["grade"]
    strengths   = ats_result["strengths"]
    missing     = ats_result["missing_skills"]
    suggestions = ats_result["suggestions"]
    breakdown   = ats_result["breakdown"]
    color       = _get_score_color(score)

    st.markdown("---")
    st.header(f"③ ATS Analysis — {job_role}")

    # ── Score headline ─────────────────────────────────────────────────────
    col_score, col_grade = st.columns([1, 2])

    with col_score:
        # Use HTML to render a large coloured score number
        st.markdown(
            f"<h1 style='color:{color}; margin:0;'>{score}<span style='font-size:1rem;'>/100</span></h1>",
            unsafe_allow_html=True,
        )
        st.caption("ATS Score")

    with col_grade:
        st.markdown(
            f"<h2 style='color:{color}; margin-top:0.4rem;'>{grade}</h2>",
            unsafe_allow_html=True,
        )
        st.caption("Overall Grade")

    st.markdown("")

    # ── Strengths ──────────────────────────────────────────────────────────
    st.subheader("✅ Strengths")
    if strengths:
        for strength in strengths:
            st.markdown(f"- {strength}")
    else:
        st.info("No notable strengths detected. Review the suggestions below.")

    # ── Missing Skills ─────────────────────────────────────────────────────
    st.subheader("❌ Missing Required Skills")
    if missing:
        # Display as inline code badges for easy reading
        badges = "  ".join([f"`{skill}`" for skill in missing])
        st.markdown(badges)
        st.caption(
            f"{len(missing)} required skill(s) not found in your resume. "
            "Add these to improve your score."
        )
    else:
        st.success("All required skills for this role were detected in your resume.")

    # ── Suggestions ────────────────────────────────────────────────────────
    st.subheader("💡 Suggestions")
    if suggestions:
        for i, suggestion in enumerate(suggestions, start=1):
            st.markdown(f"**{i}.** {suggestion}")
    else:
        st.success("Your resume looks well-optimised for this role. Great work!")

    # ── Score Breakdown ────────────────────────────────────────────────────
    st.subheader("📊 Score Breakdown")
    st.caption("Individual score for each ATS category (0–100 before weighting).")

    for category, cat_score in breakdown.items():
        # Choose bar colour based on the sub-score value
        if cat_score >= 80:
            bar_color = SCORE_COLORS["excellent"]
        elif cat_score >= 55:
            bar_color = SCORE_COLORS["good"]
        elif cat_score >= 35:
            bar_color = SCORE_COLORS["fair"]
        else:
            bar_color = SCORE_COLORS["poor"]

        col_label, col_bar = st.columns([1, 3])
        col_label.markdown(f"**{category}**")

        # Render a simple HTML progress-bar-style indicator
        col_bar.markdown(
            f"""
            <div style="background:#e0e0e0; border-radius:6px; height:22px; width:100%;">
              <div style="background:{bar_color}; width:{cat_score}%; border-radius:6px;
                          height:22px; display:flex; align-items:center;
                          padding-left:8px; color:white; font-size:0.8rem; font-weight:600;">
                {cat_score}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("")   # spacing between rows


# ── Learning Steps Section ────────────────────────────────────────────────────

def render_learning_steps(job_role: str) -> None:
    """
    Render the "Recommended Next Learning Steps" section.

    Displays role-specific guidance across three categories:
      - Technologies to learn next
      - Certifications worth pursuing
      - Project ideas to build and add to a portfolio

    This section is shown unconditionally — it guides growth regardless
    of the current resume score.

    Args:
        job_role: Selected job role name string.
    """
    steps = get_learning_steps(job_role)

    technologies   = steps.get("technologies", [])
    certifications = steps.get("certifications", [])
    project_ideas  = steps.get("project_ideas", [])

    st.markdown("---")
    st.header("📚 Recommended Next Learning Steps")
    st.caption(
        f"Personalised roadmap for the **{job_role}** role. "
        "These are independent of your current score — use them to plan your growth."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("🛠️ Technologies")
        for tech in technologies:
            st.markdown(f"- `{tech}`")

    with col2:
        st.subheader("🏅 Certifications")
        for cert in certifications:
            st.markdown(f"- {cert}")

    with col3:
        st.subheader("💡 Project Ideas")
        for idea in project_ideas:
            st.markdown(f"- {idea}")

    logger.debug("Rendered learning steps for role: %s", job_role)


# ── Skills Section ────────────────────────────────────────────────────────────

def render_skills_summary(skill_results: dict) -> None:
    """
    Display total detected skills and a category-breakdown count.

    Args:
        skill_results: Dictionary from extract_skills() with keys
                       "all_skills" and "by_category".
    """
    all_skills       = skill_results["all_skills"]
    by_category      = skill_results["by_category"]
    total_skills     = len(all_skills)
    total_categories = len(by_category)

    st.markdown("---")
    st.header("🔍 Detected Skills")

    col1, col2 = st.columns(2)
    col1.metric(
        label="Total Skills Detected",
        value=total_skills,
        help="Unique skills found in your resume matched against the skills database.",
    )
    col2.metric(
        label="Skill Categories",
        value=total_categories,
        help="Number of distinct skill categories represented.",
    )

    if total_skills == 0:
        st.warning(
            "⚠️ No skills were detected. "
            "Make sure your resume has a clear Skills section with standard skill names."
        )


def render_skills_by_category(by_category: dict[str, list]) -> None:
    """
    Display detected skills grouped by category as inline code badges.

    Args:
        by_category: Dict mapping category name → list of skill names.
    """
    if not by_category:
        return

    st.subheader("Skills by Category")
    for category in sorted(by_category.keys()):
        skills_in_category = by_category[category]
        badges = "  ".join([f"`{skill}`" for skill in sorted(skills_in_category)])
        st.markdown(f"**{category}** ({len(skills_in_category)})")
        st.markdown(badges)
        st.markdown("")


def render_all_skills_flat(all_skills: list[str]) -> None:
    """
    Display all detected skills as a flat alphabetical list in an expander.

    Args:
        all_skills: Flat list of matched skill name strings.
    """
    if not all_skills:
        return

    with st.expander("📋 Full Skill List (alphabetical)", expanded=False):
        st.markdown(", ".join([f"`{s}`" for s in sorted(all_skills)]))


# ── Pipeline Helpers ──────────────────────────────────────────────────────────

def _extract_text_with_spinner(uploaded_file) -> str | None:
    """
    Run extract_text() with a spinner; return text or None on failure.

    Args:
        uploaded_file: Streamlit uploaded file object.

    Returns:
        Extracted text string, or None if an error occurred.
    """
    try:
        with st.spinner("Extracting text from your resume…"):
            resume_text = extract_text(uploaded_file)
        return resume_text

    except ValueError as e:
        st.error(f"❌ Invalid file: {e}")
        logger.warning("File validation failed for %s: %s", uploaded_file.name, str(e))
        return None

    except RuntimeError as e:
        st.error(f"❌ Could not extract text: {e}")
        logger.error("Text extraction failed for %s: %s", uploaded_file.name, str(e))
        return None

    except Exception as e:
        st.error("❌ An unexpected error occurred while reading your file.")
        logger.exception("Unexpected error during text extraction: %s", str(e))
        return None


def _extract_skills_with_spinner(resume_text: str) -> dict | None:
    """
    Run extract_skills() with a spinner; return results or None on failure.

    Args:
        resume_text: Cleaned resume text string.

    Returns:
        Skill results dictionary, or None if an error occurred.
    """
    try:
        with st.spinner("Detecting skills using NLP…"):
            skill_results = extract_skills(resume_text)
        return skill_results

    except RuntimeError as e:
        st.error(f"❌ Skill extraction failed: {e}")
        logger.error("Skill extraction failed: %s", str(e))
        return None

    except Exception as e:
        st.error("❌ An unexpected error occurred during skill detection.")
        logger.exception("Unexpected error during skill extraction: %s", str(e))
        return None


def _calculate_ats_with_spinner(
    resume_text: str,
    all_skills: list[str],
    job_role: str,
) -> dict | None:
    """
    Run calculate_ats_score() with a spinner; return results or None on failure.

    Args:
        resume_text : Cleaned resume text.
        all_skills  : Flat list of detected skill names.
        job_role    : Selected job role string.

    Returns:
        ATS result dictionary, or None if an error occurred.
    """
    try:
        with st.spinner(f"Calculating ATS score for {job_role}…"):
            ats_result = calculate_ats_score(resume_text, all_skills, job_role)
        return ats_result

    except ValueError as e:
        st.error(f"❌ Invalid job role: {e}")
        logger.error("ATS scoring failed — invalid role '%s': %s", job_role, str(e))
        return None

    except Exception as e:
        st.error("❌ An unexpected error occurred during ATS scoring.")
        logger.exception("Unexpected error during ATS scoring: %s", str(e))
        return None


# ── Full Analysis Pipeline ────────────────────────────────────────────────────

def run_analysis(uploaded_file, job_role: str) -> None:
    """
    Orchestrate the complete analysis pipeline.

    Steps:
      1. Show file info banner
      2. Extract text from the uploaded file
      3. Display extracted text (collapsible)
      4. Extract skills from the text
      5. Calculate ATS score
      6. Display ATS results (score, grade, strengths, missing, suggestions, breakdown)
      7. Display job role match % and preferred skills analysis
      8. Display recommended learning steps
      9. Display skill summary and category breakdown

    Each step that can fail returns None and shows a user-friendly error,
    stopping the pipeline cleanly without a traceback.

    Args:
        uploaded_file : Streamlit uploaded file object.
        job_role      : Selected job role name string.
    """
    render_file_info(uploaded_file)
    logger.info("Starting analysis — file: %s | role: %s", uploaded_file.name, job_role)

    # Step 1 — Extract text
    resume_text = _extract_text_with_spinner(uploaded_file)
    if resume_text is None:
        return

    # Step 2 — Show extracted text
    render_extracted_text(resume_text, uploaded_file.name)

    # Step 3 — Extract skills
    skill_results = _extract_skills_with_spinner(resume_text)
    if skill_results is None:
        return

    all_skills = skill_results["all_skills"]

    # Step 4 — Calculate ATS score
    ats_result = _calculate_ats_with_spinner(resume_text, all_skills, job_role)
    if ats_result is None:
        return

    # Step 5 — Render ATS results
    render_ats_score(ats_result, job_role)

    # Step 6 — Render job role match + preferred skills
    render_job_match_section(ats_result, job_role)

    # Step 7 — Render learning steps
    render_learning_steps(job_role)

    # Step 8 — Render skill results
    render_skills_summary(skill_results)
    if skill_results["all_skills"]:
        render_skills_by_category(skill_results["by_category"])
        render_all_skills_flat(skill_results["all_skills"])

    logger.info(
        "Analysis complete — %s | role: %s | score: %d | match: %d%% | skills: %d",
        uploaded_file.name,
        job_role,
        ats_result["ats_score"],
        ats_result["match_percentage"],
        len(all_skills),
    )


# ── App Entry Point ───────────────────────────────────────────────────────────

def main() -> None:
    """
    Main function — configures the page and drives the full app flow.

    Streamlit re-runs this function on every user interaction.
    The job roles list is cached via @st.cache_data to avoid re-reading
    the JSON file on every re-run.
    """
    configure_page()
    render_sidebar()

    st.title(f"{APP_ICON} {APP_TITLE}")
    st.markdown("---")

    # Load job roles (cached after first load)
    try:
        job_roles = load_job_roles()
    except RuntimeError as e:
        st.error(f"❌ Could not load job roles: {e}")
        logger.error("Failed to load job roles: %s", str(e))
        st.stop()   # Nothing else in the app can work without job roles

    # Role selector always visible
    selected_role = render_job_role_selector(job_roles)

    st.markdown("")

    # File uploader
    uploaded_file = render_upload_section()

    if uploaded_file is not None:
        st.markdown("---")
        run_analysis(uploaded_file, selected_role)
    else:
        st.markdown("")
        st.info("👆 Upload your resume above to get started.")


if __name__ == "__main__":
    main()