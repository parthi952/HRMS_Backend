from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from datetime import date as today_date

from database import get_db
from module.JobPosterDB import JobPostDetailes, ATS_KeySkills, AiJobPost, education_Options, AI_Model, AIMode, SelectionCheckList
from Schemas.PosterSchemas import (
    PostingSchema_create, AiGenerationRequestSchema, ATS_PostSchema, AiJobPostSchema,
    education_OptionsSchema, AI_ModelSchema, AIModeSchema, SelectionCheckListSchema
)
from JobPost.ContentGenarete import generate_job_post_content

router = APIRouter(
    prefix="/jobpost",
    tags=["Job Post"]
)

# Automated startup migrations for new columns
try:
    from database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        for col in [
            "ALTER TABLE jobpost_detailes ADD COLUMN location VARCHAR;",
            "ALTER TABLE jobpost_detailes ADD COLUMN expire_date DATE;",
            "ALTER TABLE jobpost_detailes ADD COLUMN interview_date DATE;",
            "ALTER TABLE jobpost_detailes ADD COLUMN is_active BOOLEAN DEFAULT TRUE;",
            "ALTER TABLE ats_keyskills ADD COLUMN Weight_Tech INTEGER DEFAULT 30;",
            "ALTER TABLE ats_keyskills ADD COLUMN Weight_Abilities INTEGER DEFAULT 20;",
            "ALTER TABLE ats_keyskills ADD COLUMN Weight_Experience INTEGER DEFAULT 20;",
            "ALTER TABLE ats_keyskills ADD COLUMN Weight_Education INTEGER DEFAULT 15;",
            "ALTER TABLE ats_keyskills ADD COLUMN Weight_Soft INTEGER DEFAULT 15;",
        ]:
            try:
                conn.execute(text(col))
                conn.commit()
            except Exception:
                conn.rollback()
except Exception:
    pass

# === AI GENERATION ENDPOINT ===
@router.post("/generate", status_code=status.HTTP_200_OK)
def generate_job_post(request: AiGenerationRequestSchema, db: Session = Depends(get_db)):
    try:
        result = generate_job_post_content(request)
        
        # 1. Save to AiJobPost
        new_ai_job_post = AiJobPost(
            id=str(uuid.uuid4()),
            PostId=request.JobDetails.PostId,
            Title=request.JobDetails.title,
            Poster=result.get("linkedin_post", "")
        )
        db.add(new_ai_job_post)
        
        # 2. Save to ATS_KeySkills
        req = result.get("ats_requirements", {})
        
        skills_list = req.get("technical_skills", []) + req.get("soft_skills", [])
        skills_str = ", ".join(skills_list) if isinstance(skills_list, list) else str(skills_list)
        
        education_str = req.get("education", "")
        experience_str = req.get("experience", "")
        
        abilities_list = req.get("important_abilities", [])
        abilities_str = ", ".join(abilities_list) if isinstance(abilities_list, list) else str(abilities_list)
        
        new_ats_skills = ATS_KeySkills(
            id=str(uuid.uuid4()),
            PostId=request.JobDetails.PostId,
            Title=request.JobDetails.title,
            Skills=skills_str,
            Education=education_str,
            Experience=experience_str,
            Abilities=abilities_str
        )
        db.add(new_ats_skills)
        
        db.commit()
        
        return {"message": "Content generated and saved successfully", "data": result}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# === CRUD FOR JobPostDetailes ===
@router.post("/details/create", status_code=status.HTTP_201_CREATED)
def create_job_post_details(request: PostingSchema_create, db: Session = Depends(get_db)):
    try:
        # Extract Weight values for ATS_KeySkills to avoid database mismatches
        req_data = request.model_dump()
        weight_keys = ["Weight_Tech", "Weight_Abilities", "Weight_Experience", "Weight_Education", "Weight_Soft"]
        weight_values = {k: req_data.pop(k, None) for k in weight_keys}

        new_post = JobPostDetailes(id=str(uuid.uuid4()), **req_data)
        db.add(new_post)
        db.flush()

        # Create corresponding ATS KeySkills entry
        new_ats = ATS_KeySkills(
            id=str(uuid.uuid4()),
            PostId=new_post.PostId,
            Title=new_post.title,
            Skills=new_post.stack or "",
            Education=new_post.education or "",
            Experience=new_post.experience or "",
            Abilities=new_post.methods or "",
            Weight_Tech=weight_values.get("Weight_Tech") if weight_values.get("Weight_Tech") is not None else 30,
            Weight_Abilities=weight_values.get("Weight_Abilities") if weight_values.get("Weight_Abilities") is not None else 20,
            Weight_Experience=weight_values.get("Weight_Experience") if weight_values.get("Weight_Experience") is not None else 20,
            Weight_Education=weight_values.get("Weight_Education") if weight_values.get("Weight_Education") is not None else 15,
            Weight_Soft=weight_values.get("Weight_Soft") if weight_values.get("Weight_Soft") is not None else 15,
        )
        db.add(new_ats)
        db.commit()
        db.refresh(new_post)
        return {"message": "Job Post created successfully", "data": new_post}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/details/all", status_code=status.HTTP_200_OK)
