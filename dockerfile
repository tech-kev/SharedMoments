FROM python:3.9

WORKDIR /app

COPY ./frontend ./frontend

COPY ./backend  ./backend

COPY ./locales  ./locales

RUN mkdir -p ./upload/feed_items/

RUN mkdir -p ./upload/stock_items/

RUN mkdir -p ./logs/

RUN mkdir -p ./data_transfer/

RUN mkdir -p ./keys/

COPY requirements.txt .

COPY LICENSE .

RUN pip install --no-cache-dir -r requirements.txt

COPY docker_startup.sh .

CMD ["/bin/sh", "docker_startup.sh"]