# utils/storage/s3_storage.py

import os
from datetime import datetime, timedelta, timezone

import boto3


class S3Storage:
    # Singleton instance
    _instance = None
    _lock = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(S3Storage, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # Only initialize once - check and set immediately to prevent recursion
        if self._initialized:
            return

        # Set immediately to prevent recursive initialization
        self._initialized = True

        try:
            self.bucket = os.getenv("S3_BUCKET", "mangaconverter")
            self.error_bucket = os.getenv("S3_ERROR_BUCKET", "mangaconverter-errors")

            # Get TTL from environment variable (in days)
            self.ttl_days = int(os.getenv("NEXT_PUBLIC_TTL", "1"))

            # Use internal URL for backend operations
            minio_url = os.getenv("MINIO_URL", "http://localhost:9000")
            # Use external URL for browser-accessible presigned URLs
            self.external_url = os.getenv("MINIO_EXTERNAL_URL", "http://localhost:9000")

            # Configure for S3-compatible storage (Hetzner, R2, etc.)
            from botocore.config import Config

            s3_config = Config(
                region_name='us-east-1',  # Standard region for S3 compatibility
                signature_version='s3v4',
                s3={'addressing_style': 'virtual'}
            )

            self.client = boto3.client(
                "s3",
                endpoint_url=minio_url,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                config=s3_config,
            )

            # Separate client for external presigned URLs (also use virtual-hosted style)
            self.external_client = boto3.client(
                "s3",
                endpoint_url=self.external_url,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                config=s3_config,
            )

            # Check if buckets exist (Hetzner requires manual creation via console)
            print("[S3Storage] Verifying bucket accessibility...")
            self._check_bucket_access()
            print("[S3Storage] Bucket verification completed")

            # Ensure CORS configuration is applied for browser uploads
            print("[S3Storage] Ensuring CORS configuration...")
            self.ensure_cors_configuration()

        except Exception as e:
            # Reset flag if initialization fails
            self._initialized = False
            print(f"[S3Storage] Initialization failed: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _check_bucket_access(self) -> None:
        """
        Check if buckets are accessible.
        Note: Buckets must be created manually via Hetzner Cloud Console.
        """
        # Check main bucket
        try:
            self.client.head_bucket(Bucket=self.bucket)
            print(f"[S3Storage] ✓ Main bucket accessible: {self.bucket}")
        except self.client.exceptions.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"[S3Storage] ✗ Main bucket NOT FOUND: {self.bucket}")
                print(f"[S3Storage]   → Create it via Hetzner Cloud Console: https://console.hetzner.cloud/projects")
            else:
                print(f"[S3Storage] ✗ Error accessing main bucket {self.bucket}: {e}")
        except Exception as e:
            print(f"[S3Storage] ✗ Could not check main bucket {self.bucket}: {e}")

        # Check error bucket
        try:
            self.client.head_bucket(Bucket=self.error_bucket)
            print(f"[S3Storage] ✓ Error bucket accessible: {self.error_bucket}")
        except self.client.exceptions.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"[S3Storage] ✗ Error bucket NOT FOUND: {self.error_bucket}")
                print(f"[S3Storage]   → Create it via Hetzner Cloud Console: https://console.hetzner.cloud/projects")
            else:
                print(f"[S3Storage] ✗ Error accessing error bucket {self.error_bucket}: {e}")
        except Exception as e:
            print(f"[S3Storage] ✗ Could not check error bucket {self.error_bucket}: {e}")

    def _calculate_expiration_date(self, days: int) -> str:
        """
        Calculate the expiration date for object metadata (HTTP-date format).
        """
        expire_at = datetime.now(timezone.utc) + timedelta(days=days)
        return expire_at.strftime("%a, %d %b %Y %H:%M:%S GMT")

    def ensure_lifecycle_rule(self, expiration_days: int = None) -> None:
        """
        Ensure that a lifecycle rule exists to automatically delete expired objects.
        """
        expiration_days = expiration_days or self.ttl_days
        rules = {
            "Rules": [
                {
                    "ID": "auto-expire-objects",
                    "Filter": {"Prefix": ""},
                    "Status": "Enabled",
                    "Expiration": {"Days": expiration_days},
                }
            ]
        }
        self.client.put_bucket_lifecycle_configuration(
            Bucket=self.bucket,
            LifecycleConfiguration=rules,
        )

    def ensure_error_bucket(self) -> None:
        """
        Ensure that the error bucket exists with unlimited TTL (no lifecycle rules).
        """
        try:
            # Check if error bucket exists
            self.client.head_bucket(Bucket=self.error_bucket)
        except self.client.exceptions.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Create the error bucket
                try:
                    self.client.create_bucket(Bucket=self.error_bucket)
                    print(f"Created error bucket: {self.error_bucket}")
                except Exception as create_error:
                    print(f"Warning: Could not create error bucket {self.error_bucket}: {create_error}")
            else:
                print(f"Warning: Error checking error bucket {self.error_bucket}: {e}")
        except Exception as e:
            print(f"Warning: Could not check error bucket {self.error_bucket}: {e}")

    def ensure_cors_configuration(self) -> None:
        """
        Ensure that CORS rules exist to allow browser uploads.
        Uses wildcard origin for maximum compatibility with development environments.
        """
        cors_config = {
            'CORSRules': [
                {
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['GET', 'POST', 'PUT', 'HEAD', 'DELETE', 'OPTIONS'],
                    'AllowedOrigins': ['*'],  # Allow all origins for development and production
                    'ExposeHeaders': ['ETag', 'Content-Length', 'Content-Type', 'x-amz-request-id', 'x-amz-id-2'],
                    'MaxAgeSeconds': 3600
                }
            ]
        }

        try:
            self.client.put_bucket_cors(Bucket=self.bucket, CORSConfiguration=cors_config)
            print(f"[S3Storage] CORS configuration applied to bucket: {self.bucket}")
        except Exception as e:
            # Log but don't fail - CORS might not be critical in all environments
            print(f"Warning: Could not set CORS configuration: {e}")

    def presigned_upload_url(
        self, key: str, expires: int = 3600, object_ttl_days: int = None
    ) -> dict:
        """
        Generate a presigned POST URL for uploading.
        Note: R2 doesn't support the 'Expires' field in presigned POST, so we rely on bucket lifecycle rules for TTL.
        """
        # Removed 'Expires' and 'acl' fields - R2 returns 501 Not Implemented for these
        # R2 doesn't support ACLs or Expires in presigned POST
        # TTL is enforced via bucket lifecycle rules instead
        fields = {}
        conditions = []

        return self.external_client.generate_presigned_post(
            Bucket=self.bucket,
            Key=key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=expires,
        )

    def upload(self, local_path: str, key: str, expires_in_days: int = None, progress_callback=None) -> None:
        """
        Upload a file to S3/MinIO under the given key, enforcing object expiration.

        Args:
            local_path: Path to the file to upload
            key: S3 object key
            expires_in_days: Number of days until object expires
            progress_callback: Optional callback function that receives (bytes_transferred, total_bytes)
        """
        import os

        ttl_days = expires_in_days or self.ttl_days
        expiration_date = datetime.now(timezone.utc) + timedelta(days=ttl_days)

        # Get file size for progress logging
        file_size = os.path.getsize(local_path)
        print(f"[S3Upload] Starting upload: {key}, size: {file_size} bytes")

        # Create a progress callback that logs periodically
        last_logged_percent = 0

        def logging_callback(bytes_transferred):
            nonlocal last_logged_percent
            percent = (bytes_transferred / file_size) * 100

            # Log every 10% or if we reach 100%
            if percent >= last_logged_percent + 10 or percent >= 100:
                print(f"[S3Upload] Progress: {bytes_transferred}/{file_size} bytes ({percent:.1f}%) - {key}")
                last_logged_percent = int(percent // 10) * 10

            # Call original callback if provided
            if progress_callback:
                progress_callback(bytes_transferred)

        self.client.upload_file(
            Filename=local_path,
            Bucket=self.bucket,
            Key=key,
            ExtraArgs={
                "Expires": expiration_date,
            },
            Callback=logging_callback,
        )

        print(f"[S3Upload] Upload completed: {key}")

    def exists(self, key: str) -> bool:
        """
        Check if an object exists in the bucket.
        """
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except self.client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def list(self, prefix: str = "") -> list:
        """
        List keys under the given prefix.
        """
        resp = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        return [item["Key"] for item in resp.get("Contents", [])]

    def presigned_url(self, key: str, expires: int = 3600) -> str:
        """
        Generate a presigned GET URL for the specified object.
        """
        return self.external_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires,
        )

    def get_object_size(self, key: str) -> int:
        """
        Get the size of an S3 object in bytes.
        Returns 0 if the object doesn't exist or if there's an error.
        """
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=key)
            return response['ContentLength']
        except self.client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return 0
            raise
        except Exception:
            return 0

    def copy_to_error_bucket(self, source_key: str, error_key: str = None) -> str:
        """
        Copy a file from the main bucket to the error bucket with unlimited TTL.
        
        Args:
            source_key: The key of the file in the main bucket
            error_key: Optional custom key for the error bucket. If None, uses source_key
            
        Returns:
            The key used in the error bucket
        """
        if error_key is None:
            error_key = source_key
            
        try:
            # Copy source from main bucket to error bucket
            copy_source = {'Bucket': self.bucket, 'Key': source_key}
            
            self.client.copy_object(
                CopySource=copy_source,
                Bucket=self.error_bucket,
                Key=error_key,
                MetadataDirective='COPY'
            )
            
            print(f"Copied errored file to error bucket: {source_key} -> {error_key}")
            return error_key
            
        except Exception as e:
            print(f"Warning: Could not copy file to error bucket: {e}")
            return None

    def store_error_file(self, local_path: str, error_key: str) -> str:
        """
        Store a file directly to the error bucket with unlimited TTL.
        
        Args:
            local_path: Path to the local file to upload
            error_key: Key to use in the error bucket
            
        Returns:
            The key used in the error bucket
        """
        try:
            self.client.upload_file(
                Filename=local_path,
                Bucket=self.error_bucket,
                Key=error_key,
                ExtraArgs={
                    "ACL": "private",
                    # No expiration for error files - unlimited TTL
                }
            )
            
            print(f"Stored errored file in error bucket: {error_key}")
            return error_key
            
        except Exception as e:
            print(f"Warning: Could not store file in error bucket: {e}")
            return None

    def list_error_files(self, prefix: str = "") -> list:
        """
        List files in the error bucket under the given prefix.
        """
        try:
            resp = self.client.list_objects_v2(Bucket=self.error_bucket, Prefix=prefix)
            return [item["Key"] for item in resp.get("Contents", [])]
        except Exception as e:
            print(f"Warning: Could not list error files: {e}")
            return []

    def get_error_file_presigned_url(self, key: str, expires: int = 3600) -> str:
        """
        Generate a presigned GET URL for an error file.
        """
        try:
            return self.external_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.error_bucket, "Key": key},
                ExpiresIn=expires,
            )
        except Exception as e:
            print(f"Warning: Could not generate presigned URL for error file: {e}")
            return None

    def list_objects(self, prefix: str = "") -> list:
        """
        List all objects with a given prefix (alias for list method).
        """
        return self.list(prefix)

    def copy_object(self, source_key: str, dest_key: str) -> None:
        """
        Copy an object to a new location within the same bucket.
        """
        try:
            copy_source = {
                'Bucket': self.bucket,
                'Key': source_key
            }
            self.client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket,
                Key=dest_key
            )
        except Exception as e:
            raise Exception(f"Failed to copy {source_key} to {dest_key}: {str(e)}")

    def delete_object(self, key: str) -> None:
        """
        Delete an object from the bucket.
        """
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception as e:
            raise Exception(f"Failed to delete {key}: {str(e)}")

    def initiate_multipart_upload(self, key: str, expires_in_days: int = None) -> str:
        """
        Initiate a multipart upload to S3.

        Args:
            key: S3 object key
            expires_in_days: Number of days until object expires

        Returns:
            Upload ID for the multipart upload
        """
        ttl_days = expires_in_days or self.ttl_days
        expiration_date = datetime.now(timezone.utc) + timedelta(days=ttl_days)

        response = self.client.create_multipart_upload(
            Bucket=self.bucket,
            Key=key,
            ACL='private',
            Expires=expiration_date
        )

        upload_id = response['UploadId']
        print(f"[S3Multipart] Initiated multipart upload: {key}, upload_id: {upload_id}")
        return upload_id

    def generate_multipart_part_url(self, key: str, upload_id: str, part_number: int, expires: int = 3600) -> str:
        """
        Generate a presigned URL for uploading a single part in a multipart upload.

        Args:
            key: S3 object key
            upload_id: The multipart upload ID
            part_number: Part number (1-indexed, max 10,000)
            expires: URL expiration time in seconds

        Returns:
            Presigned URL for PUT request
        """
        return self.external_client.generate_presigned_url(
            'upload_part',
            Params={
                'Bucket': self.bucket,
                'Key': key,
                'UploadId': upload_id,
                'PartNumber': part_number
            },
            ExpiresIn=expires
        )

    def complete_multipart_upload(self, key: str, upload_id: str, parts: list) -> dict:
        """
        Complete a multipart upload by combining all uploaded parts.

        Args:
            key: S3 object key
            upload_id: The multipart upload ID
            parts: List of dicts with 'PartNumber' and 'ETag' keys
                   Example: [{'PartNumber': 1, 'ETag': '"abc123"'}, ...]

        Returns:
            S3 response with Location, Bucket, Key, ETag
        """
        # Sort parts by PartNumber to ensure correct order
        sorted_parts = sorted(parts, key=lambda x: x['PartNumber'])

        response = self.client.complete_multipart_upload(
            Bucket=self.bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={'Parts': sorted_parts}
        )

        print(f"[S3Multipart] Completed multipart upload: {key}, {len(parts)} parts")
        return response

    def abort_multipart_upload(self, key: str, upload_id: str) -> None:
        """
        Abort a multipart upload and cleanup uploaded parts.

        Args:
            key: S3 object key
            upload_id: The multipart upload ID
        """
        try:
            self.client.abort_multipart_upload(
                Bucket=self.bucket,
                Key=key,
                UploadId=upload_id
            )
            print(f"[S3Multipart] Aborted multipart upload: {key}, upload_id: {upload_id}")
        except Exception as e:
            print(f"[S3Multipart] Warning: Could not abort multipart upload {upload_id}: {e}")
