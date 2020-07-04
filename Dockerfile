FROM arm32v7/python

WORKDIR /bot/3pseatBot

RUN apt-get update && apt-get install -y vim
RUN apt-get install -y ffmpeg x264
RUN pip install pynacl
RUN pip install discord.py
RUN pip install tinydb
RUN pip install python-dotenv
RUN pip install emoji

CMD ["python", "main.py"]
