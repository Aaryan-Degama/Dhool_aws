# Base image on 10 Oct 2026, to pin when builds must repeat exactly:
#   public.ecr.aws/lambda/python:3.12@sha256:145350008f3f67d82c0bc6ecd34d9eb0c95aecf11f9b69db6bab7de3d5d3cc61
FROM public.ecr.aws/lambda/python:3.12
COPY constraints-analysis.txt ${LAMBDA_TASK_ROOT}/
# constraints-analysis.txt is requirements-analysis.txt worked out in full: the exact version of everything the
# four requirements pull in, each with the SHA-256 hashes PyPI publishes for it. Two reasons:
#   - Left to choose versions, pip went back through every release of aiohttp (181 downloads) on 10 Oct 2026
#     until one timed out, and the build failed three times.
#   - With the hashes checked, the files may come from any mirror: one that served something else would be
#     refused. PyPI's own file server gave 45 kB/s behind the campus proxy that day and a mirror 1.2 MB/s.
# Regenerate it when a requirement changes:
#   uv pip compile backend/requirements-analysis.txt --python-version 3.12 \
#     --python-platform x86_64-manylinux_2_28 --no-header --generate-hashes -o backend/constraints-analysis.txt
# PIP_INDEX_URL is where pip looks; PyPI unless the build says otherwise (Metadata.DockerBuildArgs in template.yaml).
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN pip install --no-cache-dir --timeout 120 --retries 10 --require-hashes -r constraints-analysis.txt
COPY dhool/ ${LAMBDA_TASK_ROOT}/dhool/
COPY handlers/ ${LAMBDA_TASK_ROOT}/handlers/
CMD ["handlers.analysis.handler"]
