Instructies (nog specifiek voor Jeroen zijn situatie):

- Go to backend folder
- Run `docker build -t pensionfund .`
- Run `docker run --rm -v /home/jeroen/Projecten/Dash/dekkingsgraadDash/db:/app/db -e PUID=1000 -e PGID=1000 -e TZ=Europe/Amsterdam -e UMASK_SET=022 pensionfund`
