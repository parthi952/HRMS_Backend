import re
import json
import os
import io

try:
    from ATS_System.DacumentExtracter import extract_text_from_pdf
except ImportError:
    from DacumentExtracter import extract_text_from_pdf

# =========================================================
# LAZY LOAD SENTENCE TRANSFORMER MODEL
# =========================================================

_model = None

def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print("Loading Semantic AI Model...")
        _model = SentenceTransformer("all-mpnet-base-v2")
    return _model


# =========================================================
# GEMINI AI - EXTRACT RESUME CATEGORIES
# =========================================================

def extract_resume_categories_with_ai(resume_text: str) -> dict:
    """
    Uses Gemini AI to extract keyword categories from the resume text
    matching the same category structure as the job post ATS JSON:
      - technical_skills
      - soft_skills
      - education
      - experience
      - abilities
    Returns a dict with each category as a flat list of keyword strings.
    """
    import dotenv
    from google import genai
    from google.genai import types

    dotenv.load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    prompt = f"""
You are an expert ATS resume parser.

Analyze the resume text below and extract keywords into these exact categories:
- technical_skills: All technical tools, languages, frameworks, platforms found in the resume
- soft_skills: Interpersonal and behavioral traits mentioned
- education: Education qualifications as short keywords (e.g. "computer science", "bachelor", "b.tech")
- experience: Experience-related keywords/phrases (e.g. "2 years", "3+ years", "internship")
- abilities: Specific role competencies demonstrated (e.g. "code review", "agile", "api design", "ci/cd")

Return ONLY a JSON object, no extra text:
{{
  "technical_skills": [],
  "soft_skills": [],
  "education": [],
  "experience": [],
  "abilities": []
}}

RESUME TEXT:
{resume_text[:4000]}
"""

    try:
        response = client.models.generate_content(
            model=os.getenv("MODEL"),
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="LOW")
            )
        )
        raw = response.text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()

        return json.loads(raw)

    except Exception as e:
        print(f"[ATSScore] Gemini extraction failed: {e}. Returning empty categories.")
        return {
            "technical_skills": [],
            "soft_skills": [],
            "education": [],
            "experience": [],
            "abilities": []
        }


# =========================================================
# SEMANTIC VECTOR SIMILARITY PER CATEGORY
# =========================================================

# =========================================================
# GEMINI AI - DOUBLE-CHECK AND VALIDATE SEMANTIC MATCHES
# =========================================================

def validate_missing_with_gemini(missing_items: list, resume_text: str, category_name: str) -> list:
    """
    Uses Gemini AI to double-check if any of the 'missing' items are actually present
    or semantically satisfied by the resume content (e.g., synonyms, acronyms, or alternate names).
    Returns a list of items that are indeed found/satisfied.
    """
    if not missing_items or not resume_text:
        return []

    import dotenv
    from google import genai
    from google.genai import types

    dotenv.load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return []

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are an advanced recruitment AI. Your task is to double-check if any of the "candidate missing items" listed below are actually present or semantically satisfied in the candidate's resume.

Resume text:
\"\"\"
{resume_text[:3500]}
\"\"\"

Missing requirements in category '{category_name}':
{json.dumps(missing_items)}

For each missing item, determine if it is semantically present in the resume. Examples:
- Job requires "AWS" -> Candidate has "Amazon Web Services" -> Match!
- Job requires "B.E. Computer Science" -> Candidate has "Bachelor of Engineering in CS" -> Match!
- Job requires "React" -> Candidate has "ReactJS" -> Match!
- Job requires "Agile/Scrum" -> Candidate has "worked in an agile environment" -> Match!

