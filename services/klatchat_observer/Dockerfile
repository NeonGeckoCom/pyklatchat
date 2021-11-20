FROM python:3.8

ADD . /klatchat_observer
WORKDIR .
RUN apt-get update && \
    apt-get install -y \
    gcc \
    python3  \
    python3-dev  \
    && pip install wheel  \
    && pip install .

ENV NEON_CONFIG_PATH /config

CMD ["klatchat_observer"]