FROM python:3.12-slim
ARG S6_OVERLAY_VERSION=3.2.0.0
RUN apt-get update && apt-get install -y --no-install-recommends curl xz-utils && rm -rf /var/lib/apt/lists/*
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz /tmp/s6-overlay-noarch.tar.xz
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz /tmp/s6-overlay-x86_64.tar.xz
RUN tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz && tar -C / -Jxpf /tmp/s6-overlay-x86_64.tar.xz && rm /tmp/*.tar.xz
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY app/ /app/
COPY s6-overlay/ /etc/s6-overlay/
RUN find /etc/s6-overlay/s6-rc.d -name 'run' -o -name 'finish' | xargs chmod +x
ENV PYTHONPATH=/app
VOLUME ["/data"]
EXPOSE 7861
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 CMD curl -f http://localhost:7861/health || exit 1
ENTRYPOINT ["/init"]
