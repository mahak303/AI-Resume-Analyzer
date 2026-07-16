



import json
import logging

import plotly.graph_objects as go
import streamlit as st

from config import (
    ALLOWED_FILE_TYPES,
    APP_DESCRIPTION,
    APP_ICON,
    APP_TITLE,
    JOB_ROLES_JSON_PATH,
    MAX_FILE_SIZE_MB,
    PAGE_LAYOUT,
    SCORE_BANDS,
    SCORE_COLORS,
    SIDEBAR_STATE,
)
from src.ats_engine import calculate_ats_score
from src.pdf_parser import extract_text, get_file_info
from src.skill_extractor import extract_skills, get_all_skills
from src.suggestions import get_learning_steps

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Global CSS ────────────────────────────────────────────────────────────────

def inject_css() -> None:
    """
    Inject custom CSS for typography, spacing, cards, and badges.

    All colours reference the SCORE_COLORS palette from config.py.
    This keeps the design system consistent — one place to change colours.
    """
    st.markdown(
        """
        <style>
        /* ── Typography ─────────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* ── Section headings ──────────────────────────────── */
        .section-heading {
            font-size: 1.3rem;
            font-weight: 700;
            color: #1a1a2e;
            margin: 0 0 0.2rem 0;
            padding-bottom: 0.4rem;
            border-bottom: 2px solid #e8eaf6;
        }

        /* ── Score card ────────────────────────────────────── */
        .score-card {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 16px;
            padding: 2rem;
            text-align: center;
            box-shadow: 0 8px 32px rgba(26,26,46,0.18);
        }
        .score-number {
            font-size: 4rem;
            font-weight: 800;
            line-height: 1;
            margin: 0;
        }
        .score-label {
            font-size: 0.85rem;
            color: #a0aec0;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-top: 0.3rem;
        }
        .grade-badge {
            display: inline-block;
            padding: 0.35rem 1.1rem;
            border-radius: 999px;
            font-size: 0.95rem;
            font-weight: 700;
            margin-top: 0.8rem;
            letter-spacing: 0.04em;
        }

        /* ── Metric cards ──────────────────────────────────── */
        .metric-card {
            background: #f8f9ff;
            border: 1px solid #e8eaf6;
            border-radius: 12px;
            padding: 1rem 1.2rem;
            text-align: center;
        }
        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #1a1a2e;
            line-height: 1.1;
        }
        .metric-label {
            font-size: 0.75rem;
            color: #718096;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-top: 0.2rem;
        }

        /* ── Strength / weakness / suggestion boxes ─────────── */
        .strength-box {
            background: #f0fdf4;
            border-left: 4px solid #2ecc71;
            border-radius: 0 10px 10px 0;
            padding: 1rem 1.2rem;
            margin-bottom: 0.5rem;
        }
        .missing-box {
            background: #fff5f5;
            border-left: 4px solid #e74c3c;
            border-radius: 0 10px 10px 0;
            padding: 1rem 1.2rem;
            margin-bottom: 0.5rem;
        }
        .suggestion-box {
            background: #eff6ff;
            border-left: 4px solid #3b82f6;
            border-radius: 0 10px 10px 0;
            padding: 1rem 1.2rem;
            margin-bottom: 0.5rem;
        }

        /* ── Skill badges ──────────────────────────────────── */
        .badge-wrap {
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
            margin-top: 0.3rem;
        }
        .badge {
            background: #e8eaf6;
            color: #3730a3;
            border-radius: 999px;
            padding: 0.25rem 0.75rem;
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            white-space: nowrap;
        }
        .badge-green  { background: #d1fae5; color: #065f46; }
        .badge-red    { background: #fee2e2; color: #991b1b; }
        .badge-blue   { background: #dbeafe; color: #1e40af; }

        /* ── Progress bar ──────────────────────────────────── */
        .progress-row {
            margin-bottom: 0.65rem;
        }
        .progress-label-row {
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            font-weight: 600;
            color: #374151;
            margin-bottom: 0.2rem;
        }
        .progress-track {
            background: #e5e7eb;
            border-radius: 999px;
            height: 10px;
            width: 100%;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            border-radius: 999px;
            transition: width 0.4s ease;
        }

        /* ── Section divider ───────────────────────────────── */
        .section-divider {
            height: 2px;
            background: linear-gradient(90deg, #e8eaf6 0%, transparent 100%);
            margin: 2rem 0 1.5rem 0;
            border: none;
        }

        /* ── Learning step cards ────────────────────────────── */
        .learn-card {
            background: #f8f9ff;
            border: 1px solid #e8eaf6;
            border-radius: 12px;
            padding: 1.2rem;
            height: 100%;
        }
        .learn-card-title {
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #6366f1;
            margin-bottom: 0.7rem;
        }
        .learn-item {
            font-size: 0.85rem;
            color: #374151;
            padding: 0.3rem 0;
            border-bottom: 1px solid #f0f0f0;
            line-height: 1.4;
        }
        .learn-item:last-child { border-bottom: none; }

        /* ── Footer ────────────────────────────────────────── */
        .footer {
            margin-top: 3rem;
            padding: 1.5rem;
            background: #1a1a2e;
            border-radius: 12px;
            text-align: center;
            color: #a0aec0;
            font-size: 0.82rem;
            line-height: 1.8;
        }
        .footer strong { color: #e2e8f0; }

        /* ── Hide default Streamlit elements ────────────────── */
        #MainMenu { visibility: hidden; }
        footer    { visibility: hidden; }

        /* ── Tighten main column padding on desktop ─────────── */
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 1rem;
            max-width: 1100px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_score_color(score: int) -> str:
    """Return hex colour for a score value using SCORE_COLORS from config."""
    if score >= SCORE_BANDS["excellent"]:
        return SCORE_COLORS["excellent"]
    elif score >= SCORE_BANDS["good"]:
        return SCORE_COLORS["good"]
    elif score >= SCORE_BANDS["fair"]:
        return SCORE_COLORS["fair"]
    else:
        return SCORE_COLORS["poor"]


def _badge_html(skills: list[str], style: str = "") -> str:
    """
    Render a list of skill names as HTML badge chips.

    Args:
        skills : List of skill name strings.
        style  : Optional extra CSS class name (badge-green, badge-red, badge-blue).

    Returns:
        HTML string with wrapped badge divs.
    """
    cls = f"badge {style}".strip()
    chips = "".join(f'<span class="{cls}">{s}</span>' for s in sorted(skills))
    return f'<div class="badge-wrap">{chips}</div>'


def _progress_bar_html(label: str, value: float, color: str) -> str:
    """
    Render a single labelled progress bar in HTML.

    Args:
        label : Category name shown above the bar.
        value : Score 0–100, controls bar width.
        color : Hex fill colour.

    Returns:
        HTML string for the complete progress row.
    """
    return f"""
    <div class="progress-row">
      <div class="progress-label-row">
        <span>{label}</span>
        <span style="color:{color}; font-weight:700;">{value}/100</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" style="width:{value}%; background:{color};"></div>
      </div>
    </div>
    """


# ── Data Loader ───────────────────────────────────────────────────────────────

@st.cache_data
def load_job_roles() -> list[str]:
    """
    Load job role names from job_roles.json, cached after first read.

    Returns:
        Sorted list of role name strings.
    """
    try:
        with open(JOB_ROLES_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        roles = sorted(data["roles"].keys())
        logger.info("Loaded %d job roles", len(roles))
        return roles
    except FileNotFoundError:
        raise RuntimeError("job_roles.json not found.")
    except (json.JSONDecodeError, KeyError) as e:
        raise RuntimeError(f"Could not read job roles: {e}")


# ── Page Config ───────────────────────────────────────────────────────────────

def configure_page() -> None:
    """Configure Streamlit page — must be the first st call."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout=PAGE_LAYOUT,
        initial_sidebar_state=SIDEBAR_STATE,
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar() -> None:
    """Render the sidebar with branding, instructions, and score guide."""
    with st.sidebar:
        # Branding
        st.markdown(
            f"""
            <div style="text-align:center; padding: 0.5rem 0 1rem 0;">
              <div style="font-size:2.5rem;">{APP_ICON}</div>
              <div style="font-size:1.1rem; font-weight:700;
                          color:#1a1a2e; margin-top:0.3rem;">{APP_TITLE}</div>
              <div style="font-size:0.75rem; color:#718096; margin-top:0.2rem;">
                Powered by Python &amp; spaCy
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # How to use
        st.markdown("**📋 How to use**")
        steps = [
            "Select your target job role",
            "Upload your resume (PDF or DOCX)",
            "Review your ATS score and feedback",
            "Follow the learning roadmap",
        ]
        for i, step in enumerate(steps, 1):
            st.markdown(
                f"<div style='font-size:0.83rem; padding:0.25rem 0; color:#374151;'>"
                f"<b style='color:#6366f1;'>{i}.</b> {step}</div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # File info
        st.markdown("**📁 Supported Formats**")
        for fmt in ALLOWED_FILE_TYPES:
            st.markdown(
                f"<span style='background:#e8eaf6; color:#3730a3; padding:0.2rem 0.6rem;"
                f"border-radius:6px; font-size:0.8rem; font-weight:600;'>.{fmt.upper()}</span>",
                unsafe_allow_html=True,
            )
        st.markdown(
            f"<div style='font-size:0.8rem; color:#718096; margin-top:0.4rem;'>"
            f"Max size: <b>{MAX_FILE_SIZE_MB} MB</b></div>",
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # ATS score guide
        st.markdown("**🏅 ATS Score Guide**")
        guide = [
            ("🟢", "85–100", "Excellent",   SCORE_COLORS["excellent"]),
            ("🟡", "70–84",  "Good",         SCORE_COLORS["good"]),
            ("🟠", "50–69",  "Fair",         SCORE_COLORS["fair"]),
            ("🔴", "0–49",   "Needs Work",   SCORE_COLORS["poor"]),
        ]
        for emoji, band, label, color in guide:
            st.markdown(
                f"<div style='display:flex; align-items:center; gap:0.5rem;"
                f"font-size:0.82rem; padding:0.2rem 0;'>"
                f"{emoji} <b style='color:{color};'>{band}</b> — {label}</div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.caption("© 2025 Mahak Keswani · AI Resume Analyzer")


# ── Header ────────────────────────────────────────────────────────────────────

def render_header() -> None:
    """Render the main page title and subtitle."""
    st.markdown(
        f"""
        <div style="margin-bottom: 1.5rem;">
          <h1 style="font-size:2rem; font-weight:800; color:#1a1a2e; margin:0;">
            {APP_ICON} {APP_TITLE}
          </h1>
          <p style="color:#718096; margin:0.3rem 0 0 0; font-size:0.95rem;">
            {APP_DESCRIPTION}
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Input Section ─────────────────────────────────────────────────────────────

def render_inputs(job_roles: list[str]) -> tuple[str, object]:
    """
    Render job role selector and file uploader side by side.

    Args:
        job_roles: List of available role name strings.

    Returns:
        Tuple of (selected_role, uploaded_file).
    """
    col_role, col_upload = st.columns([1, 1], gap="large")

    with col_role:
        st.markdown(
            '<p class="section-heading">🎯 Target Job Role</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='font-size:0.83rem; color:#718096; margin-bottom:0.5rem;'>"
            "Your resume will be scored against this role's requirements.</p>",
            unsafe_allow_html=True,
        )
        selected_role = st.selectbox(
            label="job_role",
            options=job_roles,
            index=0,
            label_visibility="collapsed",
            help="Choose the role you are applying for.",
        )

    with col_upload:
        st.markdown(
            '<p class="section-heading">📂 Upload Resume</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='font-size:0.83rem; color:#718096; margin-bottom:0.5rem;'>"
            f"PDF or DOCX · Max {MAX_FILE_SIZE_MB} MB</p>",
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader(
            label="resume_upload",
            type=ALLOWED_FILE_TYPES,
            label_visibility="collapsed",
            help=f"Supported: {', '.join(f'.{t.upper()}' for t in ALLOWED_FILE_TYPES)}",
        )

    logger.debug("Selected role: %s | File: %s", selected_role,
                 uploaded_file.name if uploaded_file else "None")
    return selected_role, uploaded_file


# ── File Info Banner ──────────────────────────────────────────────────────────

def render_file_info(uploaded_file) -> None:
    """Show a compact success banner with file metadata."""
    info = get_file_info(uploaded_file)
    st.success(
        f"✅ **{info['name']}** · {info['extension']} · {info['size_mb']} MB"
    )


# ── Extracted Text ────────────────────────────────────────────────────────────

def render_extracted_text(resume_text: str, file_name: str) -> None:
    """
    Show extracted resume text in a collapsible expander with word/char counts.

    Args:
        resume_text : Cleaned text from the resume.
        file_name   : Filename shown in the expander header.
    """
    with st.expander(f"📄 Extracted text — `{file_name}`", expanded=False):
        c1, c2 = st.columns(2)
        c1.metric("Characters", f"{len(resume_text):,}")
        c2.metric("Words",      f"{len(resume_text.split()):,}")
        st.text_area(
            label="raw",
            value=resume_text,
            height=260,
            disabled=True,
            label_visibility="collapsed",
        )


# ── ATS Score Section ─────────────────────────────────────────────────────────

def render_ats_score(ats_result: dict, job_role: str) -> None:
    """
    Render the ATS score card, grade badge, strengths, missing skills,
    suggestions, and score breakdown with progress bars.

    Args:
        ats_result : Full dictionary from calculate_ats_score().
        job_role   : Selected role name for the section heading.
    """
    score       = ats_result["ats_score"]
    grade       = ats_result["grade"]
    strengths   = ats_result["strengths"]
    missing     = ats_result["missing_skills"]
    suggestions = ats_result["suggestions"]
    breakdown   = ats_result["breakdown"]
    color       = _get_score_color(score)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown(
        f'<p class="section-heading">📊 ATS Analysis — {job_role}</p>',
        unsafe_allow_html=True,
    )

    # ── Score card + breakdown side by side ───────────────────────────────
    col_card, col_breakdown = st.columns([1, 2], gap="large")

    with col_card:
        st.markdown(
            f"""
            <div class="score-card">
              <div class="score-number" style="color:{color};">{score}</div>
              <div class="score-label">ATS Score / 100</div>
              <span class="grade-badge"
                style="background:{color}22; color:{color}; border:1.5px solid {color};">
                {grade}
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Match percentage below the card
        match_pct   = ats_result["match_percentage"]
        match_color = _get_score_color(match_pct)
        st.markdown(
            f"""
            <div class="metric-card" style="margin-top:0.75rem;">
              <div class="metric-value" style="color:{match_color};">{match_pct}%</div>
              <div class="metric-label">Role Match</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_breakdown:
        st.markdown(
            "<p style='font-size:0.85rem; font-weight:600; color:#374151;"
            "margin-bottom:0.6rem;'>Score Breakdown</p>",
            unsafe_allow_html=True,
        )
        bars_html = ""
        for category, cat_score in breakdown.items():
            bars_html += _progress_bar_html(category, cat_score, _get_score_color(cat_score))
        st.markdown(bars_html, unsafe_allow_html=True)

    st.markdown("")

    # ── Strengths, Missing Skills, Suggestions in a clean 3-col row ──────
    col_str, col_miss, col_sug = st.columns(3, gap="medium")

    with col_str:
        st.markdown(
            "<p style='font-size:0.85rem; font-weight:700; color:#065f46;"
            "margin-bottom:0.5rem;'>✅ Strengths</p>",
            unsafe_allow_html=True,
        )
        if strengths:
            for item in strengths:
                st.markdown(
                    f'<div class="strength-box" style="font-size:0.82rem;">'
                    f'{item}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No strengths detected yet.")

    with col_miss:
        st.markdown(
            "<p style='font-size:0.85rem; font-weight:700; color:#991b1b;"
            "margin-bottom:0.5rem;'>❌ Missing Skills</p>",
            unsafe_allow_html=True,
        )
        if missing:
            st.markdown(_badge_html(missing, "badge-red"), unsafe_allow_html=True)
            st.markdown(
                f"<p style='font-size:0.75rem; color:#718096; margin-top:0.5rem;'>"
                f"{len(missing)} required skill(s) not found.</p>",
                unsafe_allow_html=True,
            )
        else:
            st.success("All required skills found! 🎉")

    with col_sug:
        st.markdown(
            "<p style='font-size:0.85rem; font-weight:700; color:#1e40af;"
            "margin-bottom:0.5rem;'>💡 Suggestions</p>",
            unsafe_allow_html=True,
        )
        if suggestions:
            for i, sug in enumerate(suggestions, 1):
                st.markdown(
                    f'<div class="suggestion-box" style="font-size:0.82rem;">'
                    f'<b>{i}.</b> {sug}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.success("Resume looks well-optimised! 🎉")

    # ── Bar chart for breakdown ────────────────────────────────────────────
    st.markdown("")
    _render_breakdown_chart(breakdown)


def _render_breakdown_chart(breakdown: dict) -> None:
    """
    Render a horizontal Plotly bar chart for the ATS score breakdown.

    Args:
        breakdown: Dict mapping category name → score float.
    """
    categories = list(breakdown.keys())
    values     = list(breakdown.values())
    colors     = [_get_score_color(v) for v in values]

    fig = go.Figure(go.Bar(
        x=values,
        y=categories,
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"{v}/100" for v in values],
        textposition="outside",
        textfont=dict(size=11, color="#374151"),
        hovertemplate="%{y}: <b>%{x}/100</b><extra></extra>",
    ))

    fig.update_layout(
        margin=dict(l=0, r=60, t=10, b=10),
        xaxis=dict(range=[0, 115], showgrid=False, zeroline=False,
                   showticklabels=False),
        yaxis=dict(showgrid=False, tickfont=dict(size=12, color="#374151")),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=260,
        showlegend=False,
    )

    with st.expander("📊 Score Breakdown Chart", expanded=True):
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Job Role Match Section ────────────────────────────────────────────────────

def render_job_match_section(ats_result: dict, job_role: str) -> None:
    """
    Render role match %, skill summary metrics, preferred skills analysis,
    and required skills detail.

    Args:
        ats_result : Full result dict from calculate_ats_score().
        job_role   : Selected role name.
    """
    match_pct         = ats_result["match_percentage"]
    matched_required  = ats_result["matched_required"]
    missing_required  = ats_result["missing_required"]
    matched_preferred = ats_result["matched_preferred"]
    missing_preferred = ats_result["missing_preferred"]
    total_required    = ats_result["total_required"]
    total_preferred   = ats_result["total_preferred"]
    match_color       = _get_score_color(match_pct)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown(
        f'<p class="section-heading">🎯 Role Match — {job_role}</p>',
        unsafe_allow_html=True,
    )

    # ── 4 metric cards ────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4, gap="medium")

    cards = [
        (f"{len(matched_required)}/{total_required}", "Required Matched",  SCORE_COLORS["excellent"]),
        (str(len(missing_required)),                   "Required Missing",  SCORE_COLORS["poor"]),
        (f"{len(matched_preferred)}/{total_preferred}", "Preferred Matched", SCORE_COLORS["good"]),
        (str(len(missing_preferred)),                  "Preferred Missing", "#718096"),
    ]
    for col, (val, lbl, clr) in zip([m1, m2, m3, m4], cards):
        col.markdown(
            f"""
            <div class="metric-card">
              <div class="metric-value" style="color:{clr};">{val}</div>
              <div class="metric-label">{lbl}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("")

    # ── Preferred skills two-column layout ────────────────────────────────
    pref_found_col, pref_miss_col = st.columns(2, gap="large")

    with pref_found_col:
        st.markdown(
            "<p style='font-size:0.83rem; font-weight:700; color:#065f46;"
            "margin-bottom:0.4rem;'>✓ Preferred Skills Found</p>",
            unsafe_allow_html=True,
        )
        if matched_preferred:
            st.markdown(_badge_html(matched_preferred, "badge-green"),
                        unsafe_allow_html=True)
        else:
            st.caption("No preferred skills detected.")

    with pref_miss_col:
        st.markdown(
            "<p style='font-size:0.83rem; font-weight:700; color:#991b1b;"
            "margin-bottom:0.4rem;'>✗ Preferred Skills Missing</p>",
            unsafe_allow_html=True,
        )
        if missing_preferred:
            st.markdown(_badge_html(missing_preferred, "badge-red"),
                        unsafe_allow_html=True)
        else:
            st.success("All preferred skills present!")

    # ── Required skills detail (collapsible) ──────────────────────────────
    with st.expander("📋 Required Skills Detail", expanded=False):
        req_f, req_m = st.columns(2, gap="large")
        with req_f:
            st.markdown("**✓ Found**")
            if matched_required:
                st.markdown(_badge_html(matched_required, "badge-green"),
                            unsafe_allow_html=True)
            else:
                st.warning("No required skills found.")
        with req_m:
            st.markdown("**✗ Missing**")
            if missing_required:
                st.markdown(_badge_html(missing_required, "badge-red"),
                            unsafe_allow_html=True)
            else:
                st.success("All required skills present!")

    logger.debug("Job match rendered — %d%% | req: %d/%d | pref: %d/%d",
                 match_pct, len(matched_required), total_required,
                 len(matched_preferred), total_preferred)


# ── Detected Skills Section ───────────────────────────────────────────────────

def render_skills_section(skill_results: dict) -> None:
    """
    Render total skill counts, a pie chart by category,
    and skill badges grouped by category.

    Args:
        skill_results: Dict with keys "all_skills" and "by_category".
    """
    all_skills   = skill_results["all_skills"]
    by_category  = skill_results["by_category"]
    total        = len(all_skills)
    n_categories = len(by_category)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-heading">🔍 Detected Skills</p>',
        unsafe_allow_html=True,
    )

    if total == 0:
        st.warning(
            "⚠️ No skills detected. Add a clear Skills section "
            "with standard skill names to your resume."
        )
        return

    # ── Summary metrics ───────────────────────────────────────────────────
    mc1, mc2 = st.columns(2)
    mc1.markdown(
        f'<div class="metric-card"><div class="metric-value">{total}</div>'
        f'<div class="metric-label">Skills Detected</div></div>',
        unsafe_allow_html=True,
    )
    mc2.markdown(
        f'<div class="metric-card"><div class="metric-value">{n_categories}</div>'
        f'<div class="metric-label">Categories</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("")

    # ── Pie chart + category badges side by side ──────────────────────────
    chart_col, badges_col = st.columns([1, 2], gap="large")

    with chart_col:
        _render_skills_pie(by_category)

    with badges_col:
        st.markdown(
            "<p style='font-size:0.85rem; font-weight:600; color:#374151;"
            "margin-bottom:0.6rem;'>Skills by Category</p>",
            unsafe_allow_html=True,
        )
        for category in sorted(by_category.keys()):
            skills_in_cat = by_category[category]
            st.markdown(
                f"<p style='font-size:0.78rem; font-weight:700; color:#6366f1;"
                f"margin: 0.6rem 0 0.2rem 0; text-transform:uppercase;"
                f"letter-spacing:0.06em;'>{category} ({len(skills_in_cat)})</p>",
                unsafe_allow_html=True,
            )
            st.markdown(_badge_html(skills_in_cat, ""), unsafe_allow_html=True)

    # ── Full flat list ────────────────────────────────────────────────────
    with st.expander("📋 All detected skills (A–Z)", expanded=False):
        st.markdown(_badge_html(all_skills, "badge-blue"), unsafe_allow_html=True)


def _render_skills_pie(by_category: dict) -> None:
    """
    Render a Plotly donut chart showing skill distribution by category.

    Args:
        by_category: Dict mapping category → list of skill names.
    """
    labels = list(by_category.keys())
    values = [len(v) for v in by_category.values()]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.5,
        textinfo="percent",
        textfont=dict(size=11),
        hovertemplate="%{label}: <b>%{value} skills</b><extra></extra>",
        marker=dict(line=dict(color="white", width=2)),
    ))

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        height=240,
        annotations=[dict(
            text=f"<b>{sum(values)}</b><br>skills",
            x=0.5, y=0.5,
            font=dict(size=14, color="#1a1a2e"),
            showarrow=False,
        )],
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Learning Steps Section ────────────────────────────────────────────────────

def render_learning_steps(job_role: str) -> None:
    """
    Render the personalised "Next Learning Steps" section.

    Displays technologies, certifications, and project ideas
    for the selected role in styled cards.

    Args:
        job_role: Selected job role name.
    """
    steps          = get_learning_steps(job_role)
    technologies   = steps.get("technologies", [])
    certifications = steps.get("certifications", [])
    project_ideas  = steps.get("project_ideas", [])

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-heading">📚 Recommended Next Learning Steps</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='font-size:0.83rem; color:#718096; margin-bottom:1rem;'>"
        f"Personalised roadmap for the <b>{job_role}</b> role. "
        f"Independent of your current score — use this to plan your growth.</p>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3, gap="medium")

    def _card(col, icon: str, title: str, items: list[str]) -> None:
        items_html = "".join(
            f'<div class="learn-item">{icon_bullet} {item}</div>'
            for icon_bullet, item in [("→", i) for i in items]
        )
        col.markdown(
            f"""
            <div class="learn-card">
              <div class="learn-card-title">{icon} {title}</div>
              {items_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    _card(col1, "🛠️", "Technologies",   technologies)
    _card(col2, "🏅", "Certifications", certifications)
    _card(col3, "💡", "Project Ideas",  project_ideas)

    logger.debug("Rendered learning steps for: %s", job_role)


# ── Footer ────────────────────────────────────────────────────────────────────

def render_footer() -> None:
    """Render the professional footer with author and tech stack info."""
    st.markdown(
        """
        <div class="footer">
          <div><strong>Developed by Mahak Keswani</strong></div>
          <div style="margin:0.2rem 0; font-size:0.9rem; color:#e2e8f0;">
            AI Resume Analyzer
          </div>
          <div>Built using Python &nbsp;•&nbsp; Streamlit &nbsp;•&nbsp; spaCy</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Pipeline Helpers ──────────────────────────────────────────────────────────

def _extract_text_with_spinner(uploaded_file) -> str | None:
    """Run extract_text() with a spinner. Returns text or None on failure."""
    try:
        with st.spinner("Extracting resume text…"):
            return extract_text(uploaded_file)
    except ValueError as e:
        st.error(f"❌ Invalid file: {e}")
        logger.warning("Validation failed for %s: %s", uploaded_file.name, e)
    except RuntimeError as e:
        st.error(f"❌ Could not extract text: {e}")
        logger.error("Extraction failed for %s: %s", uploaded_file.name, e)
    except Exception as e:
        st.error("❌ Unexpected error reading your file.")
        logger.exception("Unexpected extraction error: %s", e)
    return None


def _extract_skills_with_spinner(resume_text: str) -> dict | None:
    """Run extract_skills() with a spinner. Returns dict or None on failure."""
    try:
        with st.spinner("Detecting skills with NLP…"):
            return extract_skills(resume_text)
    except RuntimeError as e:
        st.error(f"❌ Skill extraction failed: {e}")
        logger.error("Skill extraction error: %s", e)
    except Exception as e:
        st.error("❌ Unexpected error during skill detection.")
        logger.exception("Unexpected skill extraction error: %s", e)
    return None


def _calculate_ats_with_spinner(
    resume_text: str,
    all_skills: list[str],
    job_role: str,
) -> dict | None:
    """Run calculate_ats_score() with a spinner. Returns dict or None on failure."""
    try:
        with st.spinner(f"Scoring against {job_role}…"):
            return calculate_ats_score(resume_text, all_skills, job_role)
    except ValueError as e:
        st.error(f"❌ Invalid job role: {e}")
        logger.error("ATS scoring error for role '%s': %s", job_role, e)
    except Exception as e:
        st.error("❌ Unexpected error during ATS scoring.")
        logger.exception("Unexpected ATS scoring error: %s", e)
    return None


# ── Full Analysis Pipeline ────────────────────────────────────────────────────

def run_analysis(uploaded_file, job_role: str) -> None:
    """
    Orchestrate the complete analysis pipeline and render all results.

    Steps:
      1.  File info banner
      2.  Extract + display text
      3.  Extract skills
      4.  Calculate ATS score
      5.  Render ATS score card, breakdown, strengths, missing, suggestions
      6.  Render role match % and preferred skills
      7.  Render detected skills + charts
      8.  Render learning steps
      9.  Footer

    Args:
        uploaded_file : Streamlit uploaded file object.
        job_role      : Selected job role name string.
    """
    render_file_info(uploaded_file)
    logger.info("Analysis start — %s | %s", uploaded_file.name, job_role)

    resume_text = _extract_text_with_spinner(uploaded_file)
    if resume_text is None:
        return

    render_extracted_text(resume_text, uploaded_file.name)

    skill_results = _extract_skills_with_spinner(resume_text)
    if skill_results is None:
        return

    all_skills = get_all_skills(resume_text)

    ats_result = _calculate_ats_with_spinner(resume_text, all_skills, job_role)
    if ats_result is None:
        return

    render_ats_score(ats_result, job_role)
    render_job_match_section(ats_result, job_role)
    render_skills_section(skill_results)
    render_learning_steps(job_role)
    render_footer()

    logger.info(
        "Analysis done — %s | role: %s | score: %d | match: %d%% | skills: %d",
        uploaded_file.name, job_role,
        ats_result["ats_score"], ats_result["match_percentage"], len(all_skills),
    )


# ── App Entry Point ───────────────────────────────────────────────────────────

def main() -> None:
    """
    Configure the page, inject CSS, render the header and inputs,
    then run the full analysis pipeline when a file is uploaded.
    """
    configure_page()
    inject_css()
    render_sidebar()
    render_header()

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    try:
        job_roles = load_job_roles()
    except RuntimeError as e:
        st.error(f"❌ Could not load job roles: {e}")
        logger.error("Failed to load job roles: %s", e)
        st.stop()

    selected_role, uploaded_file = render_inputs(job_roles)

    if uploaded_file is not None:
        st.markdown("")
        run_analysis(uploaded_file, selected_role)
    else:
        st.markdown("")
        st.info("👆 Upload your resume above to begin the analysis.")
        render_footer()


if __name__ == "__main__":
    main()