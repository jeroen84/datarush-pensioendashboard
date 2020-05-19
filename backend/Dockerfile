FROM python:3.7

WORKDIR /backend

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY marketdata.py /backend/
COPY __init__.py /backend/
COPY websitesDgr.py /backend/

VOLUME /backend/db/
VOLUME /backend/log/

ENTRYPOINT [ "python ]

CMD [ "/backend/__init__.py"]