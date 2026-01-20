#!/usr/bin/env python3
"""
Script to configure CORS on the S3/Object Storage bucket.
This needs to be run once to enable browser uploads with presigned URLs.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.storage.s3_storage import S3Storage


def main():
    print("[CORS Setup] Initializing S3 storage...")
    s3 = S3Storage()

    print(f"[CORS Setup] Applying CORS configuration to bucket: {s3.bucket}")

    try:
        s3.ensure_cors_configuration()
        print("[CORS Setup] ✓ CORS configuration applied successfully")

        # Verify the configuration
        print("[CORS Setup] Verifying CORS configuration...")
        cors_config = s3.client.get_bucket_cors(Bucket=s3.bucket)
        print(f"[CORS Setup] Current CORS rules:")
        for i, rule in enumerate(cors_config.get("CORSRules", []), 1):
            print(f"  Rule {i}:")
            print(f"    Allowed Origins: {rule.get('AllowedOrigins', [])}")
            print(f"    Allowed Methods: {rule.get('AllowedMethods', [])}")
            print(f"    Allowed Headers: {rule.get('AllowedHeaders', [])}")
            print(f"    Expose Headers: {rule.get('ExposeHeaders', [])}")
            print(f"    Max Age: {rule.get('MaxAgeSeconds', 'N/A')} seconds")

        print("\n[CORS Setup] ✓ Setup completed successfully")
        return 0

    except Exception as e:
        print(f"[CORS Setup] ✗ Error applying CORS configuration: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
