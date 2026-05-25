import asyncio,requests,httpx,base64,os
from typing import List,Optional
from pydantic import EmailStr
import os
from dotenv import load_dotenv


load_dotenv()

tenant_id = os.getenv("tenant_id")
client_id = os.getenv("client_id")
client_secret = os.getenv("client_secret")
sender_email = os.getenv("sender_email")





def build_graph_attachments(files: List[str]) -> list:
    attachments = []

    for file_path in files:

        with open(file_path, "rb") as f:
            file_content = f.read()

        encoded_content = base64.b64encode(
            file_content
        ).decode("utf-8")

        attachments.append(
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": os.path.basename(file_path),
                "contentBytes": encoded_content,
            }
        )

    return attachments

async def get_graph_token(
    tenant_id: str,
    client_id: str,
    client_secret: str,
) -> str:

    url = (
        f"https://login.microsoftonline.com/"
        f"{tenant_id}/oauth2/v2.0/token"
    )

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(url, data=data)

    res.raise_for_status()

    return res.json()["access_token"]


async def send_email(
    *,
    client_ip: str,
    receiver_emails: List[EmailStr],
    subject: str,
    body: str,
    is_html: bool = False,
    attachments: Optional[List[str]] = None,
    tenant_id: str,
    client_id: str,
    client_secret: str,
    sender_email: str,
) -> bool:

    token = await get_graph_token(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )

    payload = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML" if is_html else "Text",
                "content": body,
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": email
                    }
                }
                for email in receiver_emails
            ],
        },
        "saveToSentItems": True,
    }

    if attachments:
        payload["message"]["attachments"] = (
            build_graph_attachments(attachments)
        )

    url = (
        f"https://graph.microsoft.com/v1.0/"
        f"users/{sender_email}/sendMail"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            url,
            headers=headers,
            json=payload,
        )

    if res.status_code != 202:
        raise Exception(
            f"Mail failed: "
            f"{res.status_code} {res.text}"
        )

    return True



from payroll import PAYROLL_TEMPLATE

# ------------------- TEST -------------------
if __name__ == "__main__":
    email_conten=PAYROLL_TEMPLATE
    asyncio.run(
        send_email(
            client_ip="127.0.0.1",
            receiver_emails=[
                "siva@tibos.in",
            ],
            subject="This is From Tibos CRM",
            body=email_conten,
            is_html=True,
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            sender_email=sender_email
        )
    )