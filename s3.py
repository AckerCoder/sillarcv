import pulumi
import pulumi_aws as aws
from utils import tags

cv_bucket = aws.s3.Bucket("cv-bucket",
    bucket="mis-postulaciones-cv",
    acl="private",
    force_destroy=True,
    versioning={
        "enabled": True
    },
    server_side_encryption_configuration={
        "rule": {
            "apply_server_side_encryption_by_default": {
                "sse_algorithm": "AES256"
            }
        }
    },
    tags=tags
)

cv_bucket_public_access_block = aws.s3.BucketPublicAccessBlock("cv-bucket-public-access-block",
    bucket=cv_bucket.id,
    block_public_acls=True,
    block_public_policy=True,
    ignore_public_acls=True,
    restrict_public_buckets=True
)