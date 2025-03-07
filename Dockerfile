FROM python:3.9-slim-buster AS builder

RUN apt update && apt install -y \
    make \
    swig \
    g++ \
    libatlas-base-dev \
    portaudio19-dev \
    git

WORKDIR /src

RUN git clone --depth 1 https://github.com/xiaoxiaolai/snowboy.git && \
    cd snowboy/swig/Python3 && \
    make

COPY requirements.txt .

RUN pip install -r requirements.txt

FROM python:3.9-slim-buster

WORKDIR /app

RUN apt update && apt install -y \
    libatlas-base-dev \
    portaudio19-dev \
    libopus0 \
    pulseaudio

COPY --from=builder /usr/local/lib/python3.9/site-packages/ /usr/local/lib/python3.9/site-packages/
COPY . .
COPY --from=builder /src/snowboy/swig/Python3/_snowboydetect.* /app/snowboy/
COPY --from=builder /src/snowboy/swig/Python3/snowboydetect.py /app/snowboy/snowboydetect.py

CMD ["python", "app.py"]