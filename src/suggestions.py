"""

Generates intelligent, role-specific improvement suggestions and personalised
learning steps for the AI Resume Analyzer.

Why this module exists:
  The generic suggestions in ats_scorer.py (_build_suggestions) only look at
  structural issues — missing sections, contact info, length, keywords.
  They say nothing about WHAT to learn or HOW to improve for a specific role.

  This module adds two things:
    1. Role-specific suggestions — prioritised, actionable, and filtered so
       suggestions already satisfied by the resume are never shown.
    2. "Recommended Next Learning Steps" — technologies, certifications, and
       project ideas tailored to the selected job role.

Public API:
    build_role_suggestions(
        job_role, missing_required, missing_preferred,
        found_sections, found_contact, length_message,
        keyword_count, total_role_keywords, quantify_count
    ) -> list[str]

    get_learning_steps(job_role) -> dict

Design principle:
    All role knowledge is defined as plain data (dicts) at the top of this
    module. The functions only read from that data — no hardcoded strings
    inside function bodies.
"""

import logging
from config import MAX_SUGGESTIONS_SHOWN

logger = logging.getLogger(__name__)


# ── Role-Specific Skill Suggestions ──────────────────────────────────────────
# For each role: a prioritised list of (skill, suggestion_text) tuples.
# Order matters — highest-impact suggestions come first.
# These are only shown when the skill is MISSING from the resume.

