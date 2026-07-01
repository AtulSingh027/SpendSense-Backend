import os
import logging
from typing import Union, Optional
from fastapi import UploadFile, HTTPException, status
from configs.cloudinary_config import cloudinary
import cloudinary.uploader

logger = logging.getLogger(__name__)


def upload_image_to_cloudinary(file_or_str: Union[UploadFile, str, None]) -> Optional[str]:
    """
    Uploads an image to Cloudinary and returns its secure URL.
    
    Supports:
    1. FastAPI UploadFile (binary upload)
    2. Base64 data URIs (e.g. data:image/png;base64,...)
    3. Remote HTTP/HTTPS image URLs
    4. Local file paths (if they exist)
    
    If the input is none of the above (e.g., standard category icons like 'food-icon'),
    it returns the string as-is without attempting to upload.
    """
    if not file_or_str:
        return None

    try:
        # Check if the input is a FastAPI UploadFile
        if isinstance(file_or_str, UploadFile):
            # Reset file cursor just in case it was read elsewhere
            file_or_str.file.seek(0)
            file_content = file_or_str.file.read()
            # Reset cursor back
            file_or_str.file.seek(0)
            
            response = cloudinary.uploader.upload(
                file_content,
                folder="spend_sense_media",
                resource_type="auto"
            )
            return response.get("secure_url") or response.get("url")

        # If it's a string, determine if it should be uploaded to Cloudinary
        if isinstance(file_or_str, str):
            is_base64 = file_or_str.startswith("data:")
            is_remote_url = file_or_str.startswith(("http://", "https://"))
            is_local_file = os.path.exists(file_or_str)

            if is_base64 or is_remote_url or is_local_file:
                response = cloudinary.uploader.upload(
                    file_or_str,
                    folder="spend_sense_media",
                    resource_type="auto"
                )
                return response.get("secure_url") or response.get("url")
            
            # If it's just a default vector/system icon name (e.g., 'food-icon')
            return file_or_str

        # Unsupported type
        logger.warning(f"Unsupported file type passed to upload_image_to_cloudinary: {type(file_or_str)}")
        return str(file_or_str)

    except Exception as e:
        logger.exception("Failed to upload image to Cloudinary")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image upload to Cloudinary failed: {str(e)}"
        )


def get_image_from_cloudinary(url: str):
    """
    Retrieves image details from Cloudinary by extracting the public ID from its URL.
    Handles subfolders and versioning strings in the URL.
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")
        
    try:
        public_id = extract_public_id_from_url(url)
        if not public_id:
            raise ValueError("Could not extract a valid Cloudinary public ID from URL")
        return cloudinary.uploader.explicit(public_id)
    except Exception as e:
        logger.exception(f"Failed to retrieve image details for URL: {url}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def extract_public_id_from_url(url: str) -> Optional[str]:
    """
    Extracts the public ID (including folder path, excluding version and extension) from a Cloudinary URL.
    Example:
    'https://res.cloudinary.com/diffw1lth/image/upload/v1719811234/spend_sense_media/abc123xyz.png'
    returns 'spend_sense_media/abc123xyz'
    """
    if "/upload/" not in url:
        return None
        
    try:
        # Get everything after '/upload/'
        after_upload = url.split("/upload/")[1]
        
        # Split by '/' to separate version and folders
        parts = after_upload.split("/")
        
        # If the first part starts with 'v' followed by numbers, it's the version prefix (e.g. v1719811234)
        if parts[0].startswith("v") and parts[0][1:].isdigit():
            parts = parts[1:]
            
        # Reconstruct the path without the version
        path_without_version = "/".join(parts)
        
        # Strip the file extension (e.g. .png, .jpg)
        public_id = path_without_version.rsplit(".", 1)[0]
        return public_id
    except Exception:
        return None
