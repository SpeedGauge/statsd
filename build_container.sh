#!/bin/bash

set -e

BRANCH=${1:-master}
PUSH=${2:-false}

HOST="320353726149.dkr.ecr.us-east-1.amazonaws.com"
REGION="us-east-1"
REPO="sg/statsd"

$(aws ecr get-login --no-include-email --region $REGION)

docker build --pull -t $HOST/$REPO -t $HOST/$REPO:$BRANCH .

# (optionally) push the images
if [ "false" != "$PUSH" ]; then
    docker push $HOST/$REPO:$BRANCH
fi
