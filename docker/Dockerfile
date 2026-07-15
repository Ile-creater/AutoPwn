FROM python:3.13-slim

LABEL org.opencontainers.image.description="AutoPwn Agent Sandbox"

# 基础工具链
RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils \
    binwalk \
    file \
    foremost \
    libimage-exiftool-perl \
    xxd \
    zstd \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
RUN pip install --no-cache-dir \
    pwntools \
    requests

# 把 agent 代码打进镜像
COPY agents/ /app/agents/
WORKDIR /app

# 默认：无网络、有限资源
CMD ["python", "-c", "print('AutoPwn sandbox ready')"]
