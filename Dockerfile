FROM arm32v7/python

WORKDIR /bot

RUN apt-get update && apt-get install -y vim
RUN apt install -y ffmpeg
RUN pip install -e .