import pulumi
import pulumi_aws as aws
import json
from utils import tags

dynamo_table = aws.dynamodb.Table("applications",
    attributes=[
        {"name": "cv_file", "type": "S"},  # Primary key - S3 key of the CV file
        {"name": "analyzed_at", "type": "S"},  # Sort key - Lambda ARN + timestamp
        {"name": "name", "type": "S"},  # For the NameIndex
        {"name": "email", "type": "S"}   # For the EmailIndex
    ],
    hash_key="cv_file",
    range_key="analyzed_at",
    billing_mode="PAY_PER_REQUEST",
    global_secondary_indexes=[
        {
            "name": "EmailIndex",
            "hash_key": "email",
            "range_key": "name",
            "projection_type": "ALL",
            "read_capacity": 0,
            "write_capacity": 0
        },
        {
            "name": "NameIndex",
            "hash_key": "name",
            "range_key": "email",
            "projection_type": "ALL",
            "read_capacity": 0,
            "write_capacity": 0
        }
    ],
    tags=tags
)
