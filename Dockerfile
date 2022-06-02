FROM ubuntu:21.10

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Paris

RUN apt update && apt-get install -y --no-install-recommends python3 python3-pip && \
    useradd --home-dir /app --no-create-home app && \
    rm -rf /var/cache/apt

ADD requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

ADD --chown=app:app src/ /app
WORKDIR /app
USER app

ENV ENV_FILE=.env

ENTRYPOINT ["flask", "run", "--host=0.0.0.0"]