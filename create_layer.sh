#!/bin/bash

# Ensure script fails on any error
set -e

echo "Building Lambda layer..."

# Create temporary Dockerfile
cat << 'EOF' > Dockerfile.tmp
FROM public.ecr.aws/lambda/python:3.9

# Install system dependencies
RUN yum install -y gcc gcc-c++ python3-devel libffi-devel openssl-devel make

# Set working directory
WORKDIR /layer

# Copy requirements file
COPY requirements.txt .

# Create python directory structure for the layer
RUN mkdir -p python/lib/python3.9/site-packages

# Install Python packages with correct architecture
ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1
RUN pip install --platform manylinux2014_x86_64 \
    --implementation cp \
    --python 3.9 \
    --only-binary=:all: \
    --target python/lib/python3.9/site-packages \
    -r requirements.txt

# Create the layer zip file
RUN zip -r layer.zip python/
EOF

# Build the Docker image with platform specification
docker build --platform linux/amd64 -t lambda-layer-builder -f Dockerfile.tmp .

# Create a container from the image
container_id=$(docker create lambda-layer-builder)

# Copy the layer.zip from the container
docker cp $container_id:/layer/layer.zip .

# Clean up
docker rm $container_id
rm Dockerfile.tmp

echo "Lambda layer has been built successfully!"
echo "The layer.zip file is ready to be uploaded to AWS Lambda."