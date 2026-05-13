from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
import module.CandidateDB as CandidateDB
import Schemas.CandidateSchemas as CandidateSchemas

router = APIRouter(prefix="/candidates", tags=["Candidates"])

# --- Helper Functions ---


def get_current_stage(db: Session, candidate_id: int):
    """Calculates current stage from CandidateStage table"""
    current = (
        db.query(CandidateDB.CandidateStage)
        .filter(
            CandidateDB.CandidateStage.candidate_id == candidate_id,
            CandidateDB.CandidateStage.Stage_status == "In Progress",
        )
        .first()
    )
    if current and current.stage:
        return current.stage.Stage_name
    return "Applied"


# --- Stage Master Endpoints ---


@router.post("/stages/master", response_model=CandidateSchemas.StageResponse)
def create_stage(stage_in: CandidateSchemas.StageBase, db: Session = Depends(get_db)):
    db_stage = CandidateDB.Stage(**stage_in.dict())
    db.add(db_stage)
    db.commit()
    db.refresh(db_stage)
    return db_stage


@router.get("/stages/master", response_model=List[CandidateSchemas.StageResponse])
def get_all_stages(db: Session = Depends(get_db)):
    return db.query(CandidateDB.Stage).order_by(CandidateDB.Stage.Stage_index).all()


# --- Candidate CRUD ---


@router.post("/Register", status_code=status.HTTP_201_CREATED)
def create_candidate(
    candidate_in: CandidateSchemas.CandidateCreate, db: Session = Depends(get_db)
):
    try:
        # 1. Generate internal ID code (e.g. CAN-0001)
        from Caluclation.IdCustom import generate_next_candidate_id

        new_code = generate_next_candidate_id(db)

        # 2. Create Candidate
        db_candidate = CandidateDB.Candidate(
            Candidate_ID=new_code, Candidate_status="Applied", **candidate_in.dict()
        )
        db.add(db_candidate)
        db.flush()  # Get ID

        # 3. Find First Stage from Master
        first_stage_master = (
            db.query(CandidateDB.Stage).order_by(CandidateDB.Stage.Stage_index).first()
        )

        if not first_stage_master:
            raise HTTPException(400, "No recruitment stages configured in Stage Master")

        # 4. Create first CandidateStage (In Progress)
        new_candidate_stage = CandidateDB.CandidateStage(
            candidate_id=db_candidate.id,
            stage_id=first_stage_master.id,
            Stage_status="In Progress",
        )
        db.add(new_candidate_stage)

        # 5. Create first Interview
        new_interview = CandidateDB.Interview(
            candidate_id=db_candidate.id,
            stage_id=first_stage_master.id,
            Interview_status="Scheduled",
        )
        db.add(new_interview)

        db.commit()
        return {
            "message": "Candidate registered and screening round created",
            "Candidate_ID": new_code,
            "id": db_candidate.id,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all", response_model=List[CandidateSchemas.CandidateResponse])
def list_candidates(db: Session = Depends(get_db)):
    candidates = db.query(CandidateDB.Candidate).all()

    # Inject dynamic current stage
    results = []
    for c in candidates:
        data = CandidateSchemas.CandidateResponse.from_orm(c)
        data.current_candidate_stage = get_current_stage(db, c.id)
        results.append(data)

    return results


@router.get("/{id}", response_model=CandidateSchemas.CandidateResponse)
def get_candidate(id: int, db: Session = Depends(get_db)):
    candidate = (
        db.query(CandidateDB.Candidate).filter(CandidateDB.Candidate.id == id).first()
    )
    if not candidate:
        raise HTTPException(404, "Candidate not found")

    data = CandidateSchemas.CandidateResponse.from_orm(candidate)
    data.current_candidate_stage = get_current_stage(db, candidate.id)
    return data


@router.put("/Update/{id}")
def update_candidate(
    id: int,
    candidate_in: CandidateSchemas.CandidateUpdate,
    db: Session = Depends(get_db),
):
    candidate = (
        db.query(CandidateDB.Candidate).filter(CandidateDB.Candidate.id == id).first()
    )
    if not candidate:
        raise HTTPException(404, "Candidate not found")

    update_data = candidate_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(candidate, key, value)

    db.commit()
    db.refresh(candidate)
    return candidate


# --- Interview Endpoints ---


@router.get("/interviews/active")
def get_active_interviews(
    stage_id: Optional[int] = None,
    stage_status: Optional[str] = None,
    interview_status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    # Fetch all interviews joined with Stage and Candidate
    all_interviews = (
        db.query(CandidateDB.Interview)
        .join(CandidateDB.Stage)
        .join(CandidateDB.Candidate)
        .all()
    )

    # Dictionary to keep only the latest interview per candidate
    # Latest is defined by the highest Stage_index
    candidate_latest_map = {}

    for inv in all_interviews:
        cand = inv.candidate
        if not cand:
            continue

        # Filter candidates by status (Applied or Selected)
        if cand.Candidate_status not in ["Applied", "Selected"]:
            continue

        cand_id = cand.id
        stage_index = inv.stage.Stage_index if inv.stage else -1

        if cand_id not in candidate_latest_map:
            candidate_latest_map[cand_id] = inv
        else:
            existing_inv = candidate_latest_map[cand_id]
            existing_stage_index = (
                existing_inv.stage.Stage_index if existing_inv.stage else -1
            )
            if stage_index > existing_stage_index:
                candidate_latest_map[cand_id] = inv
            elif stage_index == existing_stage_index:
                # If same stage, take the one with higher ID (more recent record)
                if inv.id > existing_inv.id:
                    candidate_latest_map[cand_id] = inv

    response = []

    for inv in candidate_latest_map.values():
        # Apply filters to the latest round
        if stage_id and inv.stage_id != stage_id:
            continue
        if interview_status and inv.Interview_status != interview_status:
            continue

        # Get stage status for this specific stage
        cs = (
            db.query(CandidateDB.CandidateStage)
            .filter(
                CandidateDB.CandidateStage.candidate_id == inv.candidate_id,
                CandidateDB.CandidateStage.stage_id == inv.stage_id,
            )
            .first()
        )

        current_status = cs.Stage_status if cs else "Pending"

        if stage_status and current_status != stage_status:
            continue

        # Get total stages count
        total_stages = db.query(CandidateDB.Stage).count()
        
        # Get completed stages count for this candidate
        completed_stages = db.query(CandidateDB.CandidateStage).filter(
            CandidateDB.CandidateStage.candidate_id == inv.candidate_id,
            CandidateDB.CandidateStage.Stage_status == "Completed"
        ).count()

        response.append(
            {
                "id": inv.id,
                "candidate_id": inv.candidate_id,
                "Candidate_id": inv.candidate.Candidate_ID,
                "candidate_name": inv.candidate.Candidate_name,
                "candidate_role": inv.candidate.Job_title,
                "current_candidate_stage": (
                    inv.stage.Stage_name if inv.stage else "Unknown"
                ),
                "Interview_date": inv.Interview_date,
                "Interview_time": inv.Interview_time,
                "Interview_status": inv.Interview_status,
                "Stage_status": current_status,
                "Stage_name": inv.stage.Stage_name if inv.stage else "",
                "completed_stages_count": completed_stages,
                "total_stages_count": total_stages
            }
        )

    return response


@router.put("/UpdateInterview/{id}")
def update_interview(
    id: int,
    interview_in: CandidateSchemas.InterviewUpdate,
    db: Session = Depends(get_db),
):
    interview = (
        db.query(CandidateDB.Interview).filter(CandidateDB.Interview.id == id).first()
    )
    if not interview:
        raise HTTPException(404, "Interview not found")

    candidate = interview.candidate
    current_stage_record = (
        db.query(CandidateDB.CandidateStage)
        .filter(
            CandidateDB.CandidateStage.candidate_id == interview.candidate_id,
            CandidateDB.CandidateStage.stage_id == interview.stage_id,
        )
        .first()
    )

    # Apply updates
    if interview_in.Interview_status:
        interview.Interview_status = interview_in.Interview_status

    # REJECT FLOW
    if interview_in.Final_decision == "Rejected":
        candidate.Candidate_status = "Rejected"
        interview.Interview_status = "Rejected"
        if current_stage_record:
            current_stage_record.Stage_status = "Rejected"
        db.commit()
        return {"message": "Candidate Rejected"}

    # PROGRESSION FLOW
    if interview_in.Final_decision == "Selected":
        interview.Interview_status = "Completed"

        if current_stage_record:
            current_stage_record.Stage_status = "Completed"

        # Find next stage
        current_master_stage = interview.stage
        next_master_stage = (
            db.query(CandidateDB.Stage)
            .filter(
                CandidateDB.Stage.Stage_index == current_master_stage.Stage_index + 1
            )
            .first()
        )

        if next_master_stage:
            # Move to next
            candidate.Candidate_status = "Selected"

            # Create next CandidateStage
            new_cs = CandidateDB.CandidateStage(
                candidate_id=candidate.id,
                stage_id=next_master_stage.id,
                Stage_status="In Progress",
            )
            db.add(new_cs)

            # Create next Interview (placeholder)
            new_inv = CandidateDB.Interview(
                candidate_id=candidate.id,
                stage_id=next_master_stage.id,
                Interview_status="Scheduled",
            )
            db.add(new_inv)

            db.commit()
            return {"message": f"Moved to {next_master_stage.Stage_name}"}
        else:
            # No next stage -> Candidate is Recruited
            candidate.Candidate_status = "Recruited"
            db.commit()
            return {"message": "Candidate Recruited (Pipeline Complete)"}

    db.commit()
    return {"message": "Interview Updated"}


@router.get(
    "/stages/{candidate_id}",
    response_model=List[CandidateSchemas.CandidateStageResponse],
)
def get_candidate_stages(candidate_id: int, db: Session = Depends(get_db)):
    stages = (
        db.query(CandidateDB.CandidateStage)
        .filter(CandidateDB.CandidateStage.candidate_id == candidate_id)
        .all()
    )
    results = []
    for s in stages:
        data = CandidateSchemas.CandidateStageResponse.from_orm(s)
        data.Stage_name = s.stage.Stage_name if s.stage else ""
        results.append(data)
    return results


@router.post("/BulkSchedule")
def bulk_schedule_interviews(
    bulk_in: CandidateSchemas.BulkInterviewCreate, db: Session = Depends(get_db)
):
    try:
        # Resolve stage name to ID
        stage_master = (
            db.query(CandidateDB.Stage)
            .filter(CandidateDB.Stage.Stage_name == bulk_in.Stage_name)
            .first()
        )

        if not stage_master:
            # Fallback: if stage name doesn't exist, use the first one
            stage_master = (
                db.query(CandidateDB.Stage)
                .order_by(CandidateDB.Stage.Stage_index)
                .first()
            )

        count = 0
        for c_id in bulk_in.Candidate_ids:
            candidate = (
                db.query(CandidateDB.Candidate)
                .filter(CandidateDB.Candidate.id == c_id)
                .first()
            )
            if not candidate:
                continue

            # Update candidate status
            candidate.Candidate_status = "Selected"

            # Check if stage already exists for candidate
            existing_cs = (
                db.query(CandidateDB.CandidateStage)
                .filter(
                    CandidateDB.CandidateStage.candidate_id == c_id,
                    CandidateDB.CandidateStage.stage_id == stage_master.id,
                )
                .first()
            )

            if not existing_cs:
                new_cs = CandidateDB.CandidateStage(
                    candidate_id=c_id,
                    stage_id=stage_master.id,
                    Stage_status="In Progress",
                )
                db.add(new_cs)
            else:
                existing_cs.Stage_status = "In Progress"

            # Create Interview record
            new_inv = CandidateDB.Interview(
                candidate_id=c_id,
                stage_id=stage_master.id,
                Interview_date=bulk_in.Interview_date,
                Interview_time=bulk_in.Interview_time,
                Interview_status="Scheduled",
            )
            db.add(new_inv)
            count += 1

        db.commit()
        return {"message": f"Successfully scheduled {count} interviews", "count": count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
