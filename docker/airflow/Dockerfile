FROM apache/airflow:2.10.4-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
USER airflow

COPY requirements.txt /requirements.txt
RUN grep -v '^records==' /requirements.txt > /tmp/requirements-main.txt \
    && pip install --no-cache-dir -r /tmp/requirements-main.txt \
    && pip install --no-cache-dir --no-deps records==0.6.0
