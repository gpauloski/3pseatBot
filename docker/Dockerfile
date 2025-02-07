from python:3.12-slim-buster

RUN :\
    && apt-get update -y \
    && apt-get install -y --no-install-recommends \
        build-essential opus-tools ffmpeg git \
    && apt-get clean autoclean \
    && rm -rf /var/lib/apt/lists/*

COPY . /bot

WORKDIR /bot
RUN pip install .

EXPOSE 5000

CMD [ "python", "-m", "threepseat", "--config", "/data/config.json", "--log-dir", "/data/logs" ]
