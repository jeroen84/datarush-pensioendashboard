# For running the Dashboard in a Docker container
# This is for testing purposes only
FROM python:3.8-slim-buster

WORKDIR /app

COPY pensioendashboard/requirements.txt ./

RUN pip install -r requirements.txt

COPY pensioendashboard/__init__.py /app/pensioendashboard/
COPY pensioendashboard/app.py /app/pensioendashboard/
COPY pensioendashboard/backend/graphs.py /app/pensioendashboard/backend/
COPY pensioendashboard/backend/__init__.py /app/pensioendashboard/backend/
COPY pensioendashboard/backend/dataimport.py /app/pensioendashboard/backend/
COPY demo1/__init__.py /app/demo1/
COPY demo1/app.py /app/demo1/
COPY demo1/marketdata.db /app/demo1/

COPY index.py /app/
COPY app.py /app/

# For mapping the database, in this case a sqlite db
VOLUME /app/pensioendashboard/db/
VOLUME /app/pensioendashboard/log/

ENV FLASK_ENV=development
ENV FLASK_DEBUG=1

EXPOSE 8050

ENTRYPOINT [ "python" ]

CMD [ "index.py", "--host=0.0.0.0", "--port=8050" ]
