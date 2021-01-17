FROM arm32v7/python

WORKDIR /bot/3pseatBot

RUN apt-get update && apt-get install -y vim
RUN apt-get install -y ffmpeg x264
RUN pip install pynacl
RUN pip install discord.py --upgrade
RUN pip install tinydb
RUN pip install python-dotenv
RUN pip install emoji
RUN pip install youtube-dl

CMD ["python", "main.py"]
