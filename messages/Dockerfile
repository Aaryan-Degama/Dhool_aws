# The vendor-reply reader: Laya (Apache-2.0), fine-tuned on messages/vendor-replies.jsonl, on CPU in one Lambda.
#   The weights come from scripts/laya-tune.py into messages/models/ and are not kept in git (checkpoints.md).

FROM public.ecr.aws/lambda/python:3.12
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.14.1 \
 && pip install --no-cache-dir laya==0.3.24 transformers==5.18.0 safetensors==0.8.0
# The weights must be readable by everyone (chmod -R a+rX messages/models): Lambda does not run as the file owner.
COPY models/vendor-replies-v3/ /opt/model/
COPY reply_handler.py ${LAMBDA_TASK_ROOT}/
CMD ["reply_handler.handler"]
