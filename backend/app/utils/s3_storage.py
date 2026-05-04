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

class S3StorageManager:
    """Manage photo uploads to S3 with optional local fallback."""
    
    def __init__(self):
        self.bucket = os.getenv("AWS_S3_BUCKET", "").strip()
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.folder = os.getenv("AWS_S3_FOLDER", "photos")
        self.enable_s3 = self.bucket and os.getenv("USE_S3", "true").lower() == "true"
        
        if self.enable_s3:
            try:
                self.s3_client: Any = boto3.client(  # type: ignore[union-attr]
                    's3',
                    region_name=self.region,
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
                )
                # Test connection
                self.s3_client.head_bucket(Bucket=self.bucket)
                logger.info(f"✅ S3 initialized: bucket={self.bucket}, region={self.region}")
            except Exception as e:
                logger.warning(f"⚠️  S3 initialization failed: {e}. Using local fallback.")
                self.enable_s3 = False
        else:
            logger.info("S3 not configured. Using local filesystem fallback.")
    
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        photo_request_id: int,
        content_type: str = "image/jpeg"
    ) -> str:
        """
        Upload file to S3 or local filesystem.
        
        Args:
            file_content: Raw bytes of the file
            filename: Original filename (e.g., "photo.jpg")
            photo_request_id: Photo request ID for folder structure
            content_type: MIME type
        
        Returns:
            URL to access the file
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        s3_key = f"{self.folder}/requests/{photo_request_id}/{timestamp}_{filename}"
        
        if self.enable_s3:
            return await self._upload_to_s3(
                file_content, s3_key, content_type
            )
        else:
            return await self._upload_to_local(
                file_content, photo_request_id, filename
            )
    
    async def _upload_to_s3(
        self,
        file_content: bytes,
        s3_key: str,
        content_type: str
    ) -> str:
        """Upload to S3 and return public URL."""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    "source": "photo_requests"
                }
            )
            
            # Generate pre-signed URL valid for 7 days
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': s3_key},
                ExpiresIn=7 * 24 * 3600
            )
            
            logger.info(f"✅ Uploaded to S3: {s3_key}")
            return url
            
        except ClientError as e:
            logger.error(f"❌ S3 upload failed: {e}")
            raise
    
    async def _upload_to_local(
        self,
        file_content: bytes,
        photo_request_id: int,
        filename: str
    ) -> str:
        """Upload to local /uploads directory."""
        from pathlib import Path
        
        uploads_dir = Path(__file__).parent.parent.parent / "uploads"
        uploads_dir.mkdir(exist_ok=True)
        
        request_dir = uploads_dir / f"requests" / str(photo_request_id)
        request_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filepath = request_dir / f"{timestamp}_{filename}"
        
        filepath.write_bytes(file_content)
        
        # Return relative URL
        url = f"/uploads/requests/{photo_request_id}/{filepath.name}"
        logger.info(f"✅ Uploaded to local: {filepath}")
        return url
    
    async def get_download_url(self, s3_key: str) -> Optional[str]:
        """Get a pre-signed download URL for an S3 object."""
        if not self.enable_s3:
            return None
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': s3_key},
                ExpiresIn=7 * 24 * 3600
            )
            return url
        except ClientError as e:
            logger.error(f"❌ Failed to generate download URL: {e}")
            return None
    
    async def delete_file(self, s3_key: str) -> bool:
        """Delete file from S3."""
        if not self.enable_s3:
            return True
        
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info(f"✅ Deleted from S3: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"❌ S3 delete failed: {e}")
            return False


# Global instance
_storage_manager: Optional[S3StorageManager] = None

def get_storage_manager() -> S3StorageManager:
    """Get or create the storage manager singleton."""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = S3StorageManager()
    return _storage_manager
