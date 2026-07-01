import os
import logging
import cloudinary

logger = logging.getLogger(__name__)

# Support both spelling variants for API key
api_key = os.getenv("CLOUDINARY_API_KEY") or os.getenv("COLUDINARY_API_KEY")
cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
api_secret = os.getenv("CLOUDINARY_API_SECRET")

# Production-grade check: warn if any key is missing
if not all([cloud_name, api_key, api_secret]):
    missing = [
        name for name, val in [
            ("CLOUDINARY_CLOUD_NAME", cloud_name),
            ("CLOUDINARY_API_KEY", api_key),
            ("CLOUDINARY_API_SECRET", api_secret)
        ] if not val
    ]
    logger.warning(
        f"Cloudinary is not fully configured. Missing environment variables: {', '.join(missing)}. "
        "Image uploads will fail."
    )
else:
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )


