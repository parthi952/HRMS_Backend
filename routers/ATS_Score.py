from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import io
import pdfplumber
import uuid

from database import get_db
import module.CandidateDB as CandidateDB
from module.JobPosterDB import ATS_KeySkills
from module.ATSScoreDB import CandidateATSScore
from Schemas.PosterSchemas import ATS_PostSchema
from ATS_System.ATSScore import calculate_ats_score_for_post
import requests

router = APIRouter(
    prefix="/ats_score",
    tags=["ATS Score"]
)

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        return f"Error opening PDF: {e}"
    return text

def download_blob_to_bytes(blob_name: str) -> bytes:
    try:
        response = requests.get(blob_name)
        response.raise_for_status()
        return response.content
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error downloading resume from storage: {str(e)}"
        )

@router.post("/calculate/candidate", status_code=status.HTTP_200_OK)
def calculate_candidate_ats_score(
    candidate_id: int,
    post_id: str,
    db: Session = Depends(get_db)
):
    """
    Calculates the ATS Score for an existing candidate's resume from storage
    against a specific job posting's keywords and details.
    """
    # 1. Fetch Candidate
    candidate = db.query(CandidateDB.Candidate).filter(CandidateDB.Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate with ID {candidate_id} not found.")
    
    if not candidate.Resume_path:
        raise HTTPException(status_code=400, detail="Candidate does not have a resume uploaded.")
        
    # 2. Download resume and extract text
    pdf_bytes = download_blob_to_bytes(candidate.Resume_path)
    resume_text = extract_text_from_pdf_bytes(pdf_bytes)
    
    if resume_text.startswith("Error"):
        raise HTTPException(status_code=400, detail=f"Failed to extract text from resume: {resume_text}")
        
    # 3. Calculate Score and persist
    try:
        score_details = calculate_ats_score_for_post(resume_text, post_id, db)
        breakdown = score_details.get("Score Breakdown", {})

        def _score(key):
            return float(breakdown.get(key, {}).get("score", "0%").replace("%", ""))

        def _joined(key, field):
            return ", ".join(breakdown.get(key, {}).get(field, []))

        ats_record = CandidateATSScore(
            candidate_id=candidate.id,
            Candidate_name=candidate.Candidate_name,
            PostId=post_id,
            final_score=float(score_details["Final ATS Score"].replace("%", "")),
            skills_score=_score("Technical Skills"),
            semantic_score=_score("Soft Skills"),
            experience_score=_score("Experience"),
            education_score=_score("Education"),
            methodologies_score=_score("Abilities"),
            matched_skills=_joined("Technical Skills", "matched"),
            missing_skills=_joined("Technical Skills", "missing"),
            suggestions=", ".join(score_details.get("Suggestions", [])),
        )
        db.add(ats_record)

        # Auto change active stage (e.g. screening/applied) to Completed
        active_cs = db.query(CandidateDB.CandidateStage).filter(
            CandidateDB.CandidateStage.candidate_id == candidate.id,
            CandidateDB.CandidateStage.Stage_status == "In Progress"
        ).first()
        if active_cs:
            active_cs.Stage_status = "Completed"
            
            # Also find and complete the corresponding scheduled interview for this stage
            active_inv = db.query(CandidateDB.Interview).filter(
                CandidateDB.Interview.candidate_id == candidate.id,
                CandidateDB.Interview.stage_id == active_cs.stage_id,
                CandidateDB.Interview.Interview_status == "Scheduled"
            ).first()
            if active_inv:
                active_inv.Interview_status = "Completed"

        db.commit()
        db.refresh(ats_record)

        return {"candidate_id": candidate_id, "post_id": post_id, "score_id": ats_record.id, "results": score_details}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate/file", status_code=status.HTTP_200_OK)
async def calculate_uploaded_file_ats_score(
    post_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Calculates the ATS Score on-the-fly for an uploaded PDF resume
    against a specific job posting's keywords and details.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF resumes are supported.")
        
    # 1. Read file bytes and extract text
    try:
        pdf_bytes = await file.read()
        resume_text = extract_text_from_pdf_bytes(pdf_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")
        
    if resume_text.startswith("Error"):
        raise HTTPException(status_code=400, detail=f"Failed to extract text from resume: {resume_text}")
        
    # 2. Calculate Score (file upload — no candidate record to persist)
    try:
        score_details = calculate_ats_score_for_post(resume_text, post_id, db)
        return {"filename": file.filename, "post_id": post_id, "results": score_details}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/keyskills/{post_id}", status_code=status.HTTP_200_OK)
def get_ats_keyskills_by_post(post_id: str, db: Session = Depends(get_db)):
    """
    Retrieves the ATS KeySkills configuration for a specific job post by its PostId.
    """
    item = db.query(ATS_KeySkills).filter(ATS_KeySkills.PostId == post_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ATS KeySkills for Job Post {post_id} not found."
        )
    return {"message": "ATS KeySkills fetched successfully", "data": item}

@router.post("/keyskills", status_code=status.HTTP_200_OK)
def upsert_ats_keyskills(request: ATS_PostSchema, db: Session = Depends(get_db)):
    """
    Creates or updates the ATS KeySkills configuration for a job post by its PostId.
    """
    # Check if keyskills already exist for this PostId
    item = db.query(ATS_KeySkills).filter(ATS_KeySkills.PostId == request.PostId).first()
    
    try:
        if item:
            # Update existing
            item.Title = request.Title
            item.Skills = request.Skills
            item.Education = request.Education
            item.Experience = request.Experience
            item.Abilities = request.Abilities
            message = "ATS KeySkills updated successfully"
        else:
            # Create new
            item = ATS_KeySkills(
                id=str(uuid.uuid4()),
                **request.model_dump()
            )
            db.add(item)
            message = "ATS KeySkills created successfully"
            
        db.commit()
        db.refresh(item)
        return {"message": message, "data": item}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/candidate/{candidate_id}", status_code=200)
def get_candidate_ats_score(candidate_id: int, db: Session = Depends(get_db)):
    score = db.query(CandidateATSScore).filter(CandidateATSScore.candidate_id == candidate_id).order_by(CandidateATSScore.scored_at.desc()).first()
    if not score:
        return {"has_score": False, "message": "No score calculated yet for this candidate."}
    return {
        "has_score": True,
        "final_score": score.final_score,
        "skills_score": score.skills_score,
        "semantic_score": score.semantic_score,
        "experience_score": score.experience_score,
        "education_score": score.education_score,
        "methodologies_score": score.methodologies_score,
        "matched_skills": score.matched_skills,
        "missing_skills": score.missing_skills,
        "suggestions": score.suggestions,
        "scored_at": score.scored_at,
        "PostId": score.PostId
    }
