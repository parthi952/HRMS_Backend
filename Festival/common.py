"""Shared helpers used by both Festival Wishes and Commercial Emails —
recipient resolution, template lookup, and HTML rendering are identical
for both, only the source data (a FestivalWish vs a CommercialEmail row)
differs."""
from sqlalchemy.orm import Session
import module.FestivalDB as FestivalDB
import module.EmplyeeDB as EmplyeeDB


def get_recipients(audience: str, db: Session, cc_emails_str: str = "", to_emails_str: str = ""):
    audience = audience or "employees"
    recipients = []
    seen = set()

    # 1. If explicit recipient email(s) are specified in the Recipient Box, send ONLY to those!
    if to_emails_str and to_emails_str.strip():
        for item in to_emails_str.split(","):
            item = item.strip()
            if item and "@" in item and item.lower() not in seen:
                seen.add(item.lower())
                recipients.append(("Valued Recipient", item))
        if recipients:
            return recipients

    if audience in ("employees", "both"):
        emp_rows = db.query(
            EmplyeeDB.Employee.name,
            EmplyeeDB.Employee.email,
            EmplyeeDB.Employee.Status
        ).filter(
            EmplyeeDB.Employee.email.isnot(None),
            EmplyeeDB.Employee.email != ""
        ).all()
        for name, email, status in emp_rows:
            if not email or not email.strip():
                continue
            clean_email = email.strip()
            # Status check: include if Status is Active/active/null or not Explicitly Inactive/Terminated
            status_str = (status or "Active").strip().lower()
            if status_str not in ("inactive", "terminated", "resigned", "disabled") and clean_email.lower() not in seen:
                seen.add(clean_email.lower())
                recipients.append((name or "Team Member", clean_email))

    if audience in ("customers", "both"):
        cust_rows = db.query(FestivalDB.WishContact.name, FestivalDB.WishContact.email).filter(
            FestivalDB.WishContact.enabled == True,
            FestivalDB.WishContact.email.isnot(None),
            FestivalDB.WishContact.email != ""
        ).all()
        for name, email in cust_rows:
            if not email or not email.strip():
                continue
            clean_email = email.strip()
            if clean_email.lower() not in seen:
                seen.add(clean_email.lower())
                recipients.append((name or "Valued Customer", clean_email))

    # Fallback to CC Emails if no recipients were found in DB tables
    if not recipients and cc_emails_str:
        cc_list = [c.strip() for c in cc_emails_str.split(",") if c.strip() and "@" in c]
        for c_email in cc_list:
            if c_email.lower() not in seen:
                seen.add(c_email.lower())
                recipients.append(("Valued Recipient", c_email))

    return recipients


def get_template(template_id, db: Session):
    template = None
    if template_id:
        template = db.query(FestivalDB.WishTemplate).filter(FestivalDB.WishTemplate.id == template_id).first()
    if not template:
        template = db.query(FestivalDB.WishTemplate).filter(FestivalDB.WishTemplate.is_default == True).first()
    if not template:
        template = db.query(FestivalDB.WishTemplate).order_by(FestivalDB.WishTemplate.id).first()
    return template


def merge_message(message: str, name: str) -> str:
    """Simple mail-merge: replaces {{name}} / {name} placeholders with the recipient's name."""
    return (
        message
        .replace("{{name}}", name).replace("{{Name}}", name)
        .replace("{name}", name).replace("{Name}", name)
    )


def build_email_html(title: str, template, message: str) -> str:
    if not template:
        return message
    header = template.header_html.replace("{{festival_name}}", title).replace("{festival_name}", title)
    if template.logo_url:
        align_margin = {
            "left": "margin:0 auto 10pt 0;",
            "right": "margin:0 0 10pt auto;",
        }.get(template.logo_align or "center", "margin:0 auto 10pt auto;")
        logo_html = f'<img src="{template.logo_url}" alt="" width="{template.logo_width or 120}" style="display:block;{align_margin}max-width:100%;" />'
        header = logo_html + header
    highlight_block = ""
    if template.highlight_html:
        highlight_block = f"""
  <tr>
    <td style="padding:11.25pt 26.25pt 18.75pt;">
      <table cellspacing="0" cellpadding="0" border="0" style="width:100%;">
        <tr>
          <td style="background-color:{template.highlight_bg_color};padding:15pt 18.75pt;color:#000;text-align:center;">
            {template.highlight_html}
          </td>
        </tr>
      </table>
    </td>
  </tr>"""
    return f"""
<table cellspacing="0" cellpadding="0" border="0" style="margin:0 auto;width:525pt;max-width:100%;font-family:Aptos, Calibri, Helvetica, sans-serif;">
  <tr>
    <td style="background-color:{template.header_bg_color};padding:22.5pt 15pt 18.75pt;text-align:center;color:#000;">
      {header}
    </td>
  </tr>
  <tr>
    <td style="padding:26.25pt 26.25pt 11.25pt;">
      <div style="line-height:1.38;margin:0 0 8pt;font-size:11pt;color:#000;">{message}</div>
    </td>
  </tr>{highlight_block}
  <tr><td style="background-color:#E8EDF4;height:0.75pt;">&nbsp;</td></tr>
  <tr>
    <td style="background-color:{template.footer_bg_color};padding:26.25pt;">
      {template.footer_html}
    </td>
  </tr>
</table>
""".strip()
