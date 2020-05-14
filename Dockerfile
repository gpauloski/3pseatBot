FROM arm32v7/python

WORKDIR /bot/3pseatbot

RUN apt-get update && apt-get install -y vim
RUN pip install discord.py
RUN pip install tinydb
RUN pip install python-dotenv
RUN pip install emoji

CMD ["python", "main.py"]
