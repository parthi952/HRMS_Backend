import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from database import get_db
from Auth.router import get_current_user
from Auth.models import User
from module import EmplyeeDB
from module.payrollProvider import PayRollProvider
from PdfEditor.PdfMaker import PDFMaker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pdf", tags=["PDF Generation"])


@router.post("/generate")
def generate_pdf(
    html_content: str,
    current_user: User = Depends(get_current_user)
):
    """
    General endpoint to render any arbitrary HTML content into PDF bytes.
    Requires employee portal authentication.
    """
    try:
        pdf_bytes = PDFMaker.render_html_to_pdf(html_content)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=document.pdf"}
        )
    except Exception as e:
        logger.error(f"Failed to generate generic PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile PDF: {e}"
        )


@router.get("/payslip/{emp_id}")
def download_payslip_pdf(
    emp_id: str,
    month: str = "May 2026",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Secure payslip generator:
    1. Fetches employee profile from DB.
    2. Dynamically calculates base salary, earnings, deductions, and net salary.
    3. Feeds structured details into the HTML generator.
    4. Compiles with WeasyPrint and serves a premium PDF download.
    """
    emp = db.query(EmplyeeDB.Employee).filter(
        EmplyeeDB.Employee.Emp_id == emp_id
    ).first()
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee profile '{emp_id}' not found."
        )

    # Calculate payroll variables dynamically matching router calculations
    annual_salary = float(emp.annualSalary or 0)
    salary_type = getattr(emp, "salary_type", "yearly")
    
    if salary_type == "monthly":
        base_m = annual_salary
    else:
        base_m = annual_salary / 12

    # Fetch provider
    provider = db.query(PayRollProvider).filter(
        PayRollProvider.provider_id == emp.provider
    ).first()

    earnings = []
    deductions = []
    total_earn = 0
    total_ded = 0

    if provider:
        for earn in provider.earnings:
            val = (base_m * earn.value) / 100 if earn.type == "percentage" else earn.value
            earnings.append({"name": earn.name, "value": val})
            total_earn += val
        
        for ded in provider.deductions:
            val = (base_m * ded.value) / 100 if ded.type == "percentage" else ded.value
            deductions.append({"name": ded.name, "value": val})
            total_ded += val

    gross = base_m + total_earn
    net = gross - total_ded

    # Render corporate HTML payslip
    try:
        payslip_html = PDFMaker.get_payslip_html(
            emp_name=f"{emp.f_name or ''} {emp.l_name or ''}".strip() or "Employee",
            emp_id=emp.Emp_id,
            dept=emp.Department or "N/A",
            desig=emp.designation or "Associate",
            salary_type=salary_type,
            base_salary=base_m,
            earnings=earnings,
            deductions=deductions,
            gross=gross,
            net=net,
            month=month
        )
        pdf_bytes = PDFMaker.render_html_to_pdf(payslip_html)
        filename = f"payslip_{emp_id}_{month.replace(' ', '_')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Failed to generate payslip PDF for {emp_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate payslip: {e}"
        )


@router.post("/offer-letter")
def download_offer_letter_pdf(
    candidate_name: str,
    designation: str,
    salary: str,
    joining_date: str,
    current_user: User = Depends(get_current_user)
):
    """
    Dynamic Offer Letter generator endpoint.
    Accepts customized parameters and generates a downloadable branded PDF.
    """
    try:
        offer_html = PDFMaker.get_offer_letter_html(
            candidate_name=candidate_name,
            designation=designation,
            salary=salary,
            joining_date=joining_date
        )
        pdf_bytes = PDFMaker.render_html_to_pdf(offer_html)
        filename = f"offer_letter_{candidate_name.replace(' ', '_')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Failed to generate offer letter PDF for {candidate_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate offer letter: {e}"
        )


# ─── New Payslip Generation & Azure Blob Storage Upload Endpoints ─────────────

from FileUpload.BlobFile import upload_file, generate_file_url, generate_blob_name
from module.PayrollDB import PayslipReport
import io

@router.post("/payslip/{emp_id}/generate-and-upload")
def generate_and_upload_payslip(
    emp_id: str,
    month: str = "May 2026",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calculates payroll, generates a branded PDF, uploads it to Azure Blob Storage,
    and records it in the database. Returns the secure generated SAS URL.
    """
    # 1. Fetch employee
    emp = db.query(EmplyeeDB.Employee).filter(
        EmplyeeDB.Employee.Emp_id == emp_id
    ).first()
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee profile '{emp_id}' not found."
        )

    # 2. Check if already generated for this month
    existing = db.query(PayslipReport).filter(
        PayslipReport.emp_id == emp_id,
        PayslipReport.month == month
    ).first()
    if existing:
        # Re-generate fresh SAS URL
        blob_name = existing.blob_url.split("/")[-1].split("?")[0]
        fresh_url = generate_file_url(blob_name)
        return {"message": "Payslip already uploaded. Here is the fresh URL.", "url": fresh_url}

    # 3. Calculate payroll
    annual_salary = float(emp.annualSalary or 0)
    salary_type = getattr(emp, "salary_type", "yearly")
    
    if salary_type == "monthly":
        base_m = annual_salary
    else:
        base_m = annual_salary / 12

    # Fetch provider
    provider = db.query(PayRollProvider).filter(
        PayRollProvider.provider_id == emp.provider
    ).first()

    earnings = []
    deductions = []
    total_earn = 0
    total_ded = 0

    if provider:
        for earn in provider.earnings:
            val = (base_m * earn.value) / 100 if earn.type == "percentage" else earn.value
            earnings.append({"name": earn.name, "value": val})
            total_earn += val
        
        for ded in provider.deductions:
            val = (base_m * ded.value) / 100 if ded.type == "percentage" else ded.value
            deductions.append({"name": ded.name, "value": val})
            total_ded += val

    gross = base_m + total_earn
    net = gross - total_ded

    # 4. Generate HTML and PDF bytes
    try:
        payslip_html = PDFMaker.get_payslip_html(
            emp_name=f"{emp.f_name or ''} {emp.l_name or ''}".strip() or "Employee",
            emp_id=emp.Emp_id,
            dept=emp.Department or "N/A",
            desig=emp.designation or "Associate",
            salary_type=salary_type,
            base_salary=base_m,
            earnings=earnings,
            deductions=deductions,
            gross=gross,
            net=net,
            month=month
        )
        pdf_bytes = PDFMaker.render_html_to_pdf(payslip_html)
    except Exception as e:
        logger.error(f"Failed to generate payslip PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate payslip template: {e}"
        )

    # 5. Upload to Azure Storage
    try:
        filename = f"payslip_{emp_id}_{month.replace(' ', '_')}.pdf"
        blob_name = generate_blob_name(filename)
        # Wrap in io.BytesIO for Azure upload compatibility
        pdf_stream = io.BytesIO(pdf_bytes)
        sas_url = upload_file(pdf_stream, blob_name, content_type="application/pdf")
    except Exception as e:
        logger.error(f"Failed to upload payslip to Azure Storage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload payslip PDF to storage: {e}"
        )

    # 6. Save in db
    new_report = PayslipReport(
        emp_id=emp_id,
        month=month,
        blob_url=sas_url
    )
    db.add(new_report)
    try:
        db.commit()
        db.refresh(new_report)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to write payslip record to database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete database entry for payslip: {e}"
        )

    return {"message": "Payslip uploaded successfully.", "url": sas_url}


@router.get("/payslip/{emp_id}/all")
def get_all_uploaded_payslips(
    emp_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetches all generated/uploaded payslip reports for an employee and yields fresh SAS download links.
    """
    reports = db.query(PayslipReport).filter(
        PayslipReport.emp_id == emp_id
    ).order_by(PayslipReport.uploaded_at.desc()).all()

    results = []
    for r in reports:
        # Extract the plain blob name to generate a fresh, non-expired SAS URL
        blob_name = r.blob_url.split("/")[-1].split("?")[0]
        fresh_url = generate_file_url(blob_name)
        results.append({
            "id": r.id,
            "month": r.month,
            "url": fresh_url,
            "uploaded_at": r.uploaded_at.isoformat()
        })

    return results
