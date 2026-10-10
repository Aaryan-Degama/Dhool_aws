# Base image on 10 Oct 2026, to pin when builds must repeat exactly:
#   public.ecr.aws/lambda/python:3.12@sha256:145350008f3f67d82c0bc6ecd34d9eb0c95aecf11f9b69db6bab7de3d5d3cc61
FROM public.ecr.aws/lambda/python:3.12
COPY requirements-analysis.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements-analysis.txt
COPY dhool/ ${LAMBDA_TASK_ROOT}/dhool/
COPY handlers/ ${LAMBDA_TASK_ROOT}/handlers/
CMD ["handlers.analysis.handler"]