_ROLE_SKILL_SUGGESTIONS: dict[str, list[tuple[str, str]]] = {

    "Python Developer": [
        ("FastAPI",       "Build a REST API project using FastAPI — it's the most in-demand Python web framework right now."),
        ("Django",        "Add Django experience: build a full CRUD web app and include it in your Projects section."),
        ("pytest",        "Demonstrate testing discipline: add unit tests with pytest to an existing project."),
        ("Docker",        "Containerise one of your projects with Docker and document it in your README."),
        ("PostgreSQL",    "Switch a project from SQLite to PostgreSQL to show production database experience."),
        ("Unit Testing",  "Include test coverage metrics in your projects to stand out as a quality-focused developer."),
        ("Linux",         "Get comfortable with Linux commands — document your usage in project READMEs."),
        ("Redis",         "Add Redis caching to an API project to demonstrate performance optimisation."),
    ],

    "Java Developer": [
        ("Spring Boot",   "Build a Spring Boot REST API project — it is the industry standard for Java backend roles."),
        ("JUnit",         "Add JUnit test coverage to your Java projects and mention it on your resume."),
        ("Maven",         "Use Maven or Gradle for dependency management in your projects."),
        ("Microservices", "Build two small Spring Boot services that communicate via REST to demonstrate microservices knowledge."),
        ("Docker",        "Containerise your Spring Boot application with Docker."),
        ("Kafka",         "Integrate a basic Kafka producer/consumer into a Java project."),
        ("Hibernate",     "Use Hibernate ORM in a Spring Boot project to show database mapping skills."),
    ],

    "Data Analyst": [
        ("SQL",                      "Practice advanced SQL (window functions, CTEs) on a real dataset and publish the queries on GitHub."),
        ("Power BI",                 "Build an end-to-end dashboard in Power BI using a public dataset."),
        ("Tableau",                  "Create a Tableau Public portfolio with at least two interactive dashboards."),
        ("Exploratory Data Analysis","Include a documented EDA notebook in your GitHub for every project."),
        ("Statistical Analysis",     "Add a project that uses statistical tests (t-test, chi-square) to support a business decision."),
        ("A/B Testing",              "Document an A/B testing case study — even a simulated one shows strong analytical thinking."),
        ("Excel",                    "Showcase Excel pivot tables and VLOOKUP skills — many analyst roles still rely on Excel."),
    ],

    "Data Scientist": [
        ("Scikit-learn",    "Build an end-to-end ML pipeline (preprocess → train → evaluate → save) and publish it on GitHub."),
        ("Feature Engineering", "Document a feature engineering notebook — it is one of the most valued data science skills."),
        ("XGBoost",         "Use XGBoost or LightGBM in a Kaggle competition and include your leaderboard rank."),
        ("TensorFlow",      "Complete a deep learning project using TensorFlow/Keras and deploy it."),
        ("PyTorch",         "Build and train a neural network in PyTorch — include it as a pinned GitHub project."),
        ("A/B Testing",     "Add an A/B testing or hypothesis testing project to demonstrate statistical thinking."),
        ("Time Series Analysis", "Forecast a real-world time series (stock prices, weather) and publish your approach."),
        ("AWS",             "Deploy a trained model as an API on AWS SageMaker or a Flask endpoint on EC2."),
    ],

    "Machine Learning Engineer": [
        ("TensorFlow",          "Train and serve a TensorFlow model — include training metrics and a deployment step."),
        ("PyTorch",             "Build a PyTorch model and export it using TorchScript or ONNX for deployment."),
        ("Docker",              "Package your ML model as a Docker container with a REST API endpoint."),
        ("Hyperparameter Tuning","Add Optuna or GridSearchCV hyperparameter tuning to an existing model project."),
        ("Feature Engineering", "Build a feature engineering pipeline with scikit-learn Pipelines and ColumnTransformer."),
        ("Model Evaluation",    "Include confusion matrices, ROC curves, and cross-validation scores in your project notebooks."),
        ("Kubernetes",          "Deploy a model-serving container on Kubernetes — even a local minikube setup counts."),
        ("CI/CD",               "Set up a GitHub Actions workflow that tests and retrains your model automatically."),
    ],

    "AI Engineer": [
        ("LangChain",                  "Build a LangChain-powered chatbot or document Q&A system and publish it on GitHub."),
        ("Retrieval Augmented Generation", "Build a RAG pipeline: embed documents, store in a vector DB, and query with an LLM."),
        ("Vector Databases",           "Integrate Pinecone, Chroma, or FAISS into a project to demonstrate vector search skills."),
        ("Prompt Engineering",         "Document a prompt engineering case study showing how prompt changes affect output quality."),
        ("OpenAI API",                 "Build a practical tool using the OpenAI API (e.g. resume reviewer, code explainer)."),
        ("Hugging Face",               "Fine-tune a small Hugging Face model on a custom dataset and publish the model card."),
        ("FastAPI",                    "Wrap your AI feature in a FastAPI endpoint so it can be consumed as a service."),
        ("Fine Tuning",                "Fine-tune an open-source LLM (e.g. Mistral, LLaMA) using LoRA/QLoRA."),
    ],

    "Backend Developer": [
        ("REST API",        "Build a fully documented REST API with authentication, pagination, and error handling."),
        ("Authentication",  "Implement JWT or OAuth2 authentication in one of your backend projects."),
        ("PostgreSQL",      "Use PostgreSQL with proper indexing and transactions in a production-style project."),
        ("Redis",           "Add Redis for caching or session management in an existing API project."),
        ("Docker",          "Containerise your backend application and use Docker Compose for local development."),
        ("Microservices",   "Split a monolithic project into two services that communicate via HTTP or a message queue."),
        ("MongoDB",         "Build a project using MongoDB to show NoSQL database experience."),
        ("GraphQL",         "Add a GraphQL endpoint to an existing REST API project."),
    ],

    "Frontend Developer": [
        ("React",           "Build a multi-page React application with routing, state management, and API integration."),
        ("TypeScript",      "Migrate an existing JavaScript project to TypeScript to demonstrate type-safe coding."),
        ("Next.js",         "Build a Next.js application to show server-side rendering and SEO-optimised frontend skills."),
        ("Jest",            "Add Jest unit tests to a React component library."),
        ("Redux",           "Use Redux Toolkit for state management in a medium-complexity React project."),
        ("Figma",           "Include Figma mockups alongside your frontend projects to show design awareness."),
        ("Responsive Design","Ensure all portfolio projects are fully responsive and tested on mobile viewports."),
    ],

    "Full Stack Developer": [
        ("React",       "Build a full-stack app with a React frontend and Python/Node.js backend with a real database."),
        ("Node.js",     "Add a Node.js/Express backend to a frontend project to demonstrate full stack capability."),
        ("PostgreSQL",  "Use PostgreSQL instead of SQLite in your next full-stack project."),
        ("Docker",      "Use Docker Compose to run your full-stack app (frontend, backend, database) locally."),
        ("TypeScript",  "Add TypeScript to your frontend for type safety across the stack."),
        ("CI/CD",       "Set up a GitHub Actions pipeline that tests and deploys both frontend and backend."),
        ("GraphQL",     "Replace REST endpoints with a GraphQL API in one project to show API design versatility."),
    ],

    "DevOps Engineer": [
        ("Kubernetes",     "Deploy a multi-container application on Kubernetes and document the manifests on GitHub."),
        ("Terraform",      "Write Terraform scripts to provision cloud infrastructure (even on a free tier)."),
        ("CI/CD",          "Set up a complete CI/CD pipeline using GitHub Actions or Jenkins with test, build, and deploy stages."),
        ("Ansible",        "Automate server configuration with an Ansible playbook."),
        ("Prometheus",     "Add Prometheus monitoring and Grafana dashboards to a Docker Compose project."),
        ("Helm",           "Package a Kubernetes application as a Helm chart."),
        ("AWS",            "Earn the AWS Cloud Practitioner certification to validate cloud fundamentals."),
        ("GitHub Actions", "Automate a real workflow (lint, test, build Docker image) with GitHub Actions."),
    ],

    "Cybersecurity Analyst": [
        ("Penetration Testing",   "Complete TryHackMe or HackTheBox rooms and document your methodology."),
        ("SIEM",                  "Set up a home lab with a SIEM tool (Splunk Free or ELK Stack) and analyse sample logs."),
        ("Vulnerability Assessment", "Run a vulnerability assessment on a test VM using Nessus or OpenVAS."),
        ("OWASP",                 "Build a project demonstrating OWASP Top 10 defences in a web application."),
        ("Kali Linux",            "Document your Kali Linux penetration testing workflow with a write-up."),
        ("Wireshark",             "Publish a Wireshark packet analysis case study on GitHub or a blog."),
        ("Cloud Security",        "Earn the AWS Security Specialty or CompTIA Security+ certification."),
        ("Python",                "Write Python scripts for log parsing, port scanning, or automation of security tasks."),
    ],

    "Software Engineering Intern": [
        ("Data Structures",              "Practise LeetCode Easy/Medium problems daily — document your solutions on GitHub."),
        ("Algorithms",                   "Complete a data structures & algorithms course (NPTEL or CS50) and list it on your resume."),
        ("Git",                          "Contribute to an open-source project on GitHub — even fixing a typo counts."),
        ("Object Oriented Programming",  "Build a Python or Java OOP project (e.g. library management system) and push it to GitHub."),
        ("Python",                       "Build two small Python projects and publish them with proper READMEs."),
        ("Problem Solving",              "Join a competitive programming contest (CodeChef, Codeforces) and list your rating."),
        ("SQL",                          "Complete SQL exercises on HackerRank or Mode Analytics and list the certificate."),
    ],

    "Entry-Level Software Developer": [
        ("REST API",                     "Build and document a REST API with at least five endpoints and deploy it."),
        ("Unit Testing",                 "Add unit tests with at least 60% coverage to one of your existing projects."),
        ("Docker",                       "Containerise a project and include Docker setup instructions in the README."),
        ("SQL",                          "Build a project with a relational database and write optimised SQL queries."),
        ("CI/CD",                        "Set up a simple GitHub Actions workflow that runs your tests automatically."),
        ("Object Oriented Programming",  "Refactor an existing project to use clean OOP principles and design patterns."),
    ],

    "AI/ML Intern": [
        ("Scikit-learn",        "Complete an end-to-end ML project: load data, preprocess, train, evaluate, and save the model."),
        ("Exploratory Data Analysis", "Publish a well-documented EDA notebook on Kaggle or GitHub for every project."),
        ("Pandas",              "Complete the Kaggle Pandas course and solve three dataset challenges."),
        ("Jupyter Notebook",    "Make your Jupyter notebooks clean and readable — they are your portfolio for ML roles."),
        ("Machine Learning",    "Enter a Kaggle competition at any level and include your rank in your resume."),
        ("TensorFlow",          "Build a basic image classifier using TensorFlow/Keras as a first deep learning project."),
        ("Google Colab",        "Host your ML projects on Google Colab with shared links so reviewers can run them."),
    ],

    "Data Analyst Intern": [
        ("SQL",                       "Practise SQL on Mode Analytics or StrataScratch and list the exercises on your resume."),
        ("Excel",                     "Build an Excel dashboard with pivot tables, slicers, and charts using a real dataset."),
        ("Power BI",                  "Create a Power BI dashboard on a public dataset and publish the .pbix file."),
        ("Exploratory Data Analysis", "Publish a documented EDA notebook that tells a clear data story."),
        ("Statistical Analysis",      "Add a project using descriptive statistics and simple visualisations."),
        ("Python",                    "Learn Python for data analysis: complete the Kaggle Python and Pandas micro-courses."),
        ("Tableau",                   "Build one Tableau Public visualisation and link it from your resume."),
    ],

    "Generative AI Engineer": [
        ("LangChain",                  "Build a LangChain document Q&A or agent project and deploy it as a web app."),
        ("Retrieval Augmented Generation", "Build a RAG system: chunk documents, embed them, store in a vector DB, and query with an LLM."),
        ("Prompt Engineering",         "Document a prompt engineering comparison study — show how prompts affect output quality."),
        ("Vector Databases",           "Integrate Chroma or Pinecone into a semantic search or RAG project."),
        ("OpenAI API",                 "Build a practical GenAI tool using the OpenAI API and deploy it publicly."),
        ("Hugging Face",               "Fine-tune a small open-source model on Hugging Face and publish a model card."),
        ("Fine Tuning",                "Fine-tune an LLM using LoRA/QLoRA on a custom dataset and publish the results."),
        ("FastAPI",                    "Wrap a GenAI feature in a FastAPI service with clear API documentation."),
    ],

    "NLP Engineer": [
        ("spaCy",               "Build a named entity recognition pipeline using spaCy on a custom dataset."),
        ("Hugging Face",        "Fine-tune a BERT or RoBERTa model for text classification on Hugging Face."),
        ("Text Classification", "Publish a multi-class text classification project with proper evaluation metrics."),
        ("Named Entity Recognition", "Build and evaluate a custom NER model and document your labelling approach."),
        ("Sentiment Analysis",  "Build a sentiment analysis tool on a real-world dataset (Twitter, product reviews)."),
        ("PyTorch",             "Implement a transformer model from scratch in PyTorch to deepen NLP understanding."),
        ("NLTK",                "Use NLTK for preprocessing and publish a text cleaning utility library."),
    ],

    "Computer Vision Engineer": [
        ("Convolutional Neural Networks", "Train a CNN from scratch on a dataset like CIFAR-10 and document the architecture."),
        ("Object Detection",    "Build a YOLO-based object detection project on a custom dataset."),
        ("Transfer Learning",   "Fine-tune a pretrained ResNet or EfficientNet model on a domain-specific image dataset."),
        ("PyTorch",             "Implement a full training loop in PyTorch including data augmentation and early stopping."),
        ("Image Classification","Build an image classifier web app and deploy it using Streamlit or FastAPI."),
        ("GANs",                "Implement a simple GAN (e.g. DCGAN) and publish generated image samples."),
        ("OpenCV",              "Build a real-time computer vision project using OpenCV (e.g. face detection, edge detection)."),
    ],
}


