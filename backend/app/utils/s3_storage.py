"""
S3 Storage utility for photo uploads with fallback to local filesystem.

Environment variables:
- AWS_S3_BUCKET: S3 bucket name to store photos
- AWS_ACCESS_KEY_ID: AWS access key
- AWS_SECRET_ACCESS_KEY: AWS secret key
- AWS_REGION: AWS region (default: us-east-1)
- AWS_S3_FOLDER: Folder prefix in bucket (default: photos)
- USE_S3: Enable S3 (default: True if bucket is set)
"""

import os
from typing import Optional, Any
from datetime import datetime, timezone
from uuid import uuid4
import logging

try:
    import boto3
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except ImportError:
    boto3 = None  # type: ignore[assignment]
    ClientError = Exception  # type: ignore[assignment,misc]
    HAS_BOTO3 = False

logger = logging.getLogger(__name__)


_ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
}


def _detected_media_family(file_content: bytes) -> tuple[str, set[str]] | None:
    """Detect supported media using signatures, not the client filename alone."""
    if file_content.startswith(b"\xff\xd8\xff"):
        return "image", {"image/jpeg", "image/jpg"}
    if file_content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image", {"image/png"}
    if len(file_content) >= 12 and file_content[:4] == b"RIFF" and file_content[8:12] == b"WEBP":
        return "image", {"image/webp"}

    # HEIC/HEIF, MP4 and MOV are ISO Base Media File Format containers. The
    # major brand at bytes 8..12 distinguishes the media families we accept.
    if len(file_content) >= 12 and file_content[4:8] == b"ftyp":
        brand = file_content[8:12]
        if brand in {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"}:
            return "image", {"image/heic", "image/heif"}
        if brand in {b"qt  "}:
            return "video", {"video/quicktime"}
        # Common MP4 brands. Some compatible brands vary, so the claimed type
        # still has to be video/mp4 before this branch is accepted.
        if brand in {b"isom", b"iso2", b"mp41", b"mp42", b"avc1", b"M4V ", b"MSNV"}:
            return "video", {"video/mp4"}

    return None


def validate_media_upload(file_content: bytes, content_type: str) -> tuple[str, str]:
    """Return (media_family, safe_extension) or reject unsupported/mismatched data."""
    normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized_type not in _ALLOWED_CONTENT_TYPES:
        raise ValueError("Tipo de archivo no permitido. Use JPEG, PNG, WebP, HEIC/HEIF, MP4 o MOV.")

    detected = _detected_media_family(file_content)
    if not detected:
        raise ValueError("El contenido del archivo no coincide con un formato de foto o video permitido.")

    media_family, compatible_types = detected
    if normalized_type not in compatible_types:
        raise ValueError("El tipo declarado del archivo no coincide con su contenido real.")

    return media_family, _ALLOWED_CONTENT_TYPES[normalized_type]


class S3StorageManager:
    """Manage photo uploads to S3 with optional local fallback."""

    def __init__(self):
        self.bucket = os.getenv("AWS_S3_BUCKET", "").strip()
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.folder = os.getenv("AWS_S3_FOLDER", "photos")
        self.enable_s3 = bool(self.bucket) and os.getenv("USE_S3", "true").lower() == "true"

        if self.enable_s3:
            try:
                if not HAS_BOTO3:
                    raise RuntimeError("boto3 no está instalado")
                self.s3_client: Any = boto3.client(  # type: ignore[union-attr]
                    "s3",
                    region_name=self.region,
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                )
                self.s3_client.head_bucket(Bucket=self.bucket)
                logger.info("S3 initialized: bucket=%s, region=%s", self.bucket, self.region)
            except Exception as exc:
                logger.warning("S3 initialization failed: %s. Using local fallback.", exc)
                self.enable_s3 = False
        else:
            logger.info("S3 not configured. Using local filesystem fallback.")

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        photo_request_id: int,
        content_type: str = "image/jpeg",
    ) -> str:
        """Validate and upload supported photo/video media.

        The client supplied filename is intentionally not used as a filesystem or
        object-storage path. This prevents path traversal, active-document uploads
        and collisions based on attacker-controlled names.
        """
        _media_family, safe_extension = validate_media_upload(file_content, content_type)
        safe_filename = f"{uuid4().hex}{safe_extension}"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        s3_key = f"{self.folder}/requests/{int(photo_request_id)}/{timestamp}_{safe_filename}"

        if self.enable_s3:
            return await self._upload_to_s3(file_content, s3_key, content_type)
        return await self._upload_to_local(file_content, photo_request_id, safe_filename)

    async def _upload_to_s3(
        self,
        file_content: bytes,
        s3_key: str,
        content_type: str,
    ) -> str:
        """Upload to S3 and return a pre-signed URL."""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    "source": "photo_requests",
                },
            )
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": s3_key},
                ExpiresIn=7 * 24 * 3600,
            )
            logger.info("Uploaded media to S3: %s", s3_key)
            return url
        except ClientError:
            logger.exception("S3 upload failed for key %s", s3_key)
            raise

    async def _upload_to_local(
        self,
        file_content: bytes,
        photo_request_id: int,
        safe_filename: str,
    ) -> str:
        """Upload validated media to local /uploads directory."""
        from pathlib import Path

        uploads_dir = Path(__file__).parent.parent.parent / "uploads"
        uploads_dir.mkdir(exist_ok=True)

        request_dir = uploads_dir / "requests" / str(int(photo_request_id))
        request_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filepath = request_dir / f"{timestamp}_{safe_filename}"
        filepath.write_bytes(file_content)

        url = f"/uploads/requests/{int(photo_request_id)}/{filepath.name}"
        logger.info("Uploaded validated media locally: %s", filepath)
        return url

    async def get_download_url(self, s3_key: str) -> Optional[str]:
        """Get a pre-signed download URL for an S3 object."""
        if not self.enable_s3:
            return None

        try:
            return self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": s3_key},
                ExpiresIn=7 * 24 * 3600,
            )
        except ClientError:
            logger.exception("Failed to generate S3 download URL for %s", s3_key)
            return None

    async def delete_file(self, s3_key: str) -> bool:
        """Delete file from S3."""
        if not self.enable_s3:
            return True

        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info("Deleted from S3: %s", s3_key)
            return True
        except ClientError:
            logger.exception("S3 delete failed for %s", s3_key)
            return False


_storage_manager: Optional[S3StorageManager] = None


def get_storage_manager() -> S3StorageManager:
    """Get or create the storage manager singleton."""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = S3StorageManager()
    return _storage_manager
