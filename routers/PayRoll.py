import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from module import EmplyeeDB
from module.payrollProvider import PayRollProvider, Earning, Deduction
from Schemas.PayrollSchemas import PayRollProviderCreate, PayRollProviderOut, PayrollCalculateRequest
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

    # ✅ 1. Employee
    emp = db.query(EmplyeeDB.Employee).filter(
        EmplyeeDB.Employee.Emp_id == emp_id
    ).first()

    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # ✅ 2. Provider
    provider = db.query(PayRollProvider).filter(
        PayRollProvider.provider_id == emp.provider
    ).first()

    if not provider:
        raise HTTPException(
            status_code=404,
            detail=f"Provider '{emp.provider}' not found"
        )

    # ✅ 3. Provider Name
    provider_name = provider.providername

    # ✅ 4. Salary Mode (IMPORTANT)
    # assume emp.salary_type = "monthly" or "yearly"
    salary_type = getattr(emp, "salary_type", "yearly")

    if salary_type == "monthly":
        monthly_base = float(emp.annualSalary or 0)
        yearly_base = monthly_base * 12
    else:
        yearly_base = float(emp.annualSalary or 0)
        monthly_base = yearly_base / 12

    # -----------------------------
    # ✅ MONTHLY CALCULATION
    # -----------------------------
    earnings_month = []
    deductions_month = []

    total_earn_m = 0
    total_ded_m = 0

    for earn in provider.earnings:
        val = (monthly_base * earn.value) / 100 if earn.type == "percentage" else earn.value
        earnings_month.append({
            "name": earn.name,
            "value": round(val, 2)
        })
        total_earn_m += val

    for ded in provider.deductions:
        val = (monthly_base * ded.value) / 100 if ded.type == "percentage" else ded.value
        deductions_month.append({
            "name": ded.name,
            "value": round(val, 2)
        })
        total_ded_m += val

    gross_month = monthly_base + total_earn_m
    net_month = gross_month - total_ded_m

    # -----------------------------
    # ✅ YEARLY CALCULATION
    # -----------------------------
    earnings_year = []
    deductions_year = []

    total_earn_y = total_earn_m * 12
    total_ded_y = total_ded_m * 12

    for e in earnings_month:
        earnings_year.append({
            "name": e["name"],
            "value": round(e["value"] * 12, 2)
        })

    for d in deductions_month:
        deductions_year.append({
            "name": d["name"],
            "value": round(d["value"] * 12, 2)
        })

    gross_year = gross_month * 12
    net_year = net_month * 12

    # -----------------------------
    # ✅ FINAL RESPONSE
    # -----------------------------
    return {
        "emp_id": emp_id,
        "provider_id": emp.provider,
        "provider_name": provider_name,
        "salary_type": salary_type,

        "monthly": {
            "base_salary": round(monthly_base, 2),
            "earnings": earnings_month,
            "deductions": deductions_month,
            "gross_salary": round(gross_month, 2),
            "net_salary": round(net_month, 2)
        },

        "yearly": {
            "base_salary": round(yearly_base, 2),
            "earnings": earnings_year,
            "deductions": deductions_year,
            "gross_salary": round(gross_year, 2),
            "net_salary": round(net_year, 2)
        }
    }


@router.get("/")
def get_all_employee_payroll(db: Session = Depends(get_db)):

    try:
        employees = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Status == "Active").all()
        # Pre-fetch all providers to avoid N+1 queries
        providers = db.query(PayRollProvider).all()
        provider_map = {p.provider_id: p for p in providers}

        result = []
        for emp in employees:
            annual = float(emp.annualSalary or 0)
            salary_type = getattr(emp, "salary_type", "yearly")
            
            if salary_type == "monthly":
                monthly_base = annual
            else:
                monthly_base = annual / 12

            # Calculate Net if provider exists
            net_pay = monthly_base
            provider = provider_map.get(emp.provider)
            if provider:
                total_earn = 0
                total_ded = 0
                for earn in provider.earnings:
                    val = (monthly_base * earn.value) / 100 if earn.type == "percentage" else earn.value
                    total_earn += val
                for ded in provider.deductions:
                    val = (monthly_base * ded.value) / 100 if ded.type == "percentage" else ded.value
                    total_ded += val
                net_pay = (monthly_base + total_earn) - total_ded

            result.append({
                "emp_id": emp.Emp_id,
                "provider_name": provider.providername if provider else "N/A",
                "employee": f"{emp.f_name or ''} {emp.l_name or ''}".strip(),
                "department": emp.Department or "N/A",
                "net": round(net_pay, 2),
                "status": "Pending"
            })

        return result

    except Exception as e:
        print("🔥 ERROR:", e)   # 👈 VERY IMPORTANT
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/calculate")
def calculate_payroll(
    payload: PayrollCalculateRequest,
    db: Session = Depends(get_db)
):

    # ✅ Provider
    provider = db.query(PayRollProvider).filter(
        PayRollProvider.provider_id == payload.provider_id
    ).first()

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Provider not found"
        )

    # -----------------------------
    # BASE SALARY
    # -----------------------------
    if payload.salary_type == "monthly":
        monthly_base = float(payload.salary)
    else:
        monthly_base = float(payload.salary) / 12

    # -----------------------------
    # EARNINGS
    # -----------------------------
    earnings = []
    total_earnings = 0

    for earn in provider.earnings:

        amount = (
            (monthly_base * earn.value) / 100
            if earn.type == "percentage"
            else earn.value
        )

        earnings.append({
            "name": earn.name,
            "type": earn.type,
            "value": earn.value,
            "amount": round(amount, 2)
        })

        total_earnings += amount

    # -----------------------------
    # DEDUCTIONS
    # -----------------------------
    deductions = []
    total_deductions = 0

    for ded in provider.deductions:

        amount = (
            (monthly_base * ded.value) / 100
            if ded.type == "percentage"
            else ded.value
        )

        deductions.append({
            "name": ded.name,
            "type": ded.type,
            "value": ded.value,
            "amount": round(amount, 2)
        })

        total_deductions += amount

    # -----------------------------
    # FINAL CALCULATION
    # -----------------------------
    gross = monthly_base + total_earnings

    net = gross - total_deductions

    # -----------------------------
    # RESPONSE
    # -----------------------------
    return {
        "provider_id": provider.provider_id,
        "provider_name": provider.providername,

        "baseSalary": round(monthly_base, 2),

        "earnings": earnings,
        "deductions": deductions,

        "totalEarnings": round(total_earnings, 2),
        "totalDeductions": round(total_deductions, 2),

        "gross": round(gross, 2),
        "net": round(net, 2)
    }
