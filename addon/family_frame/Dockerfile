# Built on the Home Assistant machine by the Supervisor (local add-on).
# A plain Python image: Pillow and friends install from prebuilt wheels for the
# Raspberry Pi (aarch64), so the build takes a few minutes, not an hour.
ARG BUILD_FROM
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY web ./web
COPY packs ./packs
COPY themes ./themes
COPY config ./config
COPY local ./local
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
