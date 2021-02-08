FROM arm32v7/python

COPY requirements.txt /

RUN apt-get update && apt-get install -y vim
RUN apt install -y ffmpeg
RUN pip install -r requirements.txt
RUN cd / && pip install -r requirements.txt

WORKDIR /bot
