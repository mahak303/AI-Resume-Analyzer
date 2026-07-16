# AI Resume Analyzer

An AI-powered Resume Analyzer built using Python and Streamlit that evaluates resumes against different job roles using ATS (Applicant Tracking System) principles.

The application extracts information from uploaded resumes, identifies technical skills, calculates an ATS score, compares the resume with the selected job role, highlights missing skills, and provides personalized suggestions to improve the resume.

This project was built to gain practical experience with Python, Natural Language Processing (NLP), machine learning concepts, and interactive web application development while solving a real-world problem.

---

## Live Demo

🔗 **Streamlit:** <https://ai-resume-analyzer-kughlm8hoad2tnqvytpexz.streamlit.app/>

## GitHub Repository

🔗 **GitHub:** <https://github.com/mahak303/AI-Resume-Analyzer>

---

## Features

- Upload resumes in **PDF** and **DOCX** formats.
- Extract resume text automatically.
- Detect technical skills using NLP.
- Categorize detected skills.
- Calculate an ATS score out of 100.
- Display a detailed ATS score breakdown.
- Match resumes against different job roles.
- Show required and missing skills.
- Generate personalized resume improvement suggestions.
- Recommend technologies and learning resources.
- Interactive dashboard with visual charts.
- Modern and responsive Streamlit interface.

---

## Supported Job Roles

The application currently supports multiple software and AI-related roles including:

- AI Engineer
- Machine Learning Engineer
- Data Scientist
- Data Analyst
- Python Developer
- Java Developer
- Backend Developer
- Frontend Developer
- Full Stack Developer
- DevOps Engineer
- Cybersecurity Analyst
- Fresher
- AI/ML Intern
- Data Science Intern
- Software Development Intern

The job roles can be extended easily by updating the `job_roles.json` file.

---

## Tech Stack

| Category | Technologies |
|----------|--------------|
| Language | Python |
| Framework | Streamlit |
| NLP | spaCy |
| Machine Learning | Scikit-learn |
| Data Processing | Pandas, NumPy |
| Resume Parsing | pdfplumber, python-docx |
| Visualization | Plotly |
| Version Control | Git & GitHub |

---

## Project Structure

```
AI-Resume-Analyzer
│
├── app.py                 # Main Streamlit application
├── config.py              # Project configuration
├── requirements.txt       # Project dependencies
├── runtime.txt            # Deployment runtime configuration
├── README.md
│
├── .streamlit/
│   └── config.toml        # Streamlit configuration
│
├── data/
│   ├── skills.csv         # Skills database
│   └── job_roles.json     # Job roles and matching criteria
│
├── src/
│   ├── pdf_parser.py      # Resume parsing
│   ├── skill_extractor.py # Skill extraction
│   ├── ats_engine.py      # ATS scoring & role matching
│   └── suggestions.py     # Recommendation engine
│
├── screenshots/           # Application screenshots
└── sample_resumes/        # Sample resumes for testing
```

---

## How It Works

```
Resume Upload
      │
      ▼
Resume Parsing
      │
      ▼
Skill Extraction
      │
      ▼
ATS Score Calculation
      │
      ▼
Job Role Matching
      │
      ▼
Missing Skills Detection
      │
      ▼
Personalized Suggestions
      │
      ▼
Learning Recommendations
```
## Installation

Clone the repository:

```bash
git clone https://github.com/mahak303/AI-Resume-Analyzer.git
cd AI-Resume-Analyzer
```

Create and activate a virtual environment (recommended):

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install all required dependencies:

```bash
pip install -r requirements.txt
```

Download the required spaCy language model:

```bash
python -m spacy download en_core_web_sm
```

Run the application:

```bash
streamlit run app.py
```

---

## Using the Application

1. Launch the Streamlit application.
2. Upload a resume in **PDF** or **DOCX** format.
3. Select the target job role from the dropdown menu.
4. Click **Analyze Resume**.
5. Review the generated report, including:
   - ATS Score
   - Score Breakdown
   - Job Match Percentage
   - Missing Skills
   - Personalized Suggestions
   - Learning Recommendations
   - Interactive Charts

---

## ATS Scoring Methodology

The ATS score is calculated using multiple evaluation criteria rather than simple keyword matching.

The analysis considers:

- Skill matching
- Resume section completeness
- Contact information
- Job-specific keyword relevance
- Resume length
- Quantified achievements

Each factor contributes to the final ATS score, providing a more balanced evaluation of the resume.

---

## Supported Resume Formats

Currently supported formats:

- PDF (.pdf)
- Microsoft Word (.docx)

---

## Configuration

