FROM python:3.8

USER root

WORKDIR /backtest-app

COPY requirements.txt ./
COPY backtest.py ./backtest.py
COPY program ./program
COPY Data ./Data
COPY ../Historical_Data ./Data/Historical_Data

RUN apt-get update && apt-get --no-install-recommends -y install python3-dev python3-pandas

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

RUN wget http://nav.dl.sourceforge.net/project/ta-lib/ta-lib/0.4.0/ta-lib-0.4.0-src.tar.gz && \
  tar -xvzf ta-lib-0.4.0-src.tar.gz && \
  cd ta-lib/ && \
  ./configure --prefix=/usr && \
  make && \
  make install \
  && pip3 install ta-lib

ENTRYPOINT python3 backtest.py