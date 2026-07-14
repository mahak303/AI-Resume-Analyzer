"""
──────────────────
Extracts skills from resume text by matching against our skills database (skills.csv).

How it works:
  1. Load all skills and their aliases from skills.csv into memory.
  2. Use spaCy to tokenize and lemmatize the resume text.
     - Tokenization: split text into individual words.
     - Lemmatization: reduce words to their base form.
       e.g. "databases" → "database", "developing" → "develop"
  3. Match lemmatized resume tokens against each skill in the database.
  4. Also check for multi-word skills (e.g. "machine learning", "deep learning")
     directly in the original lowercased text using regex.
  5. Return matched skills as a structured dictionary grouped by category.

Why spaCy here:
  Lemmatization improves matching accuracy. Without it, "databases" would NOT
  match "database" in our CSV. With lemmatization, both match correctly.
"""

import re
import logging
import pandas as pd
import spacy

from config import SKILLS_CSV_PATH, SPACY_MODEL

# ── Logger Setup ──────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


# ── Load spaCy Model ──────────────────────────────────────────────────────────

def _load_spacy_model() -> spacy.language.Language:
    """
    Load the spaCy English language model.

    We disable the 'parser' and 'ner' components because we only need
    the tokenizer and lemmatizer. Disabling unused components makes
    spaCy significantly faster for our use case.

    Returns:
        A loaded spaCy Language object.

    Raises:
        RuntimeError: If the spaCy model is not installed.
    """
    try:
        nlp = spacy.load(SPACY_MODEL, disable=["parser", "ner"])
        logger.info("spaCy model '%s' loaded successfully", SPACY_MODEL)
        return nlp
    except OSError:
        logger.error("spaCy model '%s' not found.", SPACY_MODEL)
        raise RuntimeError(
            f"spaCy model '{SPACY_MODEL}' is not installed. "
            f"Please run: python -m spacy download {SPACY_MODEL}"
        )


# Load the model once at module level so it is not reloaded on every function call.
# In Streamlit, this means the model loads once per session, not once per upload.
_nlp = _load_spacy_model()


# ── Load Skills Database ──────────────────────────────────────────────────────

def _load_skills_database() -> pd.DataFrame:
    """
    Load the skills database from skills.csv into a pandas DataFrame.

    The CSV has three columns:
      - category : e.g. "Programming Languages", "Machine Learning"
      - skill    : e.g. "Python", "TensorFlow"
      - aliases  : comma-separated alternatives, e.g. "python3,py"

    Returns:
        A pandas DataFrame containing all skills and their metadata.

    Raises:
        RuntimeError: If the CSV file cannot be found or read.
    """
    try:
        df = pd.read_csv(SKILLS_CSV_PATH)

        # Normalize column names — strip spaces and convert to lowercase
        df.columns = df.columns.str.lower().str.strip()

        # Fill any missing alias values with empty string to avoid NaN errors
        df["aliases"] = df["aliases"].fillna("")

        logger.info("Loaded %d skills from skills.csv", len(df))
        return df

    except FileNotFoundError:
        logger.error("skills.csv not found at path: %s", SKILLS_CSV_PATH)
        raise RuntimeError(
            f"Skills database not found at: {SKILLS_CSV_PATH}. "
            "Make sure skills.csv exists in the data/ folder."
        )
    except Exception as e:
        logger.error("Failed to load skills database: %s", str(e))
        raise RuntimeError(f"Failed to load skills database: {str(e)}")


# Load skills once at module level for the same reason as the spaCy model
_skills_df = _load_skills_database()


# ── Text Preprocessing with spaCy ─────────────────────────────────────────────

def _preprocess_text(text: str) -> tuple[set, str]:
    """
    Use spaCy to tokenize and lemmatize resume text for skill matching.

    This is where spaCy adds meaningful value to the project:

      Tokenization — splits raw text into clean individual word tokens.
      Lemmatization — converts each word to its base dictionary form.

    Example:
      Input : "Developed machine learning models using PostgreSQL databases"
      Tokens: {"develop", "machine", "learning", "model", "use", "postgresql", "database"}

    Without lemmatization, "databases" would NOT match "database" in skills.csv.
    With lemmatization, it matches correctly.

    Args:
        text: Cleaned resume text string from pdf_parser.py.

    Returns:
        A tuple of:
          - lemma_set  : set of lowercased lemmatized tokens (single-word matching)
          - lower_text : full lowercased text (multi-word phrase matching)
    """
    # Run the text through the spaCy pipeline (tokenizer + lemmatizer only)
    doc = _nlp(text)

    # Build a set of lemmatized, lowercased tokens.
    # Filter out punctuation, whitespace, and very short tokens (noise).
    lemma_set = {
        token.lemma_.lower()
        for token in doc
        if not token.is_punct
        and not token.is_space
        and len(token.text) > 1
    }

    logger.debug("Preprocessed text into %d unique lemmas", len(lemma_set))

    # Keep the full lowercased text for multi-word skill phrase matching
    lower_text = text.lower()

    return lemma_set, lower_text


