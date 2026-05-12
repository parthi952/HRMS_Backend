from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db

# Unga models matrum schemas-a correct-a import panradhu
from module.CustomIDDB import IDConfig
from Schemas.CustomIDSchemas import CustomIDStore

router = APIRouter(prefix="/CustomID", tags=["CustomID"])

# 1. GET ALL: React-oda Initial Fetch-kaga
@router.get("/store", response_model=CustomIDStore)
def get_store(db: Session = Depends(get_db)):
    all_configs = db.query(IDConfig).all()
    
    # React ethirpaakura { "EMP": [], "DEP": [], "CAN": [], "INT": [] } structure-kku mathuradhu
    store = {"EMP": [], "DEP": [], "CAN": [], "INT": [] }
    
    for item in all_configs:
        config_data = {
            "id": item.id,
            "prefix": item.prefix,
            "separator": item.separator,
            "digit": item.digit,
            "isActive": item.isActive
        }
        if item.category in store:
            store[item.category].append(config_data)
            
    return store

# --- routers/CustomID.py ---

@router.put("/store")
def sync_store(payload: CustomIDStore, db: Session = Depends(get_db)):
    try:
        # 1. Clear existing configs to prevent duplicates
        db.query(IDConfig).delete()
        
        # 2. Add new Employee configs
        for item in payload.EMP:
            db_item = IDConfig(**item.dict(), category="EMP")
            db.add(db_item)
            
        # 3. Add new Department configs
        for item in payload.DEP:
            db_item = IDConfig(**item.dict(), category="DEP")
            db.add(db_item)
            
        # 4. Add new Candidate configs
        for item in payload.CAN:
            db_item = IDConfig(**item.dict(), category="CAN")
            db.add(db_item)
            
        # 5. Add new Interview configs
        for item in payload.INT:
            db_item = IDConfig(**item.dict(), category="INT")
            db.add(db_item)
            
        db.commit()
        return {"status": "success", "message": "Database successfully synced"}

    except Exception as e:
        db.rollback()
        print(f"Error syncing: {e}") 
        raise HTTPException(status_code=500, detail=str(e))
