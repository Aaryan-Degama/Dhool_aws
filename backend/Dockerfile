# Base image on 10 Oct 2026, to pin when builds must repeat exactly:
#   public.ecr.aws/lambda/python:3.12@sha256:145350008f3f67d82c0bc6ecd34d9eb0c95aecf11f9b69db6bab7de3d5d3cc61
FROM public.ecr.aws/lambda/python:3.12
COPY requirements-analysis.txt constraints-analysis.txt ${LAMBDA_TASK_ROOT}/
# constraints-analysis.txt names the exact version of everything the four requirements pull in. Without it pip
# had to choose versions itself, and on 10 Oct 2026 it went back through every release of aiohttp (181
# downloads) until one timed out. Regenerate it when a requirement changes:
#   uv pip compile backend/requirements-analysis.txt --python-version 3.12 \
#     --python-platform x86_64-manylinux_2_28 --no-header -o backend/constraints-analysis.txt
# A slow line (a campus proxy) must not fail the build either: pip waits 120 s for a read and tries 10 times.
RUN pip install --no-cache-dir --timeout 120 --retries 10 -r requirements-analysis.txt -c constraints-analysis.txt
COPY dhool/ ${LAMBDA_TASK_ROOT}/dhool/
COPY handlers/ ${LAMBDA_TASK_ROOT}/handlers/
CMD ["handlers.analysis.handler"]
