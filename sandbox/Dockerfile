# Trusted operator must supply an approved digest-pinned base.
# Example shape: --build-arg PYTHON_BASE=python:3.13-slim@sha256:<approved-manifest>
# No base image was pulled or verified during this audit.
ARG PYTHON_BASE
FROM ${PYTHON_BASE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8
USER 65534:65534
WORKDIR /tmp
ENTRYPOINT ["python"]
