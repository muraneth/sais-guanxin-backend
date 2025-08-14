#!/bin/bash

set -e

# IMAGE_NAME='inf-repo-registry.cn-wulanchabu.cr.aliyuncs.com/infly/knowledge-assistant'
# IMAGE_TAG=$(git log --pretty=format:"%h" -n 1)
IMAGE_NAME='health-ai-search-backend'
IMAGE_TAG=1.0.3

docker build -t "$IMAGE_NAME:$IMAGE_TAG" -f Dockerfile .

# sudo -u admin docker push "$IMAGE_NAME:$IMAGE_TAG"

# echo "finish docker build and push with IMAGE_TAG: ${IMAGE_TAG}"
