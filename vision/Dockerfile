# The screenshot reader: a small vision model on CPU, inside one Lambda.
#   llama.cpp (MIT) is built from a pinned release; it serves Qwen3-VL-2B-Instruct (Apache-2.0, 4-bit).
#   The weights come from scripts/fetch-model.sh into vision/models/ and are not kept in git.

FROM public.ecr.aws/lambda/python:3.12 AS build
RUN dnf install -y gcc gcc-c++ cmake git make && dnf clean all
ARG LLAMA_TAG=b11351
RUN git clone --depth 1 --branch ${LLAMA_TAG} https://github.com/ggml-org/llama.cpp /src
# Lambda's x86 CPUs all have AVX2; no -march=native, so the binary does not depend on the build machine.
RUN cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
      -DGGML_NATIVE=OFF -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON -DGGML_BMI2=ON -DGGML_OPENMP=OFF \
      -DLLAMA_CURL=OFF -DLLAMA_OPENSSL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF \
 && cmake --build /build --target llama-server -j "$(nproc)"

FROM public.ecr.aws/lambda/python:3.12
COPY --from=build /build/bin/llama-server /opt/llama-server
COPY models/ /opt/models/
COPY screenshot_reader.py vision_handler.py ${LAMBDA_TASK_ROOT}/
CMD ["vision_handler.handler"]
