# The vendor-reply reader: Laya (Apache-2.0), fine-tuned on messages/vendor-replies.jsonl and shrunk to 8-bit
# weights (v3.2), run by ONNX Runtime on CPU in one Lambda.
#   The weights come from scripts/laya-tune.py into messages/models/ and are not kept in git (checkpoints.md).

# Base image on 10 Oct 2026, to pin when builds must repeat exactly:
#   public.ecr.aws/lambda/python:3.12@sha256:145350008f3f67d82c0bc6ecd34d9eb0c95aecf11f9b69db6bab7de3d5d3cc61
FROM public.ecr.aws/lambda/python:3.12
# PyTorch is here only because the laya package imports it; the model runs in ONNX Runtime.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.14.1 \
 && pip install --no-cache-dir laya==0.3.24 onnxruntime==1.30.0 transformers==5.18.0 safetensors==0.8.0
# The weights must be readable by everyone (chmod -R a+rX messages/models): Lambda does not run as the file owner.
COPY models/vendor-replies-v3.2-int8/ /opt/model/
COPY reply_handler.py ${LAMBDA_TASK_ROOT}/
CMD ["reply_handler.handler"]