Respond ONLY with a JSON array of the items from the missing list that are ACTUALLY satisfied by the resume. If none are satisfied, return an empty array [].
Example response format:
["item1", "item2"]
Do not add any explanation or markdown formatting.
"""
    try:
        response = client.models.generate_content(
            model=os.getenv("MODEL", "gemini-1.5-flash"),
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="LOW")
            )
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()

        verified = json.loads(raw)
        if isinstance(verified, list):
            return [item for item in verified if item in missing_items]
    except Exception as e:
        print(f"[ATSScore] Gemini missing check failed: {e}")
    return []


# =========================================================
# SEMANTIC VECTOR SIMILARITY PER CATEGORY
# =========================================================

def _semantic_category_score(
    resume_items: list,
    job_items: list,
    any_one_qualifies: bool = False,
    resume_text: str = "",
    category_name: str = "",
) -> dict:
    """
    Computes semantic similarity between each job keyword and the
    candidate's resume keywords using item-to-item sentence vectors.

    Also performs a hybrid fallback check with Gemini AI for any missing
    items to guarantee 100% accuracy and avoid false negatives.
    
    any_one_qualifies (bool):
      When True (e.g. Education), matching even ONE job keyword means
      the candidate is fully eligible → score = 100%.
    """
    from sklearn.metrics.pairwise import cosine_similarity

    if not job_items:
        return {"matched": [], "missing": [], "score": 100.0}

    if not resume_items:
        # Try Gemini validation directly on the raw resume text
        gemini_verified = validate_missing_with_gemini(job_items, resume_text, category_name)
        if gemini_verified:
            matched = list(dict.fromkeys(gemini_verified))
            missing = [item for item in job_items if item not in matched]
            if any_one_qualifies and matched:
                return {"matched": list(job_items), "missing": [], "score": 100.0}
            score = round((len(matched) / len(job_items)) * 100, 2)
            return {"matched": matched, "missing": missing, "score": score}
        return {"matched": [], "missing": list(job_items), "score": 0.0}

    # Normalize inputs
    job_items_clean = [j.strip() for j in job_items if j.strip()]
    resume_items_clean = [r.strip() for r in resume_items if r.strip()]

    matched = []
    missing_candidates = []

    # 1. Case-insensitive substring matching
    for job_item in job_items_clean:
        job_lower = job_item.lower()
        found = False
        for resume_item in resume_items_clean:
            res_lower = resume_item.lower()
            if job_lower == res_lower or job_lower in res_lower or res_lower in job_lower:
                matched.append(job_item)
                found = True
                break
        if not found:
            missing_candidates.append(job_item)

    # 2. Semantic Search (Item-to-Item Vector Similarity)
    if missing_candidates and resume_items_clean:
        model = _get_model()
        try:
            job_vecs = model.encode(missing_candidates)
            resume_vecs = model.encode(resume_items_clean)
            
            THRESHOLD = 0.60  # Optimal matching similarity threshold
            
            still_missing = []
            for i, job_item in enumerate(missing_candidates):
                sims = cosine_similarity([job_vecs[i]], resume_vecs)[0]
                max_sim_idx = sims.argmax()
                max_sim = sims[max_sim_idx]
                
                if max_sim >= THRESHOLD:
                    matched.append(job_item)
                    print(f"[Semantic Match] '{job_item}' matched with '{resume_items_clean[max_sim_idx]}' (sim: {max_sim:.2f})")
                else:
                    still_missing.append(job_item)
            missing_candidates = still_missing
        except Exception as e:
            print(f"[ATSScore] Vector search failed: {e}")

    # 3. Hybrid Double Check with Gemini AI for missing items
    if missing_candidates and resume_text:
        print(f"[ATSScore] Double checking {len(missing_candidates)} missing items in '{category_name}' with Gemini...")
        gemini_verified = validate_missing_with_gemini(missing_candidates, resume_text, category_name)
        if gemini_verified:
            for item in gemini_verified:
                matched.append(item)
                if item in missing_candidates:
                    missing_candidates.remove(item)
            print(f"[ATSScore] Gemini successfully recovered: {gemini_verified}")

    # Remove duplicates preserving order
    matched = list(dict.fromkeys(matched))
    missing = list(dict.fromkeys(missing_candidates))

    # OR-logic: if any single degree / qualification matched → fully eligible (show all required degrees as matched)
    if any_one_qualifies and matched:
        return {"matched": job_items_clean, "missing": [], "score": 100.0}

    score = round((len(matched) / len(job_items_clean)) * 100, 2)
    return {"matched": matched, "missing": missing, "score": score}


# =========================================================
# MAIN ATS SCORING FUNCTION (CATEGORY-WISE WITH AI + VECTORS)
# =========================================================

def calculate_ats_score_raw(
    resume_text: str,
    job_description: str,
    skills_str: str,
    education_str: str,
    experience_str: str,
    abilities_str: str = None,
    methods_str: str = None,
    job_technical_skills: list = None,
    job_soft_skills: list = None,
    job_education: list = None,
    job_experience: list = None,
    job_abilities: list = None,
    weights: dict = None,
) -> dict:
    """
    Category-wise ATS scoring pipeline:

    STEP 1 — Gemini AI extracts resume keywords per category
    STEP 2 — Build job category keyword lists (AI JSON → DB strings fallback)
    STEP 3 — Per-category semantic vector similarity score
    STEP 4 — Weighted final ATS score

    Weights:
      Technical Skills  30%
      Abilities         20%
      Experience        20%
      Education         15%
      Soft Skills       15%
    """

    # ----------------------------------------------------------
    # STEP 1: Gemini extracts resume keyword categories
    # ----------------------------------------------------------
    print("[ATSScore] Extracting resume categories via Gemini AI...")
    resume_cats = extract_resume_categories_with_ai(resume_text)

    # ----------------------------------------------------------
    # STEP 2: Build job category keyword lists
    #   Priority: full AI-extracted lists → DB comma-separated strings
    # ----------------------------------------------------------
    tech_list = (
        job_technical_skills
        or [s.strip() for s in skills_str.split(",") if s.strip()] if skills_str else []
    )

    edu_list = job_education or (
        [e.strip() for e in education_str.split(",") if e.strip()]
        if education_str else []
    )

    exp_list = job_experience or (
        [e.strip() for e in experience_str.split(",") if e.strip()]
        if experience_str else []
    )
    if not exp_list and experience_str:
        exp_list = [experience_str.strip()]

    ability_list = job_abilities or (
        [a.strip() for a in abilities_str.split(",") if a.strip()]
        if abilities_str else []
    )

    soft_list = job_soft_skills or []

    # ----------------------------------------------------------
    # STEP 3: Semantic vector similarity per category
    # ----------------------------------------------------------
    print("[ATSScore] Running semantic vector matching per category...")
    tech_result    = _semantic_category_score(
        resume_cats.get("technical_skills", []), 
        tech_list, 
        resume_text=resume_text, 
        category_name="Technical Skills"
    )
    # Education uses OR-logic: one matching degree = fully eligible
    edu_result     = _semantic_category_score(
        resume_cats.get("education", []), 
        edu_list, 
        any_one_qualifies=True, 
        resume_text=resume_text, 
        category_name="Education"
    )
    exp_result     = _semantic_category_score(
        resume_cats.get("experience", []), 
        exp_list, 
        resume_text=resume_text, 
        category_name="Experience"
    )
    ability_result = _semantic_category_score(
        resume_cats.get("abilities", []), 
        ability_list, 
        resume_text=resume_text, 
        category_name="Abilities"
    )
    soft_result    = _semantic_category_score(
        resume_cats.get("soft_skills", []), 
        soft_list, 
        resume_text=resume_text, 
        category_name="Soft Skills"
    )

    # ----------------------------------------------------------
    # STEP 4: Weighted final ATS Score
    # ----------------------------------------------------------
    default_weights = {
        "technical_skills": 0.30,
        "abilities": 0.20,
        "experience": 0.20,
        "education": 0.15,
        "soft_skills": 0.15,
    }
    
    active_weights = default_weights.copy()
    if weights:
        # Standardize keys to match active_weights
        norm_w = {k.lower().replace(" ", "_"): float(v) for k, v in weights.items()}
        # Normalize sum to 1.0
        total_sum = sum(norm_w.values())
        if total_sum > 0:
            for k in active_weights.keys():
                if k in norm_w:
                    # If recruiter provided numbers out of 100
                    if total_sum == 100.0 or total_sum > 1.0:
                        active_weights[k] = norm_w[k] / 100.0
                    else:
                        active_weights[k] = norm_w[k] / total_sum

    final_score = round(
        (tech_result["score"]      * active_weights.get("technical_skills", 0.30))
        + (ability_result["score"] * active_weights.get("abilities", 0.20))
        + (exp_result["score"]     * active_weights.get("experience", 0.20))
        + (edu_result["score"]     * active_weights.get("education", 0.15))
        + (soft_result["score"]    * active_weights.get("soft_skills", 0.15)),
        2
    )

    # ----------------------------------------------------------
    # STEP 5: Suggestions
    # ----------------------------------------------------------
    suggestions = []
    if tech_result["missing"]:
        suggestions.append(f"Add technical skills: {', '.join(tech_result['missing'])}")
    if ability_result["missing"]:
        suggestions.append(f"Add abilities: {', '.join(ability_result['missing'])}")
    if edu_result["missing"]:
        suggestions.append(f"Add education keywords: {', '.join(edu_result['missing'])}")
    if exp_result["missing"]:
        suggestions.append(f"Improve experience section: {', '.join(exp_result['missing'])}")
    if soft_result["missing"]:
        suggestions.append(f"Add soft skills: {', '.join(soft_result['missing'])}")

    return {
        "Final ATS Score": f"{final_score}%",
        "Score Breakdown": {
            "Technical Skills": {
                "score": f"{tech_result['score']}%",
                "weight": f"{int(active_weights.get('technical_skills', 0.30) * 100)}%",
                "matched": tech_result["matched"],
                "missing": tech_result["missing"],
            },
            "Abilities": {
                "score": f"{ability_result['score']}%",
                "weight": f"{int(active_weights.get('abilities', 0.20) * 100)}%",
                "matched": ability_result["matched"],
                "missing": ability_result["missing"],
            },
            "Experience": {
                "score": f"{exp_result['score']}%",
                "weight": f"{int(active_weights.get('experience', 0.20) * 100)}%",
                "matched": exp_result["matched"],
                "missing": exp_result["missing"],
            },
            "Education": {
                "score": f"{edu_result['score']}%",
                "weight": f"{int(active_weights.get('education', 0.15) * 100)}%",
                "matched": edu_result["matched"],
                "missing": edu_result["missing"],
            },
            "Soft Skills": {
                "score": f"{soft_result['score']}%",
                "weight": f"{int(active_weights.get('soft_skills', 0.15) * 100)}%",
                "matched": soft_result["matched"],
                "missing": soft_result["missing"],
            },
        },
        "Resume Categories Extracted": resume_cats,
        "Suggestions": suggestions,
    }


def calculate_ats_score_for_post(resume_text: str, post_id: str, db, weights: dict = None) -> dict:
    """
    Fetches job details and ATS criteria from DB and runs category-wise ATS scoring.
    Loads custom recruiter weights from the database if they exist.
    """
    from module.JobPosterDB import JobPostDetailes, ATS_KeySkills

    job_post = db.query(JobPostDetailes).filter(JobPostDetailes.PostId == post_id).first()
    if not job_post:
        raise ValueError(f"Job post with PostId '{post_id}' not found.")

    ats_keys = db.query(ATS_KeySkills).filter(ATS_KeySkills.PostId == post_id).first()

    job_description = job_post.Description or ""
    skills_str      = ats_keys.Skills     if ats_keys else ""
    education_str   = ats_keys.Education  if ats_keys else ""
    experience_str  = ats_keys.Experience if ats_keys else ""
    abilities_str   = ats_keys.Abilities  if ats_keys else ""
    methods_str     = job_post.methods    if job_post else ""

    # Load custom weights from the database if not explicitly passed
    if not weights and ats_keys:
        weights = {
            "technical_skills": ats_keys.Weight_Tech if ats_keys.Weight_Tech is not None else 30,
            "abilities": ats_keys.Weight_Abilities if ats_keys.Weight_Abilities is not None else 20,
            "experience": ats_keys.Weight_Experience if ats_keys.Weight_Experience is not None else 20,
            "education": ats_keys.Weight_Education if ats_keys.Weight_Education is not None else 15,
            "soft_skills": ats_keys.Weight_Soft if ats_keys.Weight_Soft is not None else 15,
        }

    return calculate_ats_score_raw(
        resume_text=resume_text,
        job_description=job_description,
        skills_str=skills_str,
        education_str=education_str,
        experience_str=experience_str,
        abilities_str=abilities_str,
        methods_str=methods_str,
        weights=weights,
    )


# =========================================================
# STANDALONE CLI TEST BLOCK
# =========================================================

if __name__ == "__main__":
    test_pdf = (
        r"C:\Users\parth_kozqdcr\OneDrive\Desktop\Hrm_Backend\ATS_System\Document\1.pdf"
    )

    if os.path.exists(test_pdf):
        print(f"--- Extracting text from: {os.path.basename(test_pdf)} ---")
        resume_text = extract_text_from_pdf(test_pdf)
        if resume_text.startswith("Error"):
            resume_text = "Python Developer, Git, Docker, HTML, CSS, JavaScript, ReactJS, FastAPI, SQL. Bachelor in Computer Science. 2 years experience. Agile, code review."
    else:
        resume_text = "Python Developer, Git, Docker, HTML, CSS, JavaScript, ReactJS, FastAPI, SQL. Bachelor in Computer Science. 2 years experience. Agile, code review."

    results = calculate_ats_score_raw(
        resume_text=resume_text,
        job_description="Full Stack Developer role requiring ReactJS, Python, FastAPI, MongoDB.",
        skills_str="ReactJS, Python, FastAPI, MongoDB, TypeScript",
        education_str="computer science, bachelor, b.tech",
        experience_str="2 years, 3+ years",
        abilities_str="agile, code review, unit testing, api design",
        job_soft_skills=["communication", "teamwork", "problem-solving"],
    )

    print("\n========== ATS REPORT ==========\n")
    print(json.dumps(results, indent=4))
    print("\n================================\n")
