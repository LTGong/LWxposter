#https://www.varokas.com/aws-lambda-docker/
docker build -t lwx-img-2 . #rebuild docker #docker build -t lwx-img-2 . --no-cache
aws ecr get-login-password | docker login --username AWS --password-stdin 122157976477.dkr.ecr.us-east-1.amazonaws.com #login
docker tag lwx-img-2:latest 122157976477.dkr.ecr.us-east-1.amazonaws.com/lwx-repo:latest
docker push 122157976477.dkr.ecr.us-east-1.amazonaws.com/lwx-repo:latest
aws lambda update-function-code \
    --function-name dkr-lwx \
    --image-uri 122157976477.dkr.ecr.us-east-1.amazonaws.com/lwx-repo:latest
