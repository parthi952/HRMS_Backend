import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from moduels.payrollProvider import PayRollProvider, Earning, Deduction
from Schemas.PayrollSchemas import PayRollProviderCreate, PayRollProviderOut
from typing import List

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payroll", tags=["Payroll"])


@router.post(
    "/create/providers",
    response_model=PayRollProviderOut,
    status_code=status.HTTP_201_CREATED
)
def create_payroll_provider(
    provider_data: PayRollProviderCreate,
    db: Session = Depends(get_db)
):
    # 1. Check for duplicate provider name
    existing = db.query(PayRollProvider).filter(
        PayRollProvider.providername == provider_data.providername
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A provider with the name '{provider_data.providername}' already exists."
        )

    # 2. Generate a unique provider_id using UUID (thread-safe, no race condition)
    new_id = f"provider_{uuid.uuid4().hex[:8]}"

    # 3. Create Provider Instance
    new_provider = PayRollProvider(
        provider_id=new_id,
        providername=provider_data.providername,
        description=provider_data.description or ""
    )

    # 4. Add Earnings & Deductions
    new_provider.earnings = [Earning(**earn.model_dump()) for earn in provider_data.earnings]
    new_provider.deductions = [Deduction(**ded.model_dump()) for ded in provider_data.deductions]

    try:
        db.add(new_provider)
        db.commit()
        db.refresh(new_provider)
        return new_provider
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create payroll provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payroll provider."
        )


@router.get("/providers", response_model=List[PayRollProviderOut])
def get_all_providers(db: Session = Depends(get_db)):
    return db.query(PayRollProvider).all()


@router.get("/providers/{provider_id}", response_model=PayRollProviderOut)
def get_provider_by_id(provider_id: str, db: Session = Depends(get_db)):
    provider = db.query(PayRollProvider).filter(
        PayRollProvider.provider_id == provider_id
    ).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_id}' not found."
        )
    return provider


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(provider_id: str, db: Session = Depends(get_db)):
    provider = db.query(PayRollProvider).filter(
        PayRollProvider.provider_id == provider_id
    ).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_id}' not found."
        )
    try:
        db.delete(provider)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete payroll provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete payroll provider."
        )