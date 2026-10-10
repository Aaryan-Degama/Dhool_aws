# The screenshot reader: a small vision model on CPU, inside one Lambda.
#   llama.cpp (MIT) is built from a pinned release; it serves Qwen3-VL-2B-Instruct (Apache-2.0, 4-bit).
#   The weights come from scripts/fetch-model.sh into vision/models/ and are not kept in git.

# Base image on 10 Oct 2026, to pin when builds must repeat exactly:
#   public.ecr.aws/lambda/python:3.12@sha256:145350008f3f67d82c0bc6ecd34d9eb0c95aecf11f9b69db6bab7de3d5d3cc61
FROM public.ecr.aws/lambda/python:3.12 AS build
# No package versions: Amazon Linux's repository is locked to the base image's release, which fixes them.
# hadolint ignore=DL3041
RUN dnf install -y gcc gcc-c++ cmake git make && dnf clean all
# Fetched by commit, not by tag: a tag can be moved to other code, a commit cannot. This one is tag b11351.
ARG LLAMA_SHA=631109b34da437a3c4a5ebd75091d677671392e3
RUN git init -q /src && git -C /src fetch -q --depth 1 https://github.com/ggml-org/llama.cpp ${LLAMA_SHA} \
 && git -C /src checkout -q FETCH_HEAD
# Lambda's x86 CPUs all have AVX2; no -march=native, so the binary does not depend on the build machine.
RUN cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
      -DGGML_NATIVE=OFF -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON -DGGML_BMI2=ON -DGGML_OPENMP=OFF \
      -DLLAMA_CURL=OFF -DLLAMA_OPENSSL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF \
 && cmake --build /build --target llama-server -j "$(nproc)"

# Tesseract (Apache-2.0) and Leptonica (BSD-2-Clause), from pinned releases: the Lambda base has no package for
# them. Read first, in about a second; the model is the fallback (see reader.py).
FROM public.ecr.aws/lambda/python:3.12 AS tess
# No package versions: Amazon Linux's repository is locked to the base image's release, which fixes them.
# hadolint ignore=DL3041
RUN dnf install -y gcc gcc-c++ cmake git make libpng-devel libjpeg-turbo-devel zlib-devel && dnf clean all
# The commits behind the tags 1.85.0 (Leptonica) and 5.5.1 (Tesseract).
ARG LEPTONICA_SHA=63aef18d98432b8582a1565e241f7bd2ee9cc8d9
ARG TESSERACT_SHA=3b7c70e34dea179549ed3e995872e2e019eb8477
RUN git init -q /lept && git -C /lept fetch -q --depth 1 https://github.com/DanBloomberg/leptonica ${LEPTONICA_SHA} \
 && git -C /lept checkout -q FETCH_HEAD \
 && cmake -S /lept -B /lept/build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/opt/tess -DBUILD_SHARED_LIBS=OFF \
      -DBUILD_PROG=OFF -DENABLE_GIF=OFF -DENABLE_TIFF=OFF -DENABLE_WEBP=OFF -DENABLE_OPENJPEG=OFF \
 && cmake --build /lept/build -j "$(nproc)" --target install
RUN git init -q /tess && git -C /tess fetch -q --depth 1 https://github.com/tesseract-ocr/tesseract ${TESSERACT_SHA} \
 && git -C /tess checkout -q FETCH_HEAD \
 && cmake -S /tess -B /tess/build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/opt/tess -DCMAKE_PREFIX_PATH=/opt/tess \
      -DBUILD_SHARED_LIBS=OFF -DBUILD_TRAINING_TOOLS=OFF -DOPENMP_BUILD=OFF -DDISABLE_CURL=ON -DDISABLE_ARCHIVE=ON \
      -DDISABLE_TIFF=ON -DGRAPHICS_DISABLED=ON \
 && cmake --build /tess/build -j "$(nproc)" --target install
# English, the "fast" model (Apache-2.0), pinned by tag and checked by hash.
# No pipefail: the pipe ends in the check itself, and the echo before it cannot fail.
# hadolint ignore=DL4006
RUN mkdir -p /opt/tess/share/tessdata \
 && curl -fsSL -o /opt/tess/share/tessdata/eng.traineddata https://github.com/tesseract-ocr/tessdata_fast/raw/4.1.0/eng.traineddata \
 && echo "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2  /opt/tess/share/tessdata/eng.traineddata" | sha256sum -c

FROM public.ecr.aws/lambda/python:3.12
COPY --from=build /build/bin/llama-server /opt/llama-server
COPY models/ /opt/models/
# After the 1.5 GB of weights, so changing anything below does not upload them again.
RUN pip install --no-cache-dir pillow==12.3.0
# No package versions: Amazon Linux's repository is locked to the base image's release, which fixes them.
# hadolint ignore=DL3041
RUN dnf install -y libpng libjpeg-turbo && dnf clean all
COPY --from=tess /opt/tess /opt/tess
ENV TESSERACT=/opt/tess/bin/tesseract TESSDATA_PREFIX=/opt/tess/share/tessdata
COPY screenshot_reader.py ocr_reader.py reader.py vision_handler.py ${LAMBDA_TASK_ROOT}/
CMD ["vision_handler.handler"]
