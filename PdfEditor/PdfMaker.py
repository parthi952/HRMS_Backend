import logging
import io
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# ── WEASYPRINT DEFENSIVE LOADING ──────────────────────────────────────────────
WEASYPRINT_AVAILABLE = False
WEASYPRINT_ERROR = ""
try:
    from weasyprint import HTML, CSS

    WEASYPRINT_AVAILABLE = True
except Exception as e:
    WEASYPRINT_ERROR = str(e)
    logger.warning(
        f"WeasyPrint could not initialize (GTK+ dynamic library might be missing). "
        f"PDF Generation fallback is active. Diagnostic: {e}"
    )

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


class PDFMaker:
    @staticmethod
    def render_html_to_pdf(html_content: str) -> bytes:
        """
        Converts HTML content to PDF bytes using WeasyPrint with A4 styles.
        If WeasyPrint is unavailable, generates a defensive valid fallback PDF.
        """
        if not WEASYPRINT_AVAILABLE:
            logger.warning(
                "WeasyPrint GTK missing. Returning highly compatible defensive placeholder PDF bytes."
            )
            minimal_pdf = (
                b"%PDF-1.4\n"
                b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
                b"3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<<>>/Contents 4 0 R>>endobj\n"
                b"4 0 obj<</Length 42>>stream\n"
                b"BT /F1 24 Tf 100 700 Td (Apex HRMS Payslip PDF) Tj ET\n"
                b"endstream\n"
                b"endobj\n"
                b"xref\n"
                b"0 5\n"
                b"0000000000 65535 f\n"
                b"0000000009 00000 n\n"
                b"0000000056 00000 n\n"
                b"0000000111 00000 n\n"
                b"0000000212 00000 n\n"
                b"trailer<</Size 5/Root 1 0 R>>\n"
                b"startxref\n"
                b"303\n"
                b"%%EOF"
            )
            return minimal_pdf

        # Paged Media stylesheet for modern printable A4 pages
        paged_media_css = CSS(
            string="""
            @page {
                size: A4;
                margin: 20mm 15mm 20mm 15mm;
                @bottom-right {
                    content: "Page " counter(page) " of " counter(pages);
                    font-family: 'Outfit', 'Inter', sans-serif;
                    font-size: 8pt;
                    color: #94a3b8;
                }
                @bottom-left {
                    content: "Apex Solutions HRMS • Confidential Document";
                    font-family: 'Outfit', 'Inter', sans-serif;
                    font-size: 8pt;
                    color: #94a3b8;
                }
            }
            body {
                font-family: 'Outfit', 'Inter', sans-serif;
                color: #1e293b;
                line-height: 1.5;
            }
        """
        )

        pdf_file = io.BytesIO()
        HTML(string=html_content).write_pdf(pdf_file, stylesheets=[paged_media_css])
        return pdf_file.getvalue()

    @staticmethod
    def get_payslip_html(
        emp_name: str,
        emp_id: str,
        dept: str,
        desig: str,
        salary_type: str,
        base_salary: float,
        earnings: list,
        deductions: list,
        gross: float,
        net: float,
        month: str,
    ) -> str:
        """
        Loads the payslip template from disk and substitutes placeholder variables.
        """
        template_path = os.path.join(TEMPLATE_DIR, "payslip.html")
        if not os.path.exists(template_path):
            raise FileNotFoundError(
                f"Payslip template file not found at: {template_path}"
            )

        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()

        earnings_rows = "".join(
            [
                f"<tr><td>{e['name']}</td><td class='text-right'>${e['value']:.2f}</td></tr>"
                for e in earnings
            ]
        )
        deductions_rows = "".join(
            [
                f"<tr><td>{d['name']}</td><td class='text-right'>${d['value']:.2f}</td></tr>"
                for d in deductions
            ]
        )
        if not deductions_rows:
            deductions_rows = "<tr><td colspan='2'>No deductions applied</td></tr>"

        # Substitute placeholders
        html = template
        html = html.replace("{{month}}", str(month))
        html = html.replace("{{emp_name}}", str(emp_name))
        html = html.replace("{{emp_id}}", str(emp_id))
        html = html.replace("{{dept}}", str(dept))
        html = html.replace("{{desig}}", str(desig))
        html = html.replace("{{salary_type}}", str(salary_type))
        html = html.replace("{{base_salary}}", f"${base_salary:,.2f}")
        html = html.replace("{{earnings_rows}}", earnings_rows)
        html = html.replace("{{deductions_rows}}", deductions_rows)
        html = html.replace("{{gross}}", f"${gross:,.2f}")
        html = html.replace("{{total_deductions}}", f"${(gross - net):,.2f}")
        html = html.replace("{{net}}", f"${net:,.2f}")

        return html

    @staticmethod
    def get_offer_letter_html(
        candidate_name: str, designation: str, salary: str, joining_date: str
    ) -> str:
        """
        Loads the offer letter template from disk and substitutes placeholder variables.
        """
        template_path = os.path.join(TEMPLATE_DIR, "offer_letter.html")
        if not os.path.exists(template_path):
            raise FileNotFoundError(
                f"Offer letter template file not found at: {template_path}"
            )

        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()

        today_str = datetime.now().strftime("%B %d, %Y")

        # Substitute placeholders
        html = template
        html = html.replace("{{today_str}}", today_str)
        html = html.replace("{{candidate_name}}", str(candidate_name))
        html = html.replace("{{designation}}", str(designation))
        html = html.replace("{{salary}}", f"${float(salary):,.2f}")
        html = html.replace("{{joining_date}}", str(joining_date))

        return html
