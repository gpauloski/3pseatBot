from python:3.11-slim-buster

RUN apt update
RUN apt -y install build-essential ffmpeg git

COPY . /bot

WORKDIR /bot
RUN pip install .

EXPOSE 5000

CMD [ "python", "-m", "threepseat", "--config", "/data/config.json", "--log-dir", "/data/logs" ]
