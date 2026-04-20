import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from moduels import EmplyeeDB
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



@router.delete("/providers/{provider_id}")
def delete_provider(provider_id: str, db: Session = Depends(get_db)):

    try:
        provider = db.query(PayRollProvider).filter(
            PayRollProvider.provider_id == provider_id
        ).first()

        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")

        # ✅ Delete children using ORM (SAFE)
        for earning in provider.earnings:
            db.delete(earning)

        for deduction in provider.deductions:
            db.delete(deduction)

        # ✅ Delete parent
        db.delete(provider)

        db.commit()

        return {"message": "Deleted successfully"}

    except Exception as e:
        db.rollback()
        print("🔥 REAL DELETE ERROR:", e)  # IMPORTANT
        raise HTTPException(
            status_code=500,
            detail=str(e)   # 👈 show real error in frontend
        )
    


@router.get("/details/{emp_id}")
def get_full_payroll(emp_id: str, db: Session = Depends(get_db)):

    # ✅ 1. Get Employee FIRST
    emp = db.query(EmplyeeDB.Employee).filter(
        EmplyeeDB.Employee.Emp_id == emp_id
    ).first()

    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # ✅ 2. Get Provider using provider_id
    provider = db.query(PayRollProvider).filter(
        PayRollProvider.provider_id == emp.provider
    ).first()

    if not provider:
        raise HTTPException(
            status_code=404,
            detail=f"Provider '{emp.provider}' not found"
        )

    base_salary = float(emp.annualSalary or 0) / 12

    earnings_list = []
    deductions_list = []

    total_earnings = 0
    total_deductions = 0

    # ✅ Earnings
    for earn in provider.earnings:
        val = (base_salary * earn.value) / 100 if earn.type == "percentage" else earn.value
        earnings_list.append({
            "name": earn.name,
            "value": val
        })
        total_earnings += val

    # ❌ Deductions
    for ded in provider.deductions:
        val = (base_salary * ded.value) / 100 if ded.type == "percentage" else ded.value
        deductions_list.append({
            "name": ded.name,
            "value": val
        })
        total_deductions += val

    gross_salary = base_salary + total_earnings
    net_salary = gross_salary - total_deductions

    return {
        "emp_id": emp_id,
        "provider": emp.provider,
        "base_salary": base_salary,
        "earnings": earnings_list,
        "deductions": deductions_list,
        "gross_salary": gross_salary,
        "net_salary": net_salary
    }



@router.get("/")
def get_all_employee_payroll(db: Session = Depends(get_db)):

    try:
        employees = db.query(EmplyeeDB.Employee).all()

        result = []

        for emp in employees:

            annual = float(emp.annualSalary or 0)

            monthly_salary = annual / 12

            name = f"{emp.f_name or ''} {emp.l_name or ''}".strip()

            result.append({
    "emp_id": emp.Emp_id,
    "employee": f"{emp.f_name or ''} {emp.l_name or ''}".strip(),
    "department": emp.Department or "N/A",
    "net": monthly_salary,
    "status": "Pending"
})

        return result

    except Exception as e:
        print("🔥 ERROR:", e)   # 👈 VERY IMPORTANT
        raise HTTPException(status_code=500, detail=str(e))
