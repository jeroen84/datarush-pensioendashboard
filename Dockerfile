# For running the Dashboard in a Docker container
# This is for testing purposes only
FROM python:3.7

WORKDIR /app

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY app.py /app
COPY dataimport.py /app
COPY graphs.py /app
COPY riskmodel.py /app

# For mapping the database, in this case a sqlite db
VOLUME /app/db
VOLUME /app/log

ENV FLASK_APP=${file}
ENV FLASK_ENV=development
ENV FLASK_DEBUG=1

ENTRYPOINT [ "flask" ]

CMD [ "run", "--host=0.0.0.0", "--port=8050" ]