# ── Recommended Learning Steps ────────────────────────────────────────────────
# Role-specific learning roadmap: technologies, certifications, project ideas.
# These are shown unconditionally — they guide growth regardless of current level.

_LEARNING_STEPS: dict[str, dict] = {

    "Python Developer": {
        "technologies":    ["FastAPI", "Docker", "Redis", "Celery", "PostgreSQL", "Kubernetes"],
        "certifications":  ["Python Institute PCEP / PCAP", "AWS Cloud Practitioner", "Docker Certified Associate"],
        "project_ideas":   [
            "Build a URL shortener API with FastAPI + Redis + PostgreSQL",
            "Create a CLI tool that automates a repetitive task and publish it on PyPI",
            "Build a task queue system using Celery + Redis",
        ],
    },

    "Java Developer": {
        "technologies":    ["Spring Boot", "Apache Kafka", "Kubernetes", "Redis", "Hibernate"],
        "certifications":  ["Oracle Certified Professional Java SE", "Spring Professional Certification", "AWS Developer Associate"],
        "project_ideas":   [
            "Build a Spring Boot e-commerce REST API with JWT authentication",
            "Create a Kafka producer/consumer pipeline for real-time order processing",
            "Build a microservices demo with two Spring Boot services and an API gateway",
        ],
    },

    "Data Analyst": {
        "technologies":    ["Power BI", "Tableau", "dbt", "BigQuery", "Airflow"],
        "certifications":  ["Google Data Analytics Certificate", "Microsoft Power BI Data Analyst (PL-300)", "Tableau Desktop Specialist"],
        "project_ideas":   [
            "Analyse a public e-commerce dataset and build an executive KPI dashboard",
            "Build an end-to-end ETL pipeline from CSV to a Power BI dashboard",
            "Conduct an A/B test analysis on a marketing dataset and present findings",
        ],
    },

    "Data Scientist": {
        "technologies":    ["MLflow", "Apache Spark", "Streamlit", "dbt", "AWS SageMaker"],
        "certifications":  ["Google Professional Machine Learning Engineer", "IBM Data Science Professional Certificate", "Databricks Certified Associate Developer"],
        "project_ideas":   [
            "Enter a Kaggle competition and document your feature engineering approach",
            "Build and deploy a churn prediction model as a Streamlit app",
            "Create an end-to-end ML pipeline with MLflow tracking and model registry",
        ],
    },

    "Machine Learning Engineer": {
        "technologies":    ["MLflow", "Kubeflow", "Triton Inference Server", "ONNX", "Ray"],
        "certifications":  ["Google Professional ML Engineer", "AWS Machine Learning Specialty", "Databricks ML Professional"],
        "project_ideas":   [
            "Build a real-time model serving API with FastAPI + Docker + Kubernetes",
            "Set up an MLflow experiment tracking server and compare five model runs",
            "Build a CI/CD pipeline that automatically retrains a model on new data",
        ],
    },

    "AI Engineer": {
        "technologies":    ["LangChain", "LlamaIndex", "Pinecone", "Chroma", "Weaviate", "Ollama"],
        "certifications":  ["DeepLearning.AI LangChain Course", "OpenAI Developer Certification", "AWS AI Practitioner"],
        "project_ideas":   [
            "Build a RAG-powered PDF Q&A chatbot using LangChain + Chroma",
            "Create an AI agent that browses the web and summarises news for a topic",
            "Fine-tune a small LLM using LoRA on a custom domain dataset",
        ],
    },

    "Backend Developer": {
        "technologies":    ["Redis", "Kafka", "GraphQL", "gRPC", "Kubernetes"],
        "certifications":  ["AWS Developer Associate", "Docker Certified Associate", "MongoDB Associate Developer"],
        "project_ideas":   [
            "Build a scalable REST API with JWT auth, rate limiting, and Redis caching",
            "Create a real-time notification system using WebSockets and Redis Pub/Sub",
            "Build a microservices demo with an API gateway and service discovery",
        ],
    },

    "Frontend Developer": {
        "technologies":    ["Next.js", "TypeScript", "Redux Toolkit", "Tailwind CSS", "Storybook"],
        "certifications":  ["Meta Frontend Developer Certificate", "freeCodeCamp JavaScript Certification", "Google UX Design Certificate"],
        "project_ideas":   [
            "Build a responsive portfolio site with Next.js and Tailwind CSS",
            "Create a component library with Storybook documentation",
            "Build a real-time collaborative to-do app using React + WebSockets",
        ],
    },

    "Full Stack Developer": {
        "technologies":    ["Next.js", "TypeScript", "GraphQL", "Prisma", "Supabase"],
        "certifications":  ["Meta Full Stack Certificate", "AWS Cloud Practitioner", "MongoDB Associate Developer"],
        "project_ideas":   [
            "Build a full-stack SaaS app with auth, payments (Stripe), and a dashboard",
            "Create a real-time chat application with Next.js and WebSockets",
            "Build an e-commerce platform with a React frontend and Node.js backend",
        ],
    },

    "DevOps Engineer": {
        "technologies":    ["Helm", "ArgoCD", "Prometheus", "Grafana", "Vault"],
        "certifications":  ["CKA — Certified Kubernetes Administrator", "AWS DevOps Engineer Professional", "HashiCorp Terraform Associate"],
        "project_ideas":   [
            "Set up a full GitOps pipeline using ArgoCD, Helm, and a Kubernetes cluster",
            "Build a monitoring stack with Prometheus + Grafana and alert on SLA breaches",
            "Automate cloud infrastructure provisioning with Terraform and GitHub Actions",
        ],
    },

    "Cybersecurity Analyst": {
        "technologies":    ["Splunk", "Wireshark", "Metasploit", "Nessus", "Burp Suite"],
        "certifications":  ["CompTIA Security+", "Certified Ethical Hacker (CEH)", "Google Cybersecurity Certificate"],
        "project_ideas":   [
            "Complete 30 TryHackMe rooms and publish write-ups on a personal blog",
            "Set up a home SIEM lab with ELK Stack and analyse simulated attack logs",
            "Document an OWASP Top 10 vulnerability assessment on a deliberately vulnerable app",
        ],
    },

    "Software Engineering Intern": {
        "technologies":    ["Python", "Git", "SQL", "REST API", "Docker basics"],
        "certifications":  ["CS50x (Harvard)", "Google IT Support Certificate", "Python Institute PCEP"],
        "project_ideas":   [
            "Build a command-line task manager in Python with file persistence",
            "Create a simple REST API with Flask and deploy it on Render (free tier)",
            "Solve 50 LeetCode Easy problems and document your solutions on GitHub",
        ],
    },

    "Entry-Level Software Developer": {
        "technologies":    ["Docker", "PostgreSQL", "REST API", "CI/CD", "Redis"],
        "certifications":  ["AWS Cloud Practitioner", "Python Institute PCAP", "Oracle Java SE Foundations"],
        "project_ideas":   [
            "Build a full CRUD REST API with authentication and deploy it on Railway",
            "Contribute a bug fix or feature to an open-source GitHub repository",
            "Build a URL shortener with analytics tracking as a portfolio project",
        ],
    },

    "AI/ML Intern": {
        "technologies":    ["Scikit-learn", "TensorFlow / Keras", "Pandas", "Matplotlib", "Google Colab"],
        "certifications":  ["Google Machine Learning Crash Course", "IBM Machine Learning Professional Certificate", "Kaggle ML Micro-courses"],
        "project_ideas":   [
            "Enter a Kaggle Playground competition and publish your notebook",
            "Build a movie recommendation system using collaborative filtering",
            "Train a digit recogniser (MNIST) and deploy it as a Streamlit app",
        ],
    },

    "Data Analyst Intern": {
        "technologies":    ["SQL", "Excel", "Power BI", "Pandas", "Tableau Public"],
        "certifications":  ["Google Data Analytics Certificate", "Microsoft Excel Associate (MOS)", "Kaggle SQL Micro-course"],
        "project_ideas":   [
            "Analyse IPL / FIFA dataset and build an interactive Power BI dashboard",
            "Build a Python dashboard using Streamlit on a public government dataset",
            "Perform a sales trend analysis with SQL and visualise findings in Excel",
        ],
    },

    "Generative AI Engineer": {
        "technologies":    ["LangChain", "LlamaIndex", "Pinecone", "Ollama", "Gradio", "Streamlit"],
        "certifications":  ["DeepLearning.AI — LangChain for LLM Application Development", "Hugging Face NLP Course", "AWS AI Practitioner"],
        "project_ideas":   [
            "Build a RAG chatbot over your own PDF documents using LangChain + Chroma",
            "Create an AI writing assistant with a custom system prompt and memory",
            "Fine-tune Mistral-7B on a domain-specific Q&A dataset using QLoRA",
        ],
    },

    "NLP Engineer": {
        "technologies":    ["Hugging Face Transformers", "spaCy", "LangChain", "FAISS", "Gradio"],
        "certifications":  ["Hugging Face NLP Course (free)", "DeepLearning.AI NLP Specialisation", "Stanford CS224N (audit)"],
        "project_ideas":   [
            "Fine-tune BERT for a multi-label text classification task and publish on HF Hub",
            "Build a question-answering system over a Wikipedia corpus using dense retrieval",
            "Create a named entity recognition pipeline for a domain (medical, legal, finance)",
        ],
    },

    "Computer Vision Engineer": {
        "technologies":    ["PyTorch", "OpenCV", "Ultralytics YOLO", "ONNX", "Roboflow"],
        "certifications":  ["DeepLearning.AI CNN Specialisation", "PyTorch Developer Certificate", "OpenCV University Courses"],
        "project_ideas":   [
            "Train a custom YOLOv8 object detector on a Roboflow dataset and deploy it",
            "Build a real-time face mask detection system using OpenCV and a CNN",
            "Create an image similarity search engine using CNN embeddings and FAISS",
        ],
    },
}

