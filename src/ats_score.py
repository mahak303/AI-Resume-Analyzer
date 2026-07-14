"""
ATS (Applicant Tracking System) scoring engine for the AI Resume Analyzer.

What is an ATS score?
  Most companies use software (ATS) to automatically screen resumes before a
  human ever reads them. This module simulates that process by scoring a resume
  across six weighted categories and returning a score out of 100.

How the score is calculated:
  The total score is the weighted sum of six sub-scores:

  ┌──────────────────────────┬────────┬────────────────────────────────────────┐
  │ Category                 │ Weight │ What it checks                         │
  ├──────────────────────────┼────────┼────────────────────────────────────────┤
  │ Skills Match             │  40 %  │ Required skills found in the resume    │
  │ Section Completeness     │  20 %  │ Education, Experience, Projects found  │
  │ Contact Information      │  15 %  │ Email, phone number present            │
  │ Resume Length            │  10 %  │ Word count in an acceptable range      │
  │ Keyword Density          │  10 %  │ Job-role keywords present in text      │
  │ Quantified Impact        │   5 %  │ Numbers/percentages showing results    │
  └──────────────────────────┴────────┴────────────────────────────────────────┘

  Weights are read from ATS_WEIGHTS in config.py — never hardcoded here.

Public API (the only function app.py needs to call):
  calculate_ats_score(resume_text, detected_skills, job_role) -> dict

  Returns:
    {
      "ats_score"     : int (0–100),
      "grade"         : str ("Excellent" / "Good" / "Fair" / "Needs Work"),
      "strengths"     : list[str],
      "missing_skills": list[str],
      "suggestions"   : list[str],
      "breakdown"     : dict[str, float]   ← per-category scores
    }
"""

import re
import json
import logging
from pathlib import Path

from config import (
    ATS_WEIGHTS,
    SECTION_HEADERS,
    SCORE_BANDS,
    QUANTIFICATION_PATTERNS,
    JOB_ROLES_JSON_PATH,
    MAX_MISSING_SKILLS_SHOWN,
    MAX_SUGGESTIONS_SHOWN,
)

# ── Logger ────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


# ── Load Job Roles Data ───────────────────────────────────────────────────────