# ── Skill Matching ────────────────────────────────────────────────────────────

def _skill_is_present(
    skill: str,
    aliases: str,
    lemma_set: set,
    lower_text: str,
) -> bool:
    """
    Check whether a skill (or any of its aliases) is present in the resume.

    Matching strategy:
      Single-word skills  (e.g. "Python")         → check lemma_set
      Multi-word skills   (e.g. "Machine Learning") → regex phrase search in lower_text
      Aliases are checked using the same single/multi-word logic.

    Args:
        skill     : Skill name from skills.csv, e.g. "Python".
        aliases   : Comma-separated alias string, e.g. "python3,py".
        lemma_set : Set of lemmatized tokens from the resume.
        lower_text: Full lowercased resume text.

    Returns:
        True if the skill or any alias is found in the resume, False otherwise.
    """
    # Build a list of all terms to check: the skill name + all aliases
    terms_to_check = [skill.lower()]

    if aliases:
        alias_list = [a.strip().lower() for a in aliases.split(",") if a.strip()]
        terms_to_check.extend(alias_list)

    for term in terms_to_check:
        words = term.split()

        if len(words) == 1:
            # Single-word: lemmatize the skill term too, then check lemma_set
            skill_doc = _nlp(term)
            skill_lemma = skill_doc[0].lemma_.lower() if skill_doc else term

            if skill_lemma in lemma_set or term in lemma_set:
                return True
        else:
            # Multi-word: search for the exact phrase using word boundaries
            # \b ensures "java" doesn't match inside "javascript"
            pattern = r"\b" + re.escape(term) + r"\b"
            if re.search(pattern, lower_text):
                return True

    return False


# ── Main Entry Point ──────────────────────────────────────────────────────────

def extract_skills(resume_text: str) -> dict:
    """
    Extract all skills from a resume and return them grouped by category.

    This is the primary function called by the rest of the application
    (analyzer.py and app.py).

    Process:
      1. Preprocess resume text using spaCy (tokenize + lemmatize).
      2. For each skill in skills.csv, check if it appears in the resume.
      3. Collect matched skills, avoiding duplicates.
      4. Group results by category and also return a flat list.

    Args:
        resume_text: Cleaned resume text string from pdf_parser.py.

    Returns:
        A dictionary with two keys:
          "by_category" : dict mapping category → list of matched skill names
                          e.g. {"Programming Languages": ["Python", "Java"]}
          "all_skills"  : flat deduplicated list of all matched skill names
                          e.g. ["Python", "Java", "MySQL"]

    Example:
        >>> result = extract_skills("Python developer with MySQL experience")
        >>> result["all_skills"]
        ["Python", "MySQL"]
        >>> result["by_category"]
        {"Programming Languages": ["Python"], "Databases": ["MySQL"]}
    """
    if not resume_text or not resume_text.strip():
        logger.warning("extract_skills received empty resume text")
        return {"by_category": {}, "all_skills": []}

    # Step 1: Preprocess with spaCy
    lemma_set, lower_text = _preprocess_text(resume_text)

    # Step 2: Match each skill in the database
    matched_by_category: dict[str, list] = {}
    seen_skills: set = set()  # Track matched skills to prevent duplicates

    for _, row in _skills_df.iterrows():
        category = row["category"]
        skill    = row["skill"]
        aliases  = row["aliases"]

        # Skip if we've already matched this skill (avoid duplicates)
        if skill in seen_skills:
            continue

        if _skill_is_present(skill, aliases, lemma_set, lower_text):
            seen_skills.add(skill)

            # Group by category
            if category not in matched_by_category:
                matched_by_category[category] = []
            matched_by_category[category].append(skill)

    all_matched = list(seen_skills)

    logger.info(
        "Skill extraction complete. Found %d skill(s) across %d categorie(s)",
        len(all_matched),
        len(matched_by_category),
    )

    return {
        "by_category": matched_by_category,
        "all_skills":  all_matched,
    }


# ── Convenience Wrappers ──────────────────────────────────────────────────────

def get_skills_by_category(resume_text: str) -> dict[str, list]:
    """
    Return only the category-grouped skill dictionary.

    Args:
        resume_text: Cleaned resume text.

    Returns:
        Dict mapping category names to lists of matched skill names.
    """
    return extract_skills(resume_text)["by_category"]


def get_all_skills(resume_text: str) -> list[str]:
    """
    Return only the flat deduplicated list of matched skill names.

    Args:
        resume_text: Cleaned resume text.

    Returns:
        List of matched skill name strings.
    """
    return extract_skills(resume_text)["all_skills"]