# Fallback for roles not yet defined in the mappings above
_DEFAULT_LEARNING_STEPS: dict = {
    "technologies":   ["Python", "Git", "Docker", "REST API", "SQL"],
    "certifications": ["Google IT Support Certificate", "AWS Cloud Practitioner", "CS50x"],
    "project_ideas":  [
        "Build a portfolio project relevant to your target role and publish it on GitHub",
        "Contribute to an open-source project in your domain",
        "Deploy one of your projects publicly (Render, Railway, or Streamlit Cloud)",
    ],
}


# ── Public Functions ──────────────────────────────────────────────────────────

def build_role_suggestions(
    job_role            : str,
    missing_required    : list[str],
    missing_preferred   : list[str],
    found_sections      : list[str],
    found_contact       : list[str],
    length_message      : str,
    keyword_count       : int,
    total_role_keywords : int,
    quantify_count      : int,
) -> list[str]:
    """
    Build a prioritised, role-specific list of improvement suggestions.

    Priority order (highest impact first):
      1. Role-specific skill suggestions for each missing REQUIRED skill
      2. Missing resume sections (Experience, Education, Skills, Projects)
      3. Missing contact information (Email, Phone, LinkedIn)
      4. Resume length issues
      5. Low keyword density
      6. No quantified achievements

    Suggestions already satisfied by the resume are never shown.
    The list is capped at MAX_SUGGESTIONS_SHOWN from config.py.

    Args:
        job_role            : Selected job role name, e.g. "Python Developer".
        missing_required    : Required skills not found in the resume.
        missing_preferred   : Preferred skills not found in the resume.
        found_sections      : Resume sections detected.
        found_contact       : Contact info types detected (Email, Phone, LinkedIn).
        length_message      : Human-readable resume length assessment.
        keyword_count       : Number of role keywords matched.
        total_role_keywords : Total keywords defined for the role.
        quantify_count      : Number of quantified achievements found.

    Returns:
        Prioritised list of suggestion strings, capped at MAX_SUGGESTIONS_SHOWN.
    """
    suggestions: list[str] = []

    # Convert missing skills to lowercase set for O(1) lookups
    missing_required_lower  = {s.lower() for s in missing_required}
    missing_preferred_lower = {s.lower() for s in missing_preferred}

    # ── 1. Role-specific skill suggestions ────────────────────────────────
    # Look up suggestions for this role; fall back to empty list if unknown
    role_suggestions = _ROLE_SKILL_SUGGESTIONS.get(job_role, [])

    for skill, suggestion_text in role_suggestions:
        # Only show this suggestion if the skill is actually missing
        if skill.lower() in missing_required_lower or skill.lower() in missing_preferred_lower:
            suggestions.append(suggestion_text)
        # Stop early once we have enough high-priority role-specific items
        if len(suggestions) >= MAX_SUGGESTIONS_SHOWN - 2:
            break

    # ── 2. Missing resume sections ────────────────────────────────────────
    expected_sections = {"Experience", "Education", "Skills", "Projects"}
    for section in expected_sections:
        if section not in found_sections:
            suggestions.append(
                f"Add a '{section}' section — ATS systems look for this specifically."
            )

    # ── 3. Missing contact information ────────────────────────────────────
    if "Email" not in found_contact:
        suggestions.append("Add a professional email address to your resume.")

    if "Phone" not in found_contact:
        suggestions.append("Add a phone number to your contact information.")

    if "LinkedIn" not in found_contact:
        suggestions.append("Add your LinkedIn profile URL (linkedin.com/in/yourname).")

    # ── 4. Resume length ──────────────────────────────────────────────────
    if any(word in length_message for word in ("Too short", "Too long", "Long resume")):
        suggestions.append(length_message)

    # ── 5. Low keyword density ────────────────────────────────────────────
    if total_role_keywords > 0 and keyword_count < (total_role_keywords * 0.4):
        suggestions.append(
            "Use more role-specific keywords from the job description "
            "to improve ATS keyword matching."
        )

    # ── 6. No quantified achievements ────────────────────────────────────
    if quantify_count == 0:
        suggestions.append(
            "Add measurable achievements to your bullet points "
            "(e.g. 'Improved performance by 30%', 'Built a system serving 500+ users')."
        )

    logger.debug(
        "Built %d suggestion(s) for role '%s' (capped at %d)",
        min(len(suggestions), MAX_SUGGESTIONS_SHOWN),
        job_role,
        MAX_SUGGESTIONS_SHOWN,
    )
    return suggestions[:MAX_SUGGESTIONS_SHOWN]


def get_learning_steps(job_role: str) -> dict:
    """
    Return recommended learning steps for a given job role.

    Steps are role-specific and cover three categories:
      - technologies  : Tools and frameworks to learn next
      - certifications: Industry-recognised certifications worth pursuing
      - project_ideas : Concrete project ideas to build and add to a portfolio

    If the role is not found in the knowledge base, sensible defaults
    are returned so the function never fails.

    Args:
        job_role: Selected job role name, e.g. "Data Scientist".

    Returns:
        Dictionary with keys:
          "technologies"  : list[str]
          "certifications": list[str]
          "project_ideas" : list[str]
    """
    steps = _LEARNING_STEPS.get(job_role, _DEFAULT_LEARNING_STEPS)
    logger.debug("Learning steps retrieved for role: '%s'", job_role)
    return steps