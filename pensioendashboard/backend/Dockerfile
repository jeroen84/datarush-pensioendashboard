FROM python:3.7-slim-buster

WORKDIR /backend

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY __init__.py /backend/
COPY dataimport.py /backend/
COPY marketdata.py /backend/
COPY riskmodel.py /backend/
COPY websitesDgr.py /backend/

VOLUME /db/
VOLUME /log/

ENTRYPOINT [ "python" ]

CMD [ "/backend/__init__.py" ]