def _load_job_roles() -> dict:
    """
    Load job role definitions from job_roles.json.

    Each role contains required_skills (with weights), preferred_skills,
    and a list of keywords used for keyword-density scoring.

    Returns:
        Dictionary of all job roles keyed by role name.

    Raises:
        RuntimeError: If the JSON file cannot be found or parsed.
    """
    path = Path(JOB_ROLES_JSON_PATH)

    if not path.exists():
        raise RuntimeError(
            f"job_roles.json not found at: {JOB_ROLES_JSON_PATH}. "
            "Make sure the data/ folder is present."
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Loaded %d job roles from job_roles.json", len(data["roles"]))
        return data["roles"]
    except (json.JSONDecodeError, KeyError) as e:
        raise RuntimeError(f"Failed to parse job_roles.json: {e}")


# Load once at module level — same pattern as skill_extractor.py
_JOB_ROLES: dict = _load_job_roles()


# ── Helper: Determine Score Grade ─────────────────────────────────────────────

def _get_grade(score: float) -> str:
    """
    Convert a numeric ATS score into a human-readable grade label.

    Grade bands are defined in SCORE_BANDS inside config.py:
      85–100 → Excellent
      70–84  → Good
      50–69  → Fair
       0–49  → Needs Work

    Args:
        score: Numeric ATS score between 0 and 100.

    Returns:
        Grade label string.
    """
    if score >= SCORE_BANDS["excellent"]:
        return "Excellent"
    elif score >= SCORE_BANDS["good"]:
        return "Good"
    elif score >= SCORE_BANDS["fair"]:
        return "Fair"
    else:
        return "Needs Work"


# ── Sub-scorer 1: Skills Match (40%) ──────────────────────────────────────────

def _score_skills_match(
    detected_skills: list[str],
    required_skills: dict[str, int],
    preferred_skills: dict[str, int],
) -> tuple[float, list[str], list[str]]:
    """
    Score how many of the job role's required and preferred skills are present.

    Scoring logic:
      - Required skills carry full weight (their value from job_roles.json).
      - Preferred skills carry half weight (bonus points, not penalised).
      - The raw score is normalised to 0–100 against the maximum possible score.

    Args:
        detected_skills  : Flat list of skill names found in the resume.
        required_skills  : Dict of {skill_name: weight} for required skills.
        preferred_skills : Dict of {skill_name: weight} for preferred skills.

    Returns:
        A tuple of:
          - normalised_score : float between 0.0 and 100.0
          - matched_required : list of required skill names that were found
          - missing_required : list of required skill names that were NOT found
    """
    # Normalise to lowercase sets for case-insensitive comparison
    detected_lower = {s.lower() for s in detected_skills}

    matched_required: list[str] = []
    missing_required: list[str] = []

    # Tally points earned from required skills
    earned_required = 0
    max_required    = sum(required_skills.values())

    for skill, weight in required_skills.items():
        if skill.lower() in detected_lower:
            earned_required += weight
            matched_required.append(skill)
        else:
            missing_required.append(skill)

    # Tally bonus points from preferred skills (half weight each)
    earned_preferred = 0
    max_preferred    = sum(preferred_skills.values())

    for skill, weight in preferred_skills.items():
        if skill.lower() in detected_lower:
            earned_preferred += weight * 0.5   # preferred = half credit

    # Maximum possible score = all required + all preferred at half weight
    max_total = max_required + (max_preferred * 0.5)

    if max_total == 0:
        normalised_score = 0.0
    else:
        raw_earned       = earned_required + earned_preferred
        normalised_score = min((raw_earned / max_total) * 100, 100.0)

    logger.debug(
        "Skills match: %.1f/100 | matched=%d required, missing=%d required",
        normalised_score, len(matched_required), len(missing_required),
    )
    return normalised_score, matched_required, missing_required


# ── Sub-scorer 2: Section Completeness (20%) ──────────────────────────────────

def _score_section_completeness(resume_text: str) -> tuple[float, list[str]]:
    """
    Check for the presence of key resume sections.

    Sections checked and their individual point values (out of 100):
      - Experience    : 35 points  (most important section)
      - Education     : 30 points
      - Skills        : 20 points
      - Projects      : 10 points
      - Summary       : 5  points  (nice to have)

    Detection uses the SECTION_HEADERS keyword lists from config.py.
    A section is considered present if any of its header keywords appear
    as a standalone line or at the start of a line in the resume.

    Args:
        resume_text: Cleaned resume text.

    Returns:
        A tuple of:
          - score          : float 0–100
          - found_sections : list of section names that were detected
    """
    # Points awarded per section (must sum to 100)
    section_points = {
        "experience":      35,
        "education":       30,
        "skills":          20,
        "projects":        10,
        "summary":          5,
    }

    lower_text     = resume_text.lower()
    found_sections : list[str] = []
    total_score    = 0.0

    for section_name, points in section_points.items():
        keywords = SECTION_HEADERS.get(section_name, [])

        # Check if any of the section's header keywords appear in the text
        for keyword in keywords:
            # Use word boundaries so "experienced" doesn't match "experience"
            pattern = r"(^|\n)\s*" + re.escape(keyword) + r"\s*(\n|:)"
            if re.search(pattern, lower_text):
                found_sections.append(section_name.capitalize())
                total_score += points
                break   # Found this section — no need to check more keywords

    logger.debug(
        "Section completeness: %.1f/100 | found=%s",
        total_score, found_sections,
    )
    return total_score, found_sections


# ── Sub-scorer 3: Contact Information (15%) ───────────────────────────────────

def _score_contact_info(resume_text: str) -> tuple[float, list[str]]:
    """
    Detect the presence of contact information in the resume.

    Checks for:
      - Email address  : 50 points
      - Phone number   : 30 points
      - LinkedIn URL   : 20 points

    These regex patterns are deliberately simple and cover the most common
    formats without being brittle.

    Args:
        resume_text: Cleaned resume text.

    Returns:
        A tuple of:
          - score         : float 0–100
          - found_contact : list of contact types detected
    """
    contact_checks = {
        "Email":    (r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", 50),
        "Phone":    (r"(\+?\d[\d\s\-().]{7,}\d)", 30),
        "LinkedIn": (r"linkedin\.com/in/[a-zA-Z0-9\-]+", 20),
    }

    found_contact: list[str] = []
    total_score   = 0.0

    for contact_type, (pattern, points) in contact_checks.items():
        if re.search(pattern, resume_text, re.IGNORECASE):
            found_contact.append(contact_type)
            total_score += points

    logger.debug(
        "Contact info: %.1f/100 | found=%s", total_score, found_contact
    )
    return total_score, found_contact


# ── Sub-scorer 4: Resume Length (10%) ─────────────────────────────────────────

def _score_resume_length(resume_text: str) -> tuple[float, str]:
    """
    Score the resume based on its word count.

    Ideal resume length (per industry norms):
      - 300–150  words → too short (score scales up from 0)
      - 300–700  words → ideal range → 100 points
      - 700–900  words → slightly long → 80 points
      - 900–1200 words → long → 60 points
      - > 1200   words → too long (score scales down)

    Args:
        resume_text: Cleaned resume text.

    Returns:
        A tuple of:
          - score   : float 0–100
          - message : human-readable length assessment
    """
    word_count = len(resume_text.split())

    if word_count < 150:
        score   = max(0.0, (word_count / 150) * 40)   # scales 0→40 as words grow
        message = f"Too short ({word_count} words). Aim for at least 300 words."
    elif word_count <= 700:
        score   = 100.0
        message = f"Good length ({word_count} words)."
    elif word_count <= 900:
        score   = 80.0
        message = f"Slightly long ({word_count} words). Consider trimming."
    elif word_count <= 1200:
        score   = 60.0
        message = f"Long resume ({word_count} words). Aim for under 700 words."
    else:
        score   = 40.0
        message = f"Too long ({word_count} words). Keep it to 1–2 pages."

    logger.debug("Resume length: %d words → %.1f/100 | %s", word_count, score, message)
    return score, message


# ── Sub-scorer 5: Keyword Density (10%) ───────────────────────────────────────

def _score_keyword_density(
    resume_text: str,
    role_keywords: list[str],
) -> tuple[float, int]:
    """
    Measure how many of the job role's keywords appear in the resume text.

    Keywords are defined per role in job_roles.json. Each keyword present
    contributes equally to the score. Score is normalised to 0–100.

    Args:
        resume_text  : Cleaned resume text.
        role_keywords: List of keyword strings from the selected job role.

    Returns:
        A tuple of:
          - score         : float 0–100
          - matched_count : number of keywords found
    """
    if not role_keywords:
        return 0.0, 0

    lower_text    = resume_text.lower()
    matched_count = 0

    for keyword in role_keywords:
        # Word-boundary search so "java" doesn't match inside "javascript"
        pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
        if re.search(pattern, lower_text):
            matched_count += 1

    score = (matched_count / len(role_keywords)) * 100

    logger.debug(
        "Keyword density: %d/%d keywords matched → %.1f/100",
        matched_count, len(role_keywords), score,
    )
    return score, matched_count


# ── Sub-scorer 6: Quantified Impact (5%) ──────────────────────────────────────

def _score_quantified_impact(resume_text: str) -> tuple[float, int]:
    """
    Detect the presence of quantified achievements in the resume.

    Patterns (from QUANTIFICATION_PATTERNS in config.py):
      - Percentages  : "improved efficiency by 30%"
      - Dollar values: "$50,000 revenue"
      - Multipliers  : "3x faster"
      - Scale numbers: "500+ users", "10 projects"

    Scoring:
      0 matches → 0
      1 match   → 30
      2 matches → 60
      3+ matches → 100

    Args:
        resume_text: Cleaned resume text.

    Returns:
        A tuple of:
          - score      : float 0–100
          - match_count: total number of quantification matches found
    """
    match_count = 0

    for pattern in QUANTIFICATION_PATTERNS:
        matches = re.findall(pattern, resume_text, re.IGNORECASE)
        match_count += len(matches)

    if match_count == 0:
        score = 0.0
    elif match_count == 1:
        score = 30.0
    elif match_count == 2:
        score = 60.0
    else:
        score = 100.0

    logger.debug(
        "Quantified impact: %d match(es) found → %.1f/100", match_count, score
    )
    return score, match_count


# ── Strengths Builder ─────────────────────────────────────────────────────────

def _build_strengths(
    matched_required  : list[str],
    found_sections    : list[str],
    found_contact     : list[str],
    length_message    : str,
    keyword_count     : int,
    quantify_count    : int,
) -> list[str]:
    """
    Build a list of positive strengths to show the user.

    Each strength is a plain-English sentence describing something the
    resume does well. Only genuinely passing criteria are included.

    Args:
        matched_required : Required skills found in the resume.
        found_sections   : Resume sections detected.
        found_contact    : Contact info types detected.
        length_message   : Human-readable length assessment from _score_resume_length.
        keyword_count    : Number of job keywords matched.
        quantify_count   : Number of quantified achievements found.

    Returns:
        List of strength strings.
    """
    strengths: list[str] = []

    if matched_required:
        strengths.append(
            f"Includes {len(matched_required)} required skill(s): "
            f"{', '.join(matched_required[:5])}"
            + (" and more." if len(matched_required) > 5 else ".")
        )

    for section in found_sections:
        strengths.append(f"{section} section is present.")

    if "Email" in found_contact:
        strengths.append("Email address is included.")

    if "Phone" in found_contact:
        strengths.append("Phone number is included.")

    if "LinkedIn" in found_contact:
        strengths.append("LinkedIn profile URL is included.")

    if "Good length" in length_message:
        strengths.append(length_message)

    if keyword_count >= 5:
        strengths.append(
            f"Contains {keyword_count} relevant job-role keywords."
        )

    if quantify_count >= 2:
        strengths.append(
            f"Uses {quantify_count} quantified achievement(s) — strong use of numbers."
        )

    return strengths


# ── Suggestions Builder ───────────────────────────────────────────────────────

def _build_suggestions(
    missing_required  : list[str],
    found_sections    : list[str],
    found_contact     : list[str],
    length_message    : str,
    keyword_count     : int,
    quantify_count    : int,
    total_role_keywords: int,
) -> list[str]:
    """
    Build a prioritised list of actionable improvement suggestions.

    Suggestions are ordered from highest impact (missing required skills)
    to lower impact (style/formatting improvements).

    The list is capped at MAX_SUGGESTIONS_SHOWN from config.py to avoid
    overwhelming the user.

    Args:
        missing_required    : Required skills not found in the resume.
        found_sections      : Resume sections that were detected.
        found_contact       : Contact info types detected.
        length_message      : Length assessment string.
        keyword_count       : Job keywords matched.
        quantify_count      : Quantified achievements found.
        total_role_keywords : Total keywords defined for the role.

    Returns:
        Prioritised list of suggestion strings (capped at MAX_SUGGESTIONS_SHOWN).
    """
    suggestions: list[str] = []

    # 1. Missing required skills — highest priority
    if missing_required:
        preview = missing_required[:5]
        skills_str = ", ".join(preview)
        suffix = f" (and {len(missing_required) - 5} more)" if len(missing_required) > 5 else ""
        suggestions.append(
            f"Add these missing required skills to your resume: {skills_str}{suffix}."
        )

    # 2. Missing sections
    expected_sections = {"Experience", "Education", "Skills", "Projects"}
    for section in expected_sections:
        if section not in found_sections:
            suggestions.append(
                f"Add a '{section}' section — ATS systems specifically look for this."
            )

    # 3. Missing contact information
    if "Email" not in found_contact:
        suggestions.append("Add a professional email address to your resume.")

    if "Phone" not in found_contact:
        suggestions.append("Add a phone number to your contact information.")

    if "LinkedIn" not in found_contact:
        suggestions.append(
            "Add your LinkedIn profile URL (linkedin.com/in/yourname)."
        )

    # 4. Resume length
    if "Too short" in length_message or "Too long" in length_message or "Long" in length_message:
        suggestions.append(length_message)

    # 5. Low keyword density
    if total_role_keywords > 0 and keyword_count < (total_role_keywords * 0.4):
        suggestions.append(
            "Use more role-specific keywords from the job description "
            "to improve ATS keyword matching."
        )

    # 6. No quantified achievements
    if quantify_count == 0:
        suggestions.append(
            "Add measurable achievements to your bullet points "
            "(e.g. 'Improved performance by 30%', 'Built a system serving 500+ users')."
        )

    # Return only the top N suggestions to avoid overwhelming the user
    return suggestions[:MAX_SUGGESTIONS_SHOWN]


# ── Public API ────────────────────────────────────────────────────────────────

def calculate_ats_score(
    resume_text    : str,
    detected_skills: list[str],
    job_role       : str,
) -> dict:
    """
    Calculate a comprehensive ATS score for a resume against a target job role.

    This is the only function that app.py needs to import and call.

    The total score is the weighted sum of six sub-scores, using weights
    from ATS_WEIGHTS in config.py. All sub-scores are on a 0–100 scale
    before weighting.

    Args:
        resume_text    : Cleaned resume text from pdf_parser.extract_text().
        detected_skills: Flat list of skills from skill_extractor.get_all_skills().
        job_role       : Job role name string, e.g. "Python Developer".
                         Must match a key in job_roles.json.

    Returns:
        A dictionary with the following keys:

        "ats_score"      (int)        : Final score 0–100.
        "grade"          (str)        : "Excellent" / "Good" / "Fair" / "Needs Work".
        "strengths"      (list[str])  : Things the resume does well.
        "missing_skills" (list[str])  : Required skills not found (capped at config limit).
        "suggestions"    (list[str])  : Prioritised improvement actions.
        "breakdown"      (dict)       : Per-category scores for charting.

    Raises:
        ValueError : If the job_role is not found in job_roles.json.
        RuntimeError: If job_roles.json cannot be loaded.
    """
    logger.info("Calculating ATS score for role: '%s'", job_role)

    # ── Validate job role ──────────────────────────────────────────────────
    if job_role not in _JOB_ROLES:
        available = ", ".join(_JOB_ROLES.keys())
        raise ValueError(
            f"Job role '{job_role}' not found. "
            f"Available roles: {available}"
        )

    role_data        = _JOB_ROLES[job_role]
    required_skills  = role_data.get("required_skills", {})
    preferred_skills = role_data.get("preferred_skills", {})
    role_keywords    = role_data.get("keywords", [])

    # ── Run all six sub-scorers ────────────────────────────────────────────

    skills_score, matched_required, missing_required = _score_skills_match(
        detected_skills, required_skills, preferred_skills
    )

    section_score, found_sections = _score_section_completeness(resume_text)

    contact_score, found_contact = _score_contact_info(resume_text)

    length_score, length_message = _score_resume_length(resume_text)

    keyword_score, keyword_count = _score_keyword_density(resume_text, role_keywords)

    quantify_score, quantify_count = _score_quantified_impact(resume_text)

    # ── Compute weighted total ─────────────────────────────────────────────
    # Weights from ATS_WEIGHTS in config.py.
    # We map each sub-score to its config key explicitly so the connection
    # between config and code is transparent and easy to audit.

    weighted_scores = {
        "skills_match"        : skills_score   * ATS_WEIGHTS["skills_match"],
        "section_completeness": section_score  * ATS_WEIGHTS["section_completeness"],
        "contact_info"        : contact_score  * ATS_WEIGHTS["contact_info"],
        "resume_length"       : length_score   * ATS_WEIGHTS["resume_length"],
        "keyword_density"     : keyword_score  * ATS_WEIGHTS["keyword_density"],
        "quantified_impact"   : quantify_score * ATS_WEIGHTS["quantified_impact"],
    }

    # Sum all weighted contributions and clamp to [0, 100]
    raw_total = sum(weighted_scores.values())
    ats_score = int(min(max(round(raw_total), 0), 100))

    # ── Build breakdown dict for charts (unweighted, 0–100 per category) ──
    breakdown = {
        "Skills Match"        : round(skills_score,    1),
        "Section Completeness": round(section_score,   1),
        "Contact Info"        : round(contact_score,   1),
        "Resume Length"       : round(length_score,    1),
        "Keyword Density"     : round(keyword_score,   1),
        "Quantified Impact"   : round(quantify_score,  1),
    }

    # ── Build human-readable outputs ───────────────────────────────────────
    strengths = _build_strengths(
        matched_required  = matched_required,
        found_sections    = found_sections,
        found_contact     = found_contact,
        length_message    = length_message,
        keyword_count     = keyword_count,
        quantify_count    = quantify_count,
    )

    suggestions = _build_suggestions(
        missing_required     = missing_required,
        found_sections       = found_sections,
        found_contact        = found_contact,
        length_message       = length_message,
        keyword_count        = keyword_count,
        quantify_count       = quantify_count,
        total_role_keywords  = len(role_keywords),
    )

    # Cap missing_skills list so the UI is not overwhelmed
    capped_missing = missing_required[:MAX_MISSING_SKILLS_SHOWN]

    logger.info(
        "ATS score for '%s': %d/100 (%s) | strengths=%d | missing=%d | suggestions=%d",
        job_role, ats_score, _get_grade(ats_score),
        len(strengths), len(capped_missing), len(suggestions),
    )

    return {
        "ats_score"      : ats_score,
        "grade"          : _get_grade(ats_score),
        "strengths"      : strengths,
        "missing_skills" : capped_missing,
        "suggestions"    : suggestions,
        "breakdown"      : breakdown,
    }