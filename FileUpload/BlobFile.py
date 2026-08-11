# from azure.storage.blob import (
#     BlobServiceClient,
#     generate_blob_sas,
#     BlobSasPermissions,
#     ContentSettings
# )

# from dotenv import load_dotenv

# from datetime import datetime, timedelta

# import os
# import uuid

# load_dotenv()


# account_name = os.getenv("AccountNname")

# account_key = os.getenv("AccountKey")

# container_name = os.getenv("ContainerName")

# connection_string = os.getenv(
#     "AccountSteing"
# )

# # =========================
# # BLOB CLIENT
# # =========================

# blob_service_client = (
#     BlobServiceClient.from_connection_string(
#         connection_string
#     )
# )

# # =========================
# # GENERATE UNIQUE FILE NAME
# # =========================

# def generate_blob_name(filename: str):
#     # Replace spaces and special characters that might cause issues
#     clean_filename = filename.replace(" ", "_")
#     return f"{uuid.uuid4()}-{clean_filename}"

# # =========================
# # GENERATE SAS URL
# # =========================

# def generate_file_url(blob_name: str):
#     sas_token = generate_blob_sas(
#         account_name=account_name,
#         container_name=container_name,
#         blob_name=blob_name,
#         account_key=account_key,
#         permission=BlobSasPermissions(read=True),
#         expiry=datetime.utcnow() + timedelta(minutes=10)
#     )
    
#     file_url = (
#         f"https://{account_name}.blob.core.windows.net/"
#         f"{container_name}/{blob_name}?{sas_token}"
#     )
#     return file_url


# def upload_file(file, blob_name: str, content_type: str = "application/octet-stream"):
#     blob_client = blob_service_client.get_blob_client(
#         container=container_name,
#         blob=blob_name
#     )

#     # Reset file pointer if it's a SpooledTemporaryFile
#     if hasattr(file, 'seek'):
#         file.seek(0)

#     blob_client.upload_blob(
#         file,
#         overwrite=True,
#         content_settings=ContentSettings(
#             content_type=content_type,
#             content_disposition="inline"
#         )
#     )

#     return generate_file_url(blob_name)


import os
import uuid
import logging

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Cloudinary is used when credentials are present; otherwise files are saved
# to local disk and served via the /uploads static route (see main.py).
_CLOUDINARY_ENABLED = bool(os.getenv("CLOUDINARY_CLOUD_NAME"))

try:
    import cloudinary
    import cloudinary.uploader
    if _CLOUDINARY_ENABLED:
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
            api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET"),
            secure=True
        )
except ImportError:
    _CLOUDINARY_ENABLED = False
    logger.warning("cloudinary package not installed — using local disk storage")

# Resolve uploads directory: prefer UPLOADS_DIR env var, otherwise find it
# relative to this file's location (FileUpload/../uploads).
_env_uploads = os.getenv("UPLOADS_DIR", "")
if _env_uploads:
    UPLOADS_DIR = os.path.abspath(_env_uploads)
else:
    UPLOADS_DIR = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads")
    )

API_URL = os.getenv("API_URL", "https://hrm-api.tibostech.in")

logger.info(f"[BlobFile] UPLOADS_DIR={UPLOADS_DIR}  API_URL={API_URL}  cloudinary={_CLOUDINARY_ENABLED}")


# =========================
# GENERATE UNIQUE FILE NAME
# =========================

def generate_blob_name(filename: str):
    filename = filename.replace(" ", "_")
    return f"{uuid.uuid4()}-{filename}"


# =========================
# UPLOAD FILE
# =========================

def upload_file(
    file,
    blob_name: str,
    folder: str = "hrms"
):

    if hasattr(file, "seek"):
        file.seek(0)

    public_id = generate_blob_name(blob_name)

    if _CLOUDINARY_ENABLED:
        result = cloudinary.uploader.upload(
            file=file,
            folder=folder,
            public_id=public_id,
            resource_type="auto",
            overwrite=True
        )
        return result["secure_url"]

    # Local disk storage
    folder_dir = os.path.join(UPLOADS_DIR, folder)
    os.makedirs(folder_dir, exist_ok=True)
    dest_path = os.path.join(folder_dir, public_id)

    logger.info(f"[BlobFile] saving to {dest_path}")
    with open(dest_path, "wb") as out:
        content = file.read()
        if not content:
            raise ValueError("Uploaded file is empty — nothing to save")
        out.write(content)

    logger.info(f"[BlobFile] saved {len(content)} bytes")

    # The app is created with root_path="/api", which Starlette applies to
    # mounted sub-apps (like the /uploads StaticFiles mount) even though
    # normal routes don't need it — so the public URL must include /api.
    return f"{API_URL}/api/uploads/{folder}/{public_id}"