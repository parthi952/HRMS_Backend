from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

import module.RequirementDB as RequirementDB
import module.CandidateDB as CandidateDB
import Schemas.RequirementSchemas as RequirementSchemas
from database import get_db

router = APIRouter(prefix="/requirement", tags=["Requirement"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def create_requirement(
    req_in: RequirementSchemas.RequirementCreate, db: Session = Depends(get_db)
):
    try:
        # 1. Create the main Requirement record
        new_req = RequirementDB.Requirement(
            Temp_Id=req_in.Temp_Id,
            name=req_in.name,
            email=req_in.email,
            department=req_in.department,
            position=req_in.position,
            Resume=req_in.Resume
        )
        db.add(new_req)
        db.flush()  # Get new_req.id for foreign keys

        # 2. Add Marks Sheets
        for ms in req_in.marks_sheets:
            db.add(
                RequirementDB.RequirementMarksSheet(
                    requirement_id=new_req.id,
                    doc_type=ms.doc_type,
                    doc_id=ms.doc_id,
                    link=ms.link,
                    status=ms.status
                )
            )

        # 3. Add Assets
        for asset in req_in.assets:
            db.add(
                RequirementDB.RequirementAsset(
                    requirement_id=new_req.id,
                    ass_id=asset.ass_id,
                    Type=asset.Type,
                    Ass_name=asset.Ass_name,
                    status=asset.status,
                    Conditon=asset.Conditon,
                    handover_date=asset.handover_date
                )
            )

        # 4. Add Access
        for acc in req_in.access:
            db.add(
                RequirementDB.RequirementAccess(
                    requirement_id=new_req.id,
                    AccsesName=acc.AccsesName
                )
            )

        db.commit()
        return {"message": "Requirement created successfully", "id": new_req.id}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[RequirementSchemas.RequirementResponse])
def list_requirements(db: Session = Depends(get_db)):
    requirements = db.query(RequirementDB.Requirement).all()
    return requirements


@router.get("/eligible-candidates")
def get_eligible_candidates(db: Session = Depends(get_db)):
    """Fetch candidates who are 'Recruited' and ready for the Requirement process."""
    candidates = db.query(CandidateDB.Candidate).filter(
        CandidateDB.Candidate.Candidate_status == "Recruited"
    ).all()
    return candidates


@router.get("/{id}", response_model=RequirementSchemas.RequirementResponse)
def get_requirement(id: int, db: Session = Depends(get_db)):
    req = db.query(RequirementDB.Requirement).filter(RequirementDB.Requirement.id == id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return req


@router.put("/{id}")
def update_requirement(
    id: int,
    req_in: RequirementSchemas.RequirementCreate,
    db: Session = Depends(get_db)
):
    req = db.query(RequirementDB.Requirement).filter(RequirementDB.Requirement.id == id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    try:
        req.Temp_Id = req_in.Temp_Id
        req.name = req_in.name
        req.email = req_in.email
        req.department = req_in.department
        req.position = req_in.position
        req.Resume = req_in.Resume

        # For nested items, the easiest way (matching employee.py style) is delete and recreate
        db.query(RequirementDB.RequirementMarksSheet).filter_by(requirement_id=id).delete()
        db.query(RequirementDB.RequirementAsset).filter_by(requirement_id=id).delete()
        db.query(RequirementDB.RequirementAccess).filter_by(requirement_id=id).delete()

        # Re-add items
        for ms in req_in.marks_sheets:
            db.add(RequirementDB.RequirementMarksSheet(requirement_id=id, **ms.dict()))
        
        for asset in req_in.assets:
            db.add(RequirementDB.RequirementAsset(requirement_id=id, **asset.dict()))
            
        for acc in req_in.access:
            db.add(RequirementDB.RequirementAccess(requirement_id=id, **acc.dict()))

        db.commit()
        return {"message": "Requirement updated successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{id}")
def delete_requirement(id: int, db: Session = Depends(get_db)):
    req = db.query(RequirementDB.Requirement).filter(RequirementDB.Requirement.id == id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    
    try:
        db.delete(req)
        db.commit()
        return {"message": "Requirement deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
