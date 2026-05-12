from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select

from Caluclation.IdCustom import generate_next_empid
import module.EmplyeeDB as EmplyeeDB
import Schemas.employeeSceema as employeeSceema
from database import get_db

router = APIRouter(prefix="/employee", tags=["Employee"])

from Caluclation.PayrollEandD import calculate_salary
import module.payrollProvider as payrollProvider


# ─── Employee CRUD ────────────────────────────────────────────────────────────


@router.post("/Register", status_code=status.HTTP_201_CREATED)
def create_employee(
    emp_in: employeeSceema.EmployeeCreate, db: Session = Depends(get_db)
):
    try:
        new_generated_id = generate_next_empid(db)

        new_emp = EmplyeeDB.Employee(
            Emp_id=new_generated_id,
            f_name=emp_in.f_name,
            l_name=emp_in.l_name,
            name=f"{emp_in.f_name} {emp_in.l_name}",
            gender=emp_in.gender,
            dob=emp_in.dob,
            phone=emp_in.phone,
            email=emp_in.email,
            Department=emp_in.Department,
            designation=emp_in.designation,
            emp_type=emp_in.emp_type,
            DateOfJoining=emp_in.DateOfJoining,
            Street=emp_in.Street,
            City=emp_in.City,
            State=emp_in.State,
            Pin_Code=emp_in.Pin_Code,
            p_Street=emp_in.p_Street,
            p_City=emp_in.p_City,
            p_State=emp_in.p_State,
            p_Pin_Code=emp_in.p_Pin_Code,
            provider=emp_in.provider,
            payType=emp_in.payType,
            currency=emp_in.currency,
            payFrequency=emp_in.payFrequency,
            annualSalary=emp_in.annualSalary,
            bonus_Type=emp_in.bonus_Type,
            bonus_CalculationMode=emp_in.bonus_CalculationMode,
            bonus_Value=emp_in.bonus_Value,
            apply_esi=emp_in.apply_esi,
            uan_number=emp_in.uan_number,
            pf_id=emp_in.pf_id,
            insurance_no=emp_in.insurance_no,
            aadhar_no=emp_in.aadhar_no,
            esi_no=emp_in.esi_no,
            esi_name=emp_in.esi_name,
            insurance_provider=emp_in.insurance_provider,
            bankName=emp_in.bankName,
            accountNumber=emp_in.accountNumber,
            ifscCode=emp_in.ifscCode,
            panNumber=emp_in.panNumber,
        )
        db.add(new_emp)
        db.flush()  # Get Employee PK before inserting children

        # ─── Education ───────────────────────────────────────────────────────
        for edu in emp_in.education:
            db.add(
                EmplyeeDB.Education(
                    emp_id=new_generated_id,
                    degree=edu.degree,
                    institution=edu.institution,
                    graduationYear=edu.graduationYear,
                )
            )

        # ─── Work Experience ─────────────────────────────────────────────────
        for work in emp_in.WorkExp:
            db.add(
                EmplyeeDB.WorkExpriance(
                    emp_id=new_generated_id,
                    company_name=work.company_name,
                    position=work.position,
                    FromDate=work.FromDate,
                    ToDate=work.ToDate,
                )
            )

        # ─── Family + Nominees ───────────────────────────────────────────────
        # FIX: Nominees must be linked via family_id, NOT emp_id.
        # We flush after each Family insert to get its auto-generated id,
        # then use that id as the FK for every nominee under that family member.
        for dep in emp_in.Familys:
            family_obj = EmplyeeDB.Familys(
                emp_id=new_generated_id,
                person_name=dep.person_name,
                relationship_type=dep.relationship_type,
                contact=dep.contact,
                person_dob=dep.person_dob,
            )
            db.add(family_obj)
            db.flush()  # ← family_obj.id is now available

            for nom in dep.nominees:
                if nom.nominee_name or nom.nominee_aadhar:  # skip empty rows
                    db.add(
                        EmplyeeDB.Nominees(
                            family_id=family_obj.id,  # ✅ correct FK
                            nominee_name=nom.nominee_name,
                            nominee_aadhar=nom.nominee_aadhar,
                        )
                    )

        db.commit()
        return {"message": "Successfully created employee", "Emp_id": new_generated_id}

    except Exception as e:
        db.rollback()
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/next-id")
def get_next_id(db: Session = Depends(get_db)):
    from Caluclation.IdCustom import generate_next_empid

    next_id = generate_next_empid(db)
    return {"next_id": next_id}


