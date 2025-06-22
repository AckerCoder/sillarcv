import pulumi
import pulumi_aws as aws
import json
from utils import tags

dynamo_table = aws.dynamodb.Table("applications",
    attributes=[
        {"name": "pk", "type": "S"},
        {"name": "sk", "type": "S"},
    ],
    hash_key="pk",
    range_key="sk",
    billing_mode="PAY_PER_REQUEST",
    tags=tags
)
