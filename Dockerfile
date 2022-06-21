FROM python:3.10-bullseye

RUN apt-get update
RUN apt-get install -y ffmpeg vim

RUN git clone https://github.com/gpauloski/3pseatBot /bot
WORKDIR /bot
RUN pip install -e .

EXPOSE 5000

CMD ["python", "run.py", "--config", "/data/config.json"]