@router.get("/{emp_id}")
def get_employee(emp_id: str, db: Session = Depends(get_db)):
    """
    Fetches employee details and calculates dynamic payroll based on 
    assigned provider's earnings and deductions.
    """
    # Fetch employee basic info
    emp = db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == emp_id).first()
    
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Calculate monthly base salary (annual / 12)
    # Handle null/zero safely using coalesce-like logic
    annual_salary = emp.annualSalary if emp.annualSalary else 0.0
    base_salary = annual_salary / 12

    # Fetch dynamic payroll components from provider
    # Provider ID is stored in emp.provider
    earnings = []
    deductions = []
    
    if emp.provider:
        provider = db.query(payrollProvider.PayRollProvider).filter(
            payrollProvider.PayRollProvider.provider_id == emp.provider
        ).first()
        
        if provider:
            earnings = provider.earnings
            deductions = provider.deductions

    # Perform dynamic calculation
    payroll_results = calculate_salary(base_salary, earnings, deductions)

    # Return unified response
    return {
        "Employee": emp,
        **payroll_results
    }



@router.get("/")
def list_employees(db: Session = Depends(get_db)):
    stmt = select(EmplyeeDB.Employee)
    employees = db.execute(stmt).mappings().all()
    return employees


@router.put("/EmployeeUpdate/{emp_id}")
def update_employee(
    emp_id: str,
    emp_in: employeeSceema.EmployeeCreate,
    db: Session = Depends(get_db),
):
    emp = (
        db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == emp_id).first()
    )
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    update_data = emp_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        if key == "Emp_id" or isinstance(value, list):
            continue
        setattr(emp, key, value)

    try:
        db.commit()
        db.refresh(emp)
        return {"message": f"Successfully updated employee {emp_id}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ─── Education ────────────────────────────────────────────────────────────────


@router.get("/EmployeeEducation/{emp_id}")
def get_employee_education(emp_id: str, db: Session = Depends(get_db)):
    education = (
        db.query(EmplyeeDB.Education).filter(EmplyeeDB.Education.emp_id == emp_id).all()
    )
    if not education:
        raise HTTPException(
            status_code=404, detail="Education details not found for this employee"
        )
    return education


@router.post("/EmployeeEducationCreate/{emp_id}", status_code=status.HTTP_201_CREATED)
def create_employee_education(
    emp_id: str,
    education_in: List[employeeSceema.EducationCreate],
    db: Session = Depends(get_db),
):
    emp = (
        db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == emp_id).first()
    )
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    for edu in education_in:
        db.add(
            EmplyeeDB.Education(
                emp_id=emp_id,
                degree=edu.degree,
                institution=edu.institution,
                graduationYear=edu.graduationYear,
            )
        )

    try:
        db.commit()
        return {"message": f"Education details created for employee {emp_id}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/EmployeeEducationUpdate/{emp_id}")
def update_employee_education(
    emp_id: str,
    education_in: List[employeeSceema.EducationCreate],
    db: Session = Depends(get_db),
):
    emp = (
        db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == emp_id).first()
    )
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    existing = (
        db.query(EmplyeeDB.Education).filter(EmplyeeDB.Education.emp_id == emp_id).all()
    )
    if not existing:
        raise HTTPException(
            status_code=404,
            detail="No education records found — use POST /EmployeeEducationCreate instead",
        )

    db.query(EmplyeeDB.Education).filter(EmplyeeDB.Education.emp_id == emp_id).delete()

    for edu in education_in:
        db.add(
            EmplyeeDB.Education(
                emp_id=emp_id,
                degree=edu.degree,
                institution=edu.institution,
                graduationYear=edu.graduationYear,
            )
        )

    try:
        db.commit()
        return {
            "message": f"Successfully updated education details for employee {emp_id}"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ─── Family ───────────────────────────────────────────────────────────────────


@router.get("/EmployeeFamilys/{emp_id}")
def get_employee_Familys(emp_id: str, db: Session = Depends(get_db)):
    Familys = (
        db.query(EmplyeeDB.Familys).filter(EmplyeeDB.Familys.emp_id == emp_id).all()
    )
    if not Familys:
        raise HTTPException(
            status_code=404, detail="Family details not found for this employee"
        )
    return Familys


@router.post("/EmployeeFamilysCreate/{emp_id}", status_code=status.HTTP_201_CREATED)
def create_employee_Familys(
    emp_id: str,
    Familys_in: List[employeeSceema.FamilyCreate],
    db: Session = Depends(get_db),
):
    emp = (
        db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == emp_id).first()
    )
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    for dep in Familys_in:
        family_obj = EmplyeeDB.Familys(
            emp_id=emp_id,
            person_name=dep.person_name,
            relationship_type=dep.relationship_type,
            contact=dep.contact,
            person_dob=dep.person_dob,
        )
        db.add(family_obj)
        db.flush()

        for nom in dep.nominees:
            if nom.nominee_name or nom.nominee_aadhar:
                db.add(
                    EmplyeeDB.Nominees(
                        family_id=family_obj.id,
                        nominee_name=nom.nominee_name,
                        nominee_aadhar=nom.nominee_aadhar,
                    )
                )

    try:
        db.commit()
        return {"message": f"Family details created for employee {emp_id}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/EmployeeFamilysUpdate/{emp_id}")
