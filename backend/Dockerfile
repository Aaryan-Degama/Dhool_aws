FROM public.ecr.aws/lambda/python:3.12
COPY requirements-analysis.txt .
RUN pip install --no-cache-dir -r requirements-analysis.txt
COPY dhool/ ${LAMBDA_TASK_ROOT}/dhool/
COPY handlers/ ${LAMBDA_TASK_ROOT}/handlers/
CMD ["handlers.analysis.handler"]
