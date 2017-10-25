FROM node:6-alpine
RUN apk add --no-cache python3-dev && \
    python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --upgrade pip setuptools && \
    pip3 install jinja2-cli && \
    rm -r /root/.cache

COPY . /opt/statsd/
WORKDIR /opt/statsd/

EXPOSE 8125/udp
EXPOSE 8126

CMD "/opt/statsd/docker_entrypoint.sh"