def update_employee_Familys(
    emp_id: str,
    Familys_in: List[employeeSceema.FamilyCreate],
    db: Session = Depends(get_db),
):
    emp = (
        db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == emp_id).first()
    )
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    existing = (
        db.query(EmplyeeDB.Familys).filter(EmplyeeDB.Familys.emp_id == emp_id).all()
    )
    if not existing:
        raise HTTPException(
            status_code=404,
            detail="No family records found — use POST /EmployeeFamilysCreate instead",
        )

    # Delete old families (cascade will delete their nominees too)
    db.query(EmplyeeDB.Familys).filter(EmplyeeDB.Familys.emp_id == emp_id).delete()
    db.flush()

    for dep in Familys_in:
        family_obj = EmplyeeDB.Familys(
            emp_id=emp_id,
            person_name=dep.person_name,
            relationship_type=dep.relationship_type,
            contact=dep.contact,
            person_dob=dep.person_dob,
        )
        db.add(family_obj)
        db.flush()

        for nom in dep.nominees:
            if nom.nominee_name or nom.nominee_aadhar:
                db.add(
                    EmplyeeDB.Nominees(
                        family_id=family_obj.id,
                        nominee_name=nom.nominee_name,
                        nominee_aadhar=nom.nominee_aadhar,
                    )
                )

    try:
        db.commit()
        return {"message": f"Successfully updated Family details for employee {emp_id}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ─── Work Experience ─────────────────────────────────────────────────────────


@router.get("/EmployeeWorkExp/{emp_id}")
def get_employee_work_exp(emp_id: str, db: Session = Depends(get_db)):
    work = (
        db.query(EmplyeeDB.WorkExpriance)
        .filter(EmplyeeDB.WorkExpriance.emp_id == emp_id)
        .all()
    )
    if not work:
        raise HTTPException(status_code=404, detail="Work experience details not found")
    return work


@router.post("/EmployeeWorkExpCreate/{emp_id}", status_code=status.HTTP_201_CREATED)
def create_employee_work_exp(
    emp_id: str,
    work_in: List[employeeSceema.WorkExpCreate],
    db: Session = Depends(get_db),
):
    emp = (
        db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == emp_id).first()
    )
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    for w in work_in:
        db.add(
            EmplyeeDB.WorkExpriance(
                emp_id=emp_id,
                company_name=w.company_name,
                position=w.position,
                FromDate=w.FromDate,
                ToDate=w.ToDate,
            )
        )

    try:
        db.commit()
        return {"message": f"Work experience details created for employee {emp_id}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/EmployeeWorkExpUpdate/{emp_id}")
def update_employee_work_exp(
    emp_id: str,
    work_in: List[employeeSceema.WorkExpCreate],
    db: Session = Depends(get_db),
):
    emp = (
        db.query(EmplyeeDB.Employee).filter(EmplyeeDB.Employee.Emp_id == emp_id).first()
    )
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    db.query(EmplyeeDB.WorkExpriance).filter(
        EmplyeeDB.WorkExpriance.emp_id == emp_id
    ).delete()

    for w in work_in:
        db.add(
            EmplyeeDB.WorkExpriance(
                emp_id=emp_id,
                company_name=w.company_name,
                position=w.position,
                FromDate=w.FromDate,
                ToDate=w.ToDate,
            )
        )

    try:
        db.commit()
        return {
            "message": f"Successfully updated work experience for employee {emp_id}"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
