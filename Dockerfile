FROM public.ecr.aws/lambda/python:3.9

COPY lambda_function.py .
COPY requirements.txt requirements.txt
CMD ["pip3 install -t ./python -r  requirements.txt"]
RUN pip3 install facebook-sdk
RUN pip3 install markdownify
RUN pip3 install requests
COPY . .
CMD ["lambda_function.handler"]
