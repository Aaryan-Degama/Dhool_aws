# The vendor-reply reader: Laya (Apache-2.0), fine-tuned on messages/vendor-replies.jsonl and shrunk to 8-bit
# weights (v3.2), run by ONNX Runtime on CPU in one Lambda.
#   The weights come from scripts/laya-tune.py into messages/models/ and are not kept in git (checkpoints.md).

# Base image on 10 Oct 2026, to pin when builds must repeat exactly:
#   public.ecr.aws/lambda/python:3.12@sha256:145350008f3f67d82c0bc6ecd34d9eb0c95aecf11f9b69db6bab7de3d5d3cc61
FROM public.ecr.aws/lambda/python:3.14
COPY constraints.txt ${LAMBDA_TASK_ROOT}/
# constraints.txt is requirements.txt worked out in full, each package with its published SHA-256 hashes, for
# the reasons given in backend/Dockerfile (no searching for versions; any mirror may serve the files). Regenerate:
#   uv pip compile messages/requirements.txt --python-version 3.12 --python-platform x86_64-manylinux_2_28 \
#     --no-header --generate-hashes --extra-index-url https://download.pytorch.org/whl/cpu \
#     --index-strategy unsafe-best-match -o messages/constraints.txt
# PyTorch (the CPU build, from PyTorch's own index) is here only because the laya package imports it; the model
# runs in ONNX Runtime.
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN pip install --no-cache-dir --timeout 120 --retries 10 --require-hashes -r constraints.txt \
      --extra-index-url https://download.pytorch.org/whl/cpu
# The weights must be readable by everyone (chmod -R a+rX messages/models): Lambda does not run as the file owner.
COPY models/vendor-replies-v3.2-int8/ /opt/model/
COPY reply_handler.py ${LAMBDA_TASK_ROOT}/
CMD ["reply_handler.handler"]
