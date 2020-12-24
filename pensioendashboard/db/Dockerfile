# For initializing the database

FROM alpine:3.11

LABEL maintainer="Jeroen van de Erve"

RUN apk add --update sqlite

VOLUME /db

COPY init.sql /db

ENTRYPOINT ["sqlite3"]
CMD ["marketdata.db < init.sql"]