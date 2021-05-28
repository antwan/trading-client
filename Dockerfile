FROM alpine
FROM python:3.7

ENV PATH /usr/local/bin:$PATH

COPY requirements.txt /tmp
WORKDIR /tmp
RUN pip install --upgrade pip && \
    pip install -r requirements.txt
ENV PYTHONPATH "${PYTHONPATH}:/app"

COPY ./src /app/src
COPY ./tests /app/tests
WORKDIR /app