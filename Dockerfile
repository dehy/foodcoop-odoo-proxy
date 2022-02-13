FROM alpine:3.15

RUN apk add --no-cache --update python3 py3-pip && adduser -h /app -H -D app
ADD --chown=app:app src/ /app

USER app
WORKDIR /app

RUN pip3 install --no-cache-dir -r requirements.txt

ENTRYPOINT ["/app/.local/bin/flask", "run"]