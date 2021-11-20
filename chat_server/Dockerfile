FROM python:3.8

ADD . /chat_server
WORKDIR .
RUN apt-get update && \
    apt-get install -y \
    gcc \
    python3  \
    python3-dev  \
    && pip install wheel  \
    && pip install .

ENV NEON_CONFIG_PATH /config

CMD ["chat_server"]