Most configurable settings are centralized in `config.py`, including:

- ATS scoring weights
- Supported file formats
- Resume section detection
- Application settings
- Score thresholds
- UI configuration

Job roles and their required skills can be modified by updating `data/job_roles.json`.

The skills database used during analysis is maintained in `data/skills.csv`.

---

## Deployment

The application is deployed using **Streamlit Community Cloud**.

The repository includes:

- `requirements.txt` for dependency management.
- `runtime.txt` for Python version configuration.
- `.streamlit/config.toml` for Streamlit settings.

---

## Sample Workflow

```
Upload Resume
      │
      ▼
Extract Resume Content
      │
      ▼
Detect Skills
      │
      ▼
Select Target Role
      │
      ▼
Calculate ATS Score
      │
      ▼
Compare Required Skills
      │
      ▼
Identify Skill Gaps
      │
      ▼
Generate Suggestions
      │
      ▼
Display Interactive Dashboard
```
## Project Development

The project was developed incrementally, with each phase focusing on adding new functionality while keeping the application modular and maintainable.

### Phase 1 – Project Planning & Setup

- Planned the overall project architecture.
- Selected the technology stack.
- Created the project structure.
- Configured the development environment.
- Organized project modules and configuration files.

---

### Phase 2 – Resume Parsing & Skill Extraction

- Implemented PDF and DOCX resume parsing.
- Extracted resume text for analysis.
- Built the skill extraction pipeline using NLP.
- Categorized detected skills.
- Organized skills using a structured skills database.

---

### Phase 3 – Resume Analysis

- Added resume section detection.
- Identified important resume components.
- Improved preprocessing for more accurate analysis.
- Enhanced skill detection and categorization.

---

### Phase 4 – ATS Scoring Engine

- Designed an ATS scoring system based on multiple evaluation criteria.
- Added detailed score breakdown.
- Evaluated resume completeness.
- Analyzed keyword relevance.
- Considered quantified achievements and contact information while calculating the final score.

---

### Phase 5 – Job Role Matching

- Added support for multiple job roles.
- Compared resume skills with job-specific requirements.
- Calculated role match percentage.
- Identified missing required skills.
- Extended support for AI, Data Science, Software Development, and Internship roles.

---

### Phase 6 – Personalized Suggestions

- Generated improvement suggestions based on resume analysis.
- Recommended skills to learn for the selected role.
- Added learning recommendations.
- Provided actionable feedback for improving ATS compatibility.

---

### Phase 7 – UI Enhancement

- Redesigned the Streamlit interface.
- Improved dashboard layout.
- Added interactive charts using Plotly.
- Enhanced user experience with modern components and visualizations.
- Improved overall responsiveness and presentation.

---

### Phase 8 – Finalization

- Performed testing across different resume formats.
- Deployed the application using Streamlit Community Cloud.
- Prepared project documentation.
- Organized repository for public release.

---

## Challenges Faced

During development, a few practical challenges were encountered:

- Extracting text reliably from resumes with different layouts.
- Handling inconsistent formatting across PDF and DOCX files.
- Improving skill matching accuracy while minimizing false detections.
- Designing an ATS scoring system that balances multiple evaluation factors.
- Supporting multiple job roles using configurable JSON data.
- Resolving dependency and deployment issues during cloud deployment.

These challenges helped improve both the implementation and understanding of real-world software development workflows.

---

## Future Improvements

Some features that can be added in future versions include:

- Resume ranking against multiple job roles simultaneously.
- AI-generated resume rewriting suggestions.
- OCR support for scanned resumes.
- Company-specific ATS templates.
- Authentication and user accounts.
- Resume history and analytics dashboard.
- Support for additional file formats.
- Exportable analysis reports.
- Integration with job portals.

## Screenshots:
- Home page and placeholder for resume files:  (<Screenshot (34).png>)
- ATS Analysis: (<Screenshot (35).png>)
- Strengths and weakness: (<Screenshot (36).png>)
- Role Match : (<Screenshot (37).png>)
- Skill Analysis: (<Screenshot (39).png>) , (<Screenshot (38).png>)
- Recommendations for improvement: (<Screenshot (41).png>)
- app sidebar :(<Screenshot 2026-07-16 184055.png>) ,(<Screenshot 2026-07-16 183645.png>)

## Author

**Mahak Keswani**

B.Tech in Artificial Intelligence & Data Science

GitHub: https://github.com/mahak303

LinkedIn: https://www.linkedin.com/in/mahak-keswani-7115113aa/

Email: mahak303keswani@gmail.com

---

If you have any suggestions, feedback, or would like to contribute, feel free to open an issue or submit a pull request.
