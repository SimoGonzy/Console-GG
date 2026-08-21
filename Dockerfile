FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        python3 \
        python3-pip \
        python3-venv \
        ttyd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY console_gg ./console_gg

RUN python3 -m venv /opt/console-gg-venv \
    && /opt/console-gg-venv/bin/python -m pip install --no-cache-dir --upgrade pip \
    && /opt/console-gg-venv/bin/python -m pip install --no-cache-dir -e /app \
    && useradd --system --home /data --shell /usr/sbin/nologin consolegg \
    && mkdir -p /data \
    && chown -R consolegg:consolegg /data

ENV CONSOLE_GG_STATS_PATH=/data/console_gg_stats.json
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TERM=xterm-256color
ENV CONSOLE_GG_TTYD_CREDENTIAL=

EXPOSE 7681

USER consolegg

CMD ["/bin/bash", "-lc", "args=(--writable --interface 0.0.0.0 --port 7681); if [ -n \"${CONSOLE_GG_TTYD_CREDENTIAL:-}\" ]; then args+=(--credential \"$CONSOLE_GG_TTYD_CREDENTIAL\"); fi; exec ttyd \"${args[@]}\" /opt/console-gg-venv/bin/console-gg"]
