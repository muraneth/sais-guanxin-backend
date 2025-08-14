# 这个 base 镜像太大了，所以换成了 python 的镜像
# FROM swr.cn-north-9.myhuaweicloud.com/infly-dev/health-ai-search-base:0.1
# FROM swr.cn-north-9.myhuaweicloud.com/infly-dev/python:3.10-slim-bookworm
FROM python:3.10-slim-bookworm
# FROM --platform=linux/amd64 python:3.10-slim-bookworm


USER root
COPY ./backend /app/backend

WORKDIR /app/backend

# RUN cd /app/backend && python3 -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --extra-index-url http://nexus.infly.tech:8081/repository/inf-pypi/simple --trusted-host nexus.infly.tech
RUN cd /app/backend && python3 -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

