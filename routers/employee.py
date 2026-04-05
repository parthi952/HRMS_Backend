from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func,select

import models, schemas
from database import get_db

router = APIRouter(
    prefix="/employee",
    tags=["Employee"]
)

monthly_basic=func.coalesce(models.Employee.annualSalary/12,0)
employee_pf=func.coalesce(monthly_basic*0.12,0)
employer_eps=func.coalesce(func.least(monthly_basic, 15000)*0.0833,0)
employer_epf=func.coalesce(func.least(monthly_basic, 15000)*0.0367,0)
net_salary=func.coalesce(monthly_basic-employee_pf)

# def calculate_salary(annual_salary):
#     monthly_basic = annual_salary / 12
#     employee_pf = monthly_basic * 0.12
#     employer_eps = min(monthly_basic, 15000) * 0.0833
#     employer_epf = min(monthly_basic, 15000) * 0.0367
#     net_salary = monthly_basic - employee_pf

#     return monthly_basic, employee_pf, employer_eps, employer_epf, net_salary

# Employee creation endpoint
@router.post("/Register", status_code=status.HTTP_201_CREATED)
def create_employee(emp_in: schemas.EmployeeCreate, db: Session = Depends(get_db)):
    try:


        new_emp = models.Employee(
            Emp_id=emp_in.Emp_id,
            f_name=emp_in.f_name,
            l_name=emp_in.l_name,
            name=func.concat(emp_in.f_name, " ", emp_in.l_name).label("name"),
            gender=emp_in.gender,
            dob=emp_in.dob,
            phone=emp_in.phone,
            email=emp_in.email,
            Department=emp_in.Department,
            designation=emp_in.designation,
            emp_type=emp_in.emp_type,
            DateOfJoining=emp_in.DateOfJoining,
            company_name=emp_in.company_name,
            position=emp_in.position,
            FromDate=emp_in.FromDate,
            ToDate=emp_in.ToDate,
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
           
            bankName=emp_in.bankName,
            accountNumber=emp_in.accountNumber,
            ifscCode=emp_in.ifscCode,
            panNumber=emp_in.panNumber,
        )
        db.add(new_emp)
        db.flush() 

        for edu in emp_in.education:
            db.add(models.Education(
                emp_id=emp_in.Emp_id,
                degree=edu.degree,
                institution=edu.institution,
                graduationYear=edu.graduationYear,  
            ))

        for dep in emp_in.dependents:
            db.add(models.Dependents(
                emp_id=emp_in.Emp_id,
                person_name=dep.person_name,
                relationship_type=dep.relationship_type,
                contact=dep.contact,
                person_dob=dep.person_dob, 
            ))

        db.commit()
        return {"message": f"Successfully created employee {emp_in.Emp_id}"}

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Employee ID '{emp_in.Emp_id}' already exists."
        )
    except Exception as e:
        db.rollback()
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

#employee get endpoint
@router.get("/{emp_id}")
def get_employee(emp_id: str, db: Session = Depends(get_db)):

    stmt = select(
        models.Employee,
        monthly_basic.label("monthly_salary"),
        employee_pf.label("PF"),
        employer_epf.label("EPF"),
        employer_eps.label("EPS")
    ).where(models.Employee.Emp_id == emp_id)

    result = db.execute(stmt).first()

    if not result:
        raise HTTPException(status_code=404, detail="Employee not found")

    emp, monthly_salary, PF, EPF, EPS = result

    return {
        "Employee": emp,
        "monthly_salary": monthly_salary,
        "PF": PF,
        "EPF": EPF,
        "EPS": EPS
    }


#Full Employee list endpoint
@router.get("/")
def list_employees(db: Session = Depends(get_db)):
    employees_stmt = select(
        models.Employee
    )

    
    employees=db.execute(employees_stmt).mappings().all()
    return employees


# specific employee update endpoint
@router.put("/EmployeeUpdate/{emp_id}") 
def update_employee(emp_id: str, emp_in: schemas.EmployeeCreate, db: Session = Depends(get_db)):
    emp = db.query(models.Employee).filter(models.Employee.Emp_id == emp_id).first()
    
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
    
    # Education and dependents get and update logic here if needed, currently they are not updated in this endpoint.
@router.get("/EmployeeEducation/{emp_id}")
def get_employee_education(emp_id: str, db: Session = Depends(get_db)):
    education = db.query(models.Education).filter(models.Education.emp_id == emp_id).all()
    if not education:
        raise HTTPException(status_code=404, detail="Education details not found for this employee")
    return education
@router.get("/EmployeeDependents/{emp_id}")
def get_employee_dependents(emp_id: str, db: Session = Depends(get_db)):
    dependents = db.query(models.Dependents).filter(models.Dependents.emp_id == emp_id).all()
    if not dependents:
        raise HTTPException(status_code=404, detail="Dependent details not found for this employee")
    return dependents
@router.put("/EmployeeEducationUpdate/{emp_id}")
def update_employee_education(emp_id: str, education_in: List[schemas.EducationCreate], db: Session = Depends(get_db)):
    emp = db.query(models.Employee).filter(models.Employee.Emp_id == emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    db.query(models.Education).filter(models.Education.emp_id == emp_id).delete()
    
    for edu in education_in:
        db.add(models.Education(
            emp_id=emp_id,
            degree=edu.degree,
            institution=edu.institution,
            graduationYear=edu.graduationYear,  
        ))

    try:
        db.commit()
        return {"message": f"Successfully updated education details for employee {emp_id}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
@router.put("/EmployeeDependentsUpdate/{emp_id}")
def update_employee_dependents(emp_id: str, dependents_in: List[schemas.DependentCreate], db: Session = Depends(get_db)):
    emp = db.query(models.Employee).filter(models.Employee.Emp_id == emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    db.query(models.Dependents).filter(models.Dependents.emp_id == emp_id).delete()
    
    for dep in dependents_in:
        db.add(models.Dependents(
            emp_id=emp_id,
            person_name=dep.person_name,
            relationship_type=dep.relationship_type,
            contact=dep.contact,
            person_dob=dep.person_dob, 
        ))

    try:
        db.commit()
        return {"message": f"Successfully updated dependent details for employee {emp_id}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))