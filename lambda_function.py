import pulumi
import pulumi_aws as aws
from utils import tags
from iam import lambda_role
from s3 import cv_bucket
from vpc import private_subnet_1, private_subnet_2, lambda_sg

upload_cv_lambda = aws.lambda_.Function("upload-cv-lambda",
    runtime="python3.9",
    handler="upload_cv.lambda_handler",
    role=lambda_role.arn,
    code=pulumi.AssetArchive({
        ".": pulumi.FileArchive("./lambdas")
    }),
    environment={
        "variables": {
            "S3_BUCKET_NAME": cv_bucket.bucket
        }
    },
    vpc_config={
        "subnet_ids": [private_subnet_1.id, private_subnet_2.id],
        "security_group_ids": [lambda_sg.id]
    },
    tags=tags
)