import os
import json
import dotenv
from google import genai
from google.genai import types
from Schemas.PosterSchemas import AiGenerationRequestSchema

dotenv.load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

def generate_job_post_content(request_data: AiGenerationRequestSchema) -> dict:
    job_details = request_data.JobDetails.model_dump()
    
    # Extract bot persona
    bot_persona = "You are an expert HR recruiter and ATS specialist."
    icon_type = "Bot"
    tone_override = None
    if request_data.AI_Model and len(request_data.AI_Model) > 0:
        bot_info = request_data.AI_Model[0]
        if hasattr(bot_info, 'Bot_Type') and bot_info.Bot_Type:
            bot_persona = f"You are an expert {bot_info.Bot_Type}."
        if hasattr(bot_info, 'Icon') and bot_info.Icon:
            icon_type = bot_info.Icon
        if hasattr(bot_info, 'Tone_Prompt') and bot_info.Tone_Prompt:
            tone_override = bot_info.Tone_Prompt
            
    # Extract tone dynamically based on Bot Icon Descriptor or db-stored prompt
    if tone_override:
        tone = tone_override
    else:
        tone = "Balanced Assistant (You are an expert HR recruiter and ATS specialist.)"
    
    # Fallback override if custom tone prompt is explicitly provided
    if request_data.AIMode and len(request_data.AIMode) > 0:
        tone = request_data.AIMode[0].Mode_Type
        if hasattr(request_data.AIMode[0], 'Prompt') and request_data.AIMode[0].Prompt:
            tone += f" ({request_data.AIMode[0].Prompt})"
            
    # Extract checklist features
    checklist_rules = []
    if request_data.SelectionCheckList:
        for cl in request_data.SelectionCheckList:
            if cl.enable:
                checklist_rules.append(f"- Include {cl.CheckList_Name}")
            else:
                checklist_rules.append(f"- DO NOT include {cl.CheckList_Name}")
                
    checklist_str = "\n".join(checklist_rules)

    prompt = f"""
{bot_persona}

Use this job data:
{json.dumps(job_details, indent=2)}

Generate TWO sections.

SECTION 1:
Create an attractive LinkedIn hiring post:
- Tone: {tone}
- Modern hiring style
{checklist_str}

SECTION 2:
Extract ATS keyword categories from the job description above.
Each category must be a flat list of individual keyword strings (no sentences).
Be thorough and specific.

Categories:
- technical_skills: All technical tools, languages, frameworks, platforms (e.g. "ReactJS", "Python", "FastAPI", "MongoDB")
- soft_skills: Interpersonal and behavioral traits (e.g. "communication", "teamwork", "problem-solving")
- education: List of accepted education qualifications as short keywords (e.g. "computer science", "bachelor", "b.tech", "mca")
- experience: List of experience-related keywords/phrases (e.g. "2 years", "3+ years", "senior level", "internship")
- abilities: Specific role abilities and competencies required (e.g. "REST API design", "agile methodology", "code review", "CI/CD", "unit testing")
- keywords: Other important domain keywords from the job description not covered above

Return format:

LINKEDIN_POST:
<content>

ATS_JSON:
```json
{{
   "technical_skills": [],
   "soft_skills": [],
   "education": [],
   "experience": [],
   "abilities": [],
   "keywords": []
}}
```
"""

    response = client.models.generate_content(
        model=os.getenv("MODEL"),
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level="HIGH"
            )
        )
    )

    response_text = response.text

    # Parse the response
    linkedin_post = ""
    ats_json_str = ""

    if "ATS_JSON:" in response_text:
        parts = response_text.split("ATS_JSON:")
        linkedin_post = parts[0].replace("LINKEDIN_POST:", "").strip()
        ats_json_raw = parts[1].strip()
        
        # Clean up markdown JSON block if present
        if ats_json_raw.startswith("```json"):
            ats_json_raw = ats_json_raw.replace("```json", "", 1)
        if ats_json_raw.endswith("```"):
            ats_json_raw = ats_json_raw.rsplit("```", 1)[0]
        
        ats_json_str = ats_json_raw.strip()
    else:
        linkedin_post = response_text.strip()

    try:
        ATS_Required_Skills = json.loads(ats_json_str) if ats_json_str else {}
    except json.JSONDecodeError:
        ATS_Required_Skills = {"error": "Could not parse JSON", "raw": ats_json_str}
        
    return {
        "linkedin_post": linkedin_post,
        "ats_requirements": ATS_Required_Skills
    }

if __name__ == "__main__":
    job_data_test = {
        "job_title": "React Developer",
        "company": "Tibos Technology",
        "experience": "3+ Years",
        "location": "Remote",
        "skills": [
            "React.js",
            "Node.js",
            "MongoDB",
            "REST API"
        ]
    }
    print(generate_job_post_content(job_data_test))