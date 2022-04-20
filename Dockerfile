FROM python:3.8

USER root

WORKDIR /backtest-app

COPY requirements.txt ./
COPY backtest_program.py ./backtest_program.py
COPY program ./program

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

CMD ["python3","-u","backtest_program.py"]