"""CEPH/S3-compatible storage provider implementation."""

import logging
from typing import Dict, Optional
from datetime import datetime
import uuid
import time

import aioboto3
from botocore.exceptions import ClientError
from botocore.config import Config

from app.domain.interfaces import IStorageProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class CephStorageProvider(IStorageProvider):
    """
    CEPH/S3-compatible storage provider using boto3/aioboto3.
    
    Optimized for Zata Ceph RGW:
    - Uses S3v2 signatures for maximum stability with proxies.
    - Explicitly omits custom Metadata headers which can cause signature failures.
    - Enforces path-style addressing and us-east-1 region.
    """
    
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        public_url: Optional[str] = None,
    ):
        self.endpoint_url = endpoint_url or settings.CEPH_ENDPOINT
        self.access_key_id = access_key_id or settings.CEPH_ACCESS_KEY
        self.secret_access_key = secret_access_key or settings.CEPH_SECRET_KEY
        self.bucket_name = bucket_name or settings.CEPH_BUCKET
        self.public_url = public_url or settings.CEPH_PUBLIC_URL
        
        if not all([self.endpoint_url, self.access_key_id, self.secret_access_key, self.bucket_name]):
            raise ValueError(
                "CEPH storage requires CEPH_ENDPOINT, CEPH_ACCESS_KEY, CEPH_SECRET_KEY, and CEPH_BUCKET"
            )
        
        # Create boto3 session
        self.session = aioboto3.Session()
        
        # Create S3 config (S3v2 is proven stable for this environment)
        self.s3_config = Config(
            signature_version='s3',
            region_name='us-east-1',
            s3={
                'addressing_style': 'path'
            }
        )
        
        logger.info(f"CEPH storage initialized: endpoint={self.endpoint_url}, bucket={self.bucket_name}")

    def _generate_key(self, prefix: str = "sources", filename: Optional[str] = None) -> str:
        """Generate storage key for file."""
        now = datetime.utcnow()
        file_id = str(uuid.uuid4())
        
        if filename:
            if '.' in filename:
                ext = filename.rsplit('.', 1)[1]
                key = f"{prefix}/{now.year}/{now.month:02d}/{file_id}.{ext}"
            else:
                key = f"{prefix}/{now.year}/{now.month:02d}/{file_id}"
        else:
            key = f"{prefix}/{now.year}/{now.month:02d}/{file_id}"
        
        return key
    
    async def store(
        self,
        key: str,
        content: bytes,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        if not key:
            key = self._generate_key()
        
        s3_key = key
        # Key format: bucket_name/user_id/notebook_id/source_id.ext
        if key.startswith(f"{self.bucket_name}/"):
            s3_key = key[len(self.bucket_name) + 1:]
        
        try:
            async with self.session.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name='us-east-1',
                config=self.s3_config,
            ) as s3:
                put_params = {
                    'Bucket': self.bucket_name,
                    'Key': s3_key,
                    'Body': content,
                }
                
                # Handling metadata: Omit custom metadata as it causes S3v2 signature failures
                # with the Zata proxy. The application stores metadata in SQL anyway.
                if metadata:
                    # ContentType is a standard S3 header and is stable
                    if 'content_type' in metadata:
                        put_params['ContentType'] = str(metadata['content_type'])
                    elif 'mimeType' in metadata:
                        put_params['ContentType'] = str(metadata['mimeType'])
                
                # Upload file
                await s3.put_object(**put_params)
                
                logger.info(f"File stored in CEPH: {s3_key} ({len(content)} bytes)")
                
                # Return key or public URL
                full_key = f"{self.bucket_name}/{s3_key}" if not key.startswith(f"{self.bucket_name}/") else key
                if self.public_url:
                    base_url = self.public_url.rstrip('/')
                    return f"{base_url}/{self.bucket_name}/{s3_key}"
                return full_key
                
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', 'No message')
            logger.error(f"Failed to store file in CEPH: {error_code} - {error_message}")
            logger.error(f"CEPH config - Endpoint: {self.endpoint_url}, Bucket: {self.bucket_name}, Key: {s3_key}")
            
            error_msg = f"CEPH storage error ({error_code}): {error_message or str(e)}"
            if error_code == 'SignatureDoesNotMatch':
                 error_msg = f"CEPH authentication failed (SignatureDoesNotMatch). Please check if custom metadata headers are being filtered or modified."
            
            raise RuntimeError(error_msg)
        except Exception as e:
            logger.error(f"Unexpected error storing file: {e}", exc_info=True)
            raise RuntimeError(f"Storage error: {str(e)}")
    
    async def retrieve(self, key: str) -> bytes:
        """Retrieve file content from CEPH/S3."""
        try:
            async with self.session.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name='us-east-1',
                config=self.s3_config,
            ) as s3:
                response = await s3.get_object(
                    Bucket=self.bucket_name,
                    Key=key,
                )
                content = await response['Body'].read()
                return content
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchKey':
                raise FileNotFoundError(f"File not found: {key}")
            raise RuntimeError(f"CEPH storage error: {e}")
    
    async def delete(self, key: str) -> bool:
        """Delete file from CEPH/S3."""
        try:
            async with self.session.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name='us-east-1',
                config=self.s3_config,
            ) as s3:
                await s3.delete_object(
                    Bucket=self.bucket_name,
                    Key=key,
                )
                return True
        except ClientError:
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if file exists in CEPH/S3."""
        try:
            async with self.session.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name='us-east-1',
                config=self.s3_config,
            ) as s3:
                await s3.head_object(
                    Bucket=self.bucket_name,
                    Key=key,
                )
                return True
        except ClientError:
            return False
    
    async def get_signed_url(self, key: str, expires_in: int = 600) -> str:
        """Generate a pre-signed URL for direct file access."""
        try:
            s3_key = key
            if key.startswith(f"{self.bucket_name}/"):
                s3_key = key[len(self.bucket_name) + 1:]
            
            import boto3
            from botocore.config import Config
            
            s3_client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name='us-east-1',
                config=Config(
                    signature_version='s3',
                    s3={'addressing_style': 'path'}
                ),
            )
            
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key,
                },
                ExpiresIn=expires_in,
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise RuntimeError(f"CEPH storage error: {e}")
