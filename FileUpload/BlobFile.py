from azure.storage.blob import (
    BlobServiceClient,
    generate_blob_sas,
    BlobSasPermissions,
    ContentSettings
)

from dotenv import load_dotenv

from datetime import datetime, timedelta

import os
import uuid

load_dotenv()


account_name = os.getenv("AccountNname")

account_key = os.getenv("AccountKey")

container_name = os.getenv("ContainerName")

connection_string = os.getenv(
    "AccountSteing"
)

# =========================
# BLOB CLIENT
# =========================

blob_service_client = (
    BlobServiceClient.from_connection_string(
        connection_string
    )
)

# =========================
# GENERATE UNIQUE FILE NAME
# =========================

def generate_blob_name(filename: str):
    # Replace spaces and special characters that might cause issues
    clean_filename = filename.replace(" ", "_")
    return f"{uuid.uuid4()}-{clean_filename}"

# =========================
# GENERATE SAS URL
# =========================

def generate_file_url(blob_name: str):
    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(minutes=10)
    )
    
    file_url = (
        f"https://{account_name}.blob.core.windows.net/"
        f"{container_name}/{blob_name}?{sas_token}"
    )
    return file_url


def upload_file(file, blob_name: str, content_type: str = "application/octet-stream"):
    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob=blob_name
    )

    # Reset file pointer if it's a SpooledTemporaryFile
    if hasattr(file, 'seek'):
        file.seek(0)

    blob_client.upload_blob(
        file,
        overwrite=True,
        content_settings=ContentSettings(
            content_type=content_type,
            content_disposition="inline"
        )
    )

    return generate_file_url(blob_name)