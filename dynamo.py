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
    stream_enabled=True,
    stream_view_type="NEW_IMAGE",  # Solo necesitamos la nueva imagen del registro
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

# Export the stream ARN for use in the notification Lambda
pulumi.export("dynamo_stream_arn", dynamo_table.stream_arn)