def get_job_posts(db: Session = Depends(get_db)):
    items = db.query(JobPostDetailes).all()
    today = today_date.today()
    changed = False
    for item in items:
        # Auto-expire: if expire_date is set and passed, deactivate
        if item.expire_date and item.expire_date < today and item.is_active:
            item.is_active = False
            changed = True
    if changed:
        db.commit()
    return {"message": "Job Posts fetched successfully", "data": items}

@router.put("/details/{post_id}", status_code=status.HTTP_200_OK)
def update_job_post_details(post_id: str, request: PostingSchema_create, db: Session = Depends(get_db)):
    try:
        post = db.query(JobPostDetailes).filter(JobPostDetailes.PostId == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Job Post not found")
        
        for key, value in request.model_dump().items():
            setattr(post, key, value)

        # Re-evaluate is_active based on new expire_date
        if post.expire_date and post.expire_date < today_date.today():
            post.is_active = False

        db.commit()
        db.refresh(post)
        return {"message": "Job Post updated successfully", "data": post}
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/details/{post_id}/toggle", status_code=status.HTTP_200_OK)
def toggle_job_post_active(post_id: str, db: Session = Depends(get_db)):
    """Manually toggle is_active for a job post."""
    post = db.query(JobPostDetailes).filter(JobPostDetailes.PostId == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Job Post not found")
    post.is_active = not post.is_active
    db.commit()
    db.refresh(post)
    return {"message": f"Job Post is now {'active' if post.is_active else 'inactive'}", "is_active": post.is_active}



# === CRUD FOR ATS_KeySkills ===
@router.post("/ats_keyskills/create", status_code=status.HTTP_201_CREATED)
def create_ats_keyskills(request: ATS_PostSchema, db: Session = Depends(get_db)):
    try:
        new_item = ATS_KeySkills(id=str(uuid.uuid4()), **request.model_dump())
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return {"message": "ATS KeySkills created successfully", "data": new_item}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ats_keyskills/all", status_code=status.HTTP_200_OK)
def get_ats_keyskills(db: Session = Depends(get_db)):
    items = db.query(ATS_KeySkills).all()
    return {"message": "ATS KeySkills fetched successfully", "data": items}

@router.put("/ats_keyskills/{post_id}", status_code=status.HTTP_200_OK)
def update_ats_keyskills(post_id: str, request: ATS_PostSchema, db: Session = Depends(get_db)):
    try:
        item = db.query(ATS_KeySkills).filter(ATS_KeySkills.PostId == post_id).first()
        if not item:
            # Create a new one if it doesn't exist
            new_item = ATS_KeySkills(id=str(uuid.uuid4()), **request.model_dump())
            db.add(new_item)
            db.commit()
            db.refresh(new_item)
            return {"message": "ATS KeySkills created successfully", "data": new_item}
        
        for key, value in request.model_dump().items():
            if key != "id" and key != "PostId":
                setattr(item, key, value)
        
        db.commit()
        db.refresh(item)
        return {"message": "ATS KeySkills updated successfully", "data": item}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# === CRUD FOR AiJobPost ===
@router.post("/ai_job_post/create", status_code=status.HTTP_201_CREATED)
def create_ai_job_post(request: AiJobPostSchema, db: Session = Depends(get_db)):
    try:
        new_item = AiJobPost(id=str(uuid.uuid4()), **request.model_dump())
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return {"message": "AI Job Post created successfully", "data": new_item}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ai_job_post/all", status_code=status.HTTP_200_OK)
def get_ai_job_posts(db: Session = Depends(get_db)):
    items = db.query(AiJobPost).all()
    return {"message": "AI Job Posts fetched successfully", "data": items}


# === CRUD FOR education_Options ===
@router.post("/education/create", status_code=status.HTTP_201_CREATED)
def create_education_option(request: education_OptionsSchema, db: Session = Depends(get_db)):
    try:
        new_item = education_Options(id=str(uuid.uuid4()), **request.model_dump())
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return {"message": "Education Option created successfully", "data": new_item}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/education/all", status_code=status.HTTP_200_OK)
def get_education_options(db: Session = Depends(get_db)):
    items = db.query(education_Options).all()
    return {"data": items}


# === CRUD FOR AI_Model ===
@router.post("/aimodel/create", status_code=status.HTTP_201_CREATED)
def create_aimodel(request: AI_ModelSchema, db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text
        db.execute(text("ALTER TABLE ai_model ADD COLUMN \"Tone_Prompt\" VARCHAR;"))
        db.commit()
    except Exception:
        db.rollback()
    try:
        from sqlalchemy import text
        db.execute(text("ALTER TABLE ai_model ADD COLUMN \"Tone_Id\" VARCHAR;"))
        db.commit()
    except Exception:
        db.rollback()
    try:
        data = request.model_dump()
        if not data.get("Tone_Id") or data.get("Tone_Id") == "":
            data["Tone_Id"] = None
        new_item = AI_Model(id=str(uuid.uuid4()), **data)
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return {"message": "AI Model created successfully", "data": new_item}
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/aimodel/all", status_code=status.HTTP_200_OK)
def get_aimodels(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text
        db.execute(text("ALTER TABLE ai_model ADD COLUMN \"Tone_Prompt\" VARCHAR;"))
        db.commit()
    except Exception:
        db.rollback()
    try:
        from sqlalchemy import text
        db.execute(text("ALTER TABLE ai_model ADD COLUMN \"Tone_Id\" VARCHAR;"))
        db.commit()
    except Exception:
        db.rollback()
    items = db.query(AI_Model).all()
    return {"data": items}


# === CRUD FOR AIMode ===
@router.post("/aimode/create", status_code=status.HTTP_201_CREATED)
def create_aimode(request: AIModeSchema, db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text
        db.execute(text("ALTER TABLE ai_mode ADD COLUMN \"Icon\" VARCHAR;"))
        db.commit()
    except Exception:
        db.rollback()
    try:
        data = request.model_dump()
        if not data.get("model_id") or data.get("model_id") == "":
            data["model_id"] = None
        new_item = AIMode(id=str(uuid.uuid4()), **data)
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return {"message": "AI Mode created successfully", "data": new_item}
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/aimode/all", status_code=status.HTTP_200_OK)
def get_aimodes(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text
        db.execute(text("ALTER TABLE ai_mode ADD COLUMN \"Icon\" VARCHAR;"))
        db.commit()
    except Exception:
        db.rollback()
    items = db.query(AIMode).all()
    return {"data": items}


# === CRUD FOR SelectionCheckList ===
@router.post("/checklist/create", status_code=status.HTTP_201_CREATED)
def create_checklist(request: SelectionCheckListSchema, db: Session = Depends(get_db)):
    try:
        data = request.model_dump()
        if not data.get("model_id") or data.get("model_id") == "":
            data["model_id"] = None
        new_item = SelectionCheckList(id=str(uuid.uuid4()), **data)
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return {"message": "SelectionCheckList created successfully", "data": new_item}
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/checklist/all", status_code=status.HTTP_200_OK)
def get_checklists(db: Session = Depends(get_db)):
    items = db.query(SelectionCheckList).all()
    return {"data": items}


# === DELETE ENDPOINTS ===
@router.delete("/education/{item_id}", status_code=status.HTTP_200_OK)
def delete_education(item_id: str, db: Session = Depends(get_db)):
    item = db.query(education_Options).filter(education_Options.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(item)
    db.commit()
    return {"message": "Deleted"}

@router.delete("/aimodel/{item_id}", status_code=status.HTTP_200_OK)
def delete_aimodel(item_id: str, db: Session = Depends(get_db)):
    item = db.query(AI_Model).filter(AI_Model.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(item)
    db.commit()
    return {"message": "Deleted"}

@router.delete("/aimode/{item_id}", status_code=status.HTTP_200_OK)
def delete_aimode(item_id: str, db: Session = Depends(get_db)):
    item = db.query(AIMode).filter(AIMode.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(item)
    db.commit()
    return {"message": "Deleted"}

@router.delete("/checklist/{item_id}", status_code=status.HTTP_200_OK)
def delete_checklist(item_id: str, db: Session = Depends(get_db)):
    item = db.query(SelectionCheckList).filter(SelectionCheckList.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(item)
    db.commit()
    return {"message": "Deleted"}