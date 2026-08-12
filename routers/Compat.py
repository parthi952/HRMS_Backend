from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from module.JobPosterDB import education_Options, AI_Model, AIMode, SelectionCheckList

router = APIRouter(tags=["Compat"])


@router.get("/education/all")
def compat_get_education_options(db: Session = Depends(get_db)):
    return {"data": db.query(education_Options).all()}


@router.post("/education/create", status_code=status.HTTP_201_CREATED)
def compat_create_education_option(payload: dict, db: Session = Depends(get_db)):
    new_item = education_Options(id=str(__import__("uuid").uuid4()), **payload)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return {"message": "Created", "data": new_item}


@router.get("/aimodel/all")
def compat_get_aimodels(db: Session = Depends(get_db)):
    return {"data": db.query(AI_Model).all()}


@router.post("/aimodel/create", status_code=status.HTTP_201_CREATED)
def compat_create_aimodel(payload: dict, db: Session = Depends(get_db)):
    new_item = AI_Model(id=str(__import__("uuid").uuid4()), **payload)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return {"message": "Created", "data": new_item}


@router.get("/aimode/all")
def compat_get_aimodes(db: Session = Depends(get_db)):
    return {"data": db.query(AIMode).all()}


@router.post("/aimode/create", status_code=status.HTTP_201_CREATED)
def compat_create_aimode(payload: dict, db: Session = Depends(get_db)):
    new_item = AIMode(id=str(__import__("uuid").uuid4()), **payload)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return {"message": "Created", "data": new_item}


@router.get("/checklist/all")
def compat_get_checklists(db: Session = Depends(get_db)):
    return {"data": db.query(SelectionCheckList).all()}


@router.post("/checklist/create", status_code=status.HTTP_201_CREATED)
def compat_create_checklist(payload: dict, db: Session = Depends(get_db)):
    new_item = SelectionCheckList(id=str(__import__("uuid").uuid4()), **payload)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return {"message": "Created", "data": new_item}


@router.delete("/{route}/{item_id}")
def compat_delete(route: str, item_id: str, db: Session = Depends(get_db)):
    model_map = {
        "education": education_Options,
        "aimodel": AI_Model,
        "aimode": AIMode,
        "checklist": SelectionCheckList,
    }
    model = model_map.get(route)
    if not model:
        raise HTTPException(status_code=404, detail=f"Unknown route: {route}")
    item = db.query(model).filter(model.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(item)
    db.commit()
    return {"message": "Deleted"}
