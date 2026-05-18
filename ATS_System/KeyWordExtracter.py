import re
import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from DacumentExtracter import extract_text_from_pdf

# =========================================================
# LOAD AI MODEL
# =========================================================

print("Loading Semantic AI Model...")

model = SentenceTransformer("all-mpnet-base-v2")

# =========================================================
# INPUT DATA (DYNAMIC DOCUMENT)
# =========================================================

# The user wants to use 1.pdf for extraction
test_pdf = (
    r"C:\Users\parth_kozqdcr\OneDrive\Desktop\Hrm_Backend\ATS_System\Document\1.pdf"
)

if os.path.exists(test_pdf):
    print(f"--- Extracting text from: {os.path.basename(test_pdf)} ---")
    RESUME_TEXT = extract_text_from_pdf(test_pdf)
    if RESUME_TEXT.startswith("Error"):
        print(f"Fallback to hardcoded text due to extraction error: {RESUME_TEXT}")
        # Hardcoded fallback if PDF fails
        RESUME_TEXT = "Python Developer, Git, Docker, HTML, CSS, JavaScript, ReactJS, FastAPI, SQL."
else:
    print(f"File not found: {test_pdf}. Using default text.")
    RESUME_TEXT = (
        "Python Developer, Git, Docker, HTML, CSS, JavaScript, ReactJS, FastAPI, SQL."
    )

JOB_DESCRIPTION = """
Company : Real Tech
Job Summary
We are looking for an experienced Full Stack Developer with strong expertise in ReactJS, TypeScript, Python, FastAPI, and MongoDB. The ideal candidate should have hands-on experience in developing scalable web applications, designing RESTful APIs, and working on modern frontend and backend technologies.
Key Responsibilities
Design, develop, and maintain scalable full stack web applications.
Build responsive and interactive frontend applications using ReactJS and TypeScript.
Develop backend services and REST APIs using Python and FastAPI.
Work with MongoDB for database design, querying, and optimization.
Collaborate with UI/UX designers, QA teams, DevOps teams, and business stakeholders.
Write clean, reusable, and maintainable code following best practices.
Optimize application performance, scalability, and security.
Participate in code reviews, sprint planning, and Agile development activities.
Troubleshoot and resolve application issues and bugs.
Mandatory Skills
ReactJS
TypeScript
Python
FastAPI
MongoDB
Secondary Skills
REST API Development
HTML5
CSS3
JavaScript (ES6+)
State Management (Redux/Context API)
Git/GitHub
Additional Skills
Docker & Kubernetes
CI/CD Pipelines
AWS / Azure / GCP
Agile/Scrum
Unit Testing Frameworks
Required Qualifications
Bachelor’s degree in Computer Science, IT, or related field.
Strong understanding of frontend and backend architecture.
Experience in developing scalable enterprise applications.
Good analytical, debugging, and problem-solving skills.
Strong communication and teamwork abilities.
Preferred Qualifications
Experience with Microservices architecture.
Exposure to cloud-native application development.
Knowledge of application security and performance optimization.
"""

# =========================================================
# SKILL ALIASES
# =========================================================

SKILL_ALIASES = {
    "python": ["python"],
    "html": ["html"],
    "css": ["css"],
    "javascript": ["javascript", "js"],
    "react": ["react", "reactjs"],
    "tailwind": ["tailwind"],
    "bootstrap": ["bootstrap"],
    "sql": ["sql", "sql database"],
    "github": ["github", "git"],
    "fastapi": ["fastapi"],
    "docker": ["docker"],
    "rest api": ["rest api", "api"],
}
# 
METHODS = ["agile", "waterfall"]

# =========================================================
# NORMALIZE TEXT
# =========================================================

resume_lower = RESUME_TEXT.lower()
jd_lower = JOB_DESCRIPTION.lower()

# =========================================================
# HARD SKILL MATCHING
# =========================================================

matched_skills = []
missing_skills = []

for main_skill, aliases in SKILL_ALIASES.items():
    found = False
    for alias in aliases:
        if alias.lower() in resume_lower:
            found = True
            break
    if found:
        matched_skills.append(main_skill)
    else:
        missing_skills.append(main_skill)

skills_score = (len(matched_skills) / len(SKILL_ALIASES)) * 100

# =========================================================
# METHODOLOGY MATCH
# =========================================================

matched_methods = []
for method in METHODS:
    if method in resume_lower:
        matched_methods.append(method)

methods_score = (len(matched_methods) / len(METHODS)) * 100
missing_methods = list(set(METHODS) - set(matched_methods))

# =========================================================
# SEMANTIC SIMILARITY
# =========================================================

resume_embedding = model.encode([RESUME_TEXT])
jd_embedding = model.encode([JOB_DESCRIPTION])
semantic_similarity = cosine_similarity(resume_embedding, jd_embedding)[0][0]
semantic_score = semantic_similarity * 100

# =========================================================
# EDUCATION MATCH
# =========================================================

education_keywords = ["computer science", "b.e", "bachelor", "engineering", "bca"]
edu_matches = 0
for edu in education_keywords:
    if edu in resume_lower:
        edu_matches += 1

education_score = (edu_matches / len(education_keywords)) * 100

# =========================================================
# EXPERIENCE MATCH
# =========================================================

internship_count = resume_lower.count("intern")
years_match = re.search(r"(2|3|two|three)\s*(years|yrs)", resume_lower)

if years_match:
    experience_score = 100
elif internship_count >= 2:
    experience_score = 75
elif internship_count == 1:
    experience_score = 55
else:
    experience_score = 20

# =========================================================
# FINAL ATS SCORE (WEIGHTED)
# =========================================================

final_score = (
    (skills_score * 0.30)
    + (semantic_score * 0.40)
    + (experience_score * 0.20)
    + (education_score * 0.10)
)
final_score = round(final_score, 2)

# =========================================================
# FINAL RESULT
# =========================================================

results = {
    "Final ATS Score": f"{final_score}%",
    "Score Breakdown": {
        "Skills Match": f"{round(skills_score, 2)}%",
        "Semantic Similarity": f"{round(semantic_score, 2)}%",
        "Experience Match": f"{round(experience_score, 2)}%",
        "Education Match": f"{round(education_score, 2)}%",
        "Methodologies Match": f"{round(methods_score, 2)}%",
    },
    "Matched Skills": matched_skills,
    "Missing Skills": missing_skills,
    "Missing Methodologies": missing_methods,
    "Suggestions": [],
}

# Suggestions Logic
if missing_skills:
    results["Suggestions"].append(
        f"Add missing technical skills: {', '.join(missing_skills)}"
    )
if missing_methods:
    results["Suggestions"].append(f"Add methodologies: {', '.join(missing_methods)}")
if experience_score < 100:
    results["Suggestions"].append("Add more projects and internship experience")
if semantic_score < 80:
    results["Suggestions"].append("Improve resume alignment with job description")

# Display Result
print("\n========== ATS REPORT ==========\n")
print(json.dumps(results, indent=4))
print("\n================================\n")
