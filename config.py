"""
config.py
─────────
Central configuration for AI Resume Analyzer.
All constants, weights, thresholds, and file paths live here.
Import this module anywhere you need a setting — never hardcode values.

Stack: Python, Streamlit, spaCy (basic tokenization + lemmatization only).
spaCy is used only for text preprocessing before skill matching.
Skill matching itself is done against skills.csv using string comparison.
"""

import os

# ── spaCy Settings ───────────────────────────────────────────────────────────
# Small English model — handles tokenization and lemmatization well
# Download with: python -m spacy download en_core_web_sm
SPACY_MODEL = "en_core_web_sm"


# ── Project Paths ─────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

SKILLS_CSV_PATH    = os.path.join(DATA_DIR, "skills.csv")
JOB_ROLES_JSON_PATH = os.path.join(DATA_DIR, "job_roles.json")


# ── File Upload Settings ──────────────────────────────────────────────────────

# Maximum allowed resume file size (in megabytes)
MAX_FILE_SIZE_MB = 5

# Supported file types for resume upload
ALLOWED_FILE_TYPES = ["pdf", "docx"]


# ── ATS Scoring Weights ───────────────────────────────────────────────────────
# Each category contributes a percentage to the final ATS score (must sum to 100)

ATS_WEIGHTS = {
    "skills_match":       0.40,   # How many required skills are present
    "keyword_density":    0.20,   # Frequency and variety of relevant keywords
    "section_completeness": 0.20, # Presence of key resume sections
    "quantified_impact":  0.10,   # Numbers, percentages, measurable results
    "formatting_quality": 0.10,   # Clean text, no excessive symbols/artifacts
}


# ── Resume Section Keywords ───────────────────────────────────────────────────
# Used by the parser to detect and label resume sections

SECTION_HEADERS = {
    "experience":  ["experience", "work experience", "employment", "work history",
                    "professional experience", "internship", "internships"],
    "education":   ["education", "academic background", "qualifications",
                    "educational background", "academic qualifications"],
    "skills":      ["skills", "technical skills", "core competencies",
                    "technologies", "tools", "expertise"],
    "projects":    ["projects", "personal projects", "academic projects",
                    "key projects", "portfolio"],
    "certifications": ["certifications", "certificates", "courses",
                       "professional development", "training"],
    "summary":     ["summary", "objective", "profile", "about me",
                    "professional summary", "career objective"],
}


# ── Scoring Thresholds ────────────────────────────────────────────────────────
# ATS score bands shown in the UI

SCORE_BANDS = {
    "excellent": 85,   # 85–100 → Excellent
    "good":      70,   # 70–84  → Good
    "fair":      50,   # 50–69  → Fair
    "poor":       0,   # 0–49   → Needs Work
}

SCORE_COLORS = {
    "excellent": "#2ecc71",   # green
    "good":      "#f39c12",   # orange
    "fair":      "#e67e22",   # dark orange
    "poor":      "#e74c3c",   # red
}


# ── Job Match Settings ────────────────────────────────────────────────────────

# Minimum match percentage to be considered a viable candidate
MINIMUM_MATCH_THRESHOLD = 40

# Weight split between hard skill overlap and semantic (TF-IDF) similarity
JOB_MATCH_WEIGHTS = {
    "skill_overlap": 0.65,   # Direct keyword/skill matches
    "semantic_similarity": 0.35,  # TF-IDF cosine similarity
}


# ── Feedback Settings ─────────────────────────────────────────────────────────

# Maximum number of missing skills to show in feedback (avoid overwhelming the user)
MAX_MISSING_SKILLS_SHOWN = 10

# Maximum number of improvement suggestions shown at once
MAX_SUGGESTIONS_SHOWN = 6


# ── Streamlit UI Settings ─────────────────────────────────────────────────────

APP_TITLE = "AI Resume Analyzer"
APP_ICON  = "📄"
APP_DESCRIPTION = (
    "Upload your resume and select a target job role. "
    "Get an ATS score, skill gap analysis, and actionable feedback instantly."
)

# Streamlit page layout
PAGE_LAYOUT = "wide"
SIDEBAR_STATE = "expanded"


# ── Quantification Detection ──────────────────────────────────────────────────
# Regex patterns used by the ATS scorer to detect measurable impact

QUANTIFICATION_PATTERNS = [
    r"\d+\s*%",           # percentages:   "improved by 30%"
    r"\$[\d,]+",          # dollar amounts: "$50,000"
    r"\d+\s*x\b",         # multipliers:   "3x faster"
    r"\b\d{4}\b",         # years:         "2023"
    r"\b\d+\+?\s*(users|clients|students|employees|members|projects|features)",
]