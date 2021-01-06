# Pensioendashboard by Datarush

Welcome to the repository of the [Pensioendashboard](http://pensioendashboard.datarush.nl). The dashboard provides insights in the financial health of the largest Dutch pension funds. The site is hosted by Microsoft Azure, using the Web App functionality. Github commits are automatically deployed to the web site! :rocket:

---

# General prequisitions
Since the dashboard and backend are written in Python, a Python compiler is required. I recommend using the [Anaconda](https://www.anaconda.com/distribution/), given that this is a comprehensive distribution for working with data in all its forms.

The key packages used in this repository are:

- Dash: for the web app
- Pandas: for data manupilation
- Beautifulsoup4: for web scraping
- Sqlalchemy: for database operations
- Scikit-learn: for machine learning

Please find a full list of required packages in the `requirements.txt` and `backend/requirements.txt` files.

# Part 1 - web app
The dashboard is build using the Python libraries of [Dash for Plotly](https://dash.plotly.com). Amongst others, the Dash bootstrap component is used for the layout.

The dashboard also contains modules that 'predict' the `dekkingsgraad` of the pension funds using the linear regression model of sci-kit learn.

# Part 2 - database
The database used is a sqlite database, although other types of databases are possible given the use of sqlalchemy. The database consists of market data and `dekkingsgraad` information of pensionfunds.  A (recent) copy of the database can be found here. Please place this database in the subdirectory /db.

# Part 3 - backend
The backend pulls the latest market and `dekkingsgraad` data from the respective data sources using a combination of API calls and web scrapers. 

# How to run the dashboard using Docker
To make the dashboard work on your computer or server, make sure you have [Docker](https://docker.com) installed. Also, for convenience, make sure [Docker compose](https://docs.docker.com/compose/install/) is installed. A `docker-compose.yml` file is available to run the dashboard and backend with a single command (see below).

Then, because the dashboard sources data from two public API's, one needs to set two environment variable files in the `.env` folder. Please make this folder (I have not shared this because I do not want a large amount of traffic using my API keys). Make two files in the `.env` folder: `app.env` and `backend.env`. In the first, insert the line `NEWSAPI_KEY={API_KEY}`, whereas `{API_KEY}` is your personal API key from [Newsapi](https://newsapi.org/). In the latter, insert `ALPHAVANTAGE_API={API_KEY}`, whereas `{API_KEY}` is your personal API key from [Alphavantage](https://www.alphavantage.co/).

Finally, the dashboard, as well as a single run of the backend (which updates the database with the latest data), can be run via the command `docker-compose -f "docker-compose.yml" up -d --build`. Then, the dashboard can be reached via `http://localhost:8050`.

Please note that the dashboard is set up as a development server (see the commands in the `Dockerfile` for running the dashboard). For running the application on a web server, for instance Azure Web Apps, please go [here](https://docs.microsoft.com/en-us/azure/app-service/containers/quickstart-python?tabs=bash). In the case of https://pensioendashboard.datarush.nl, I have linked the Azure Web App repository to this Github repository. When the Github repository is updated, a new Web App is automatically created by Azure Web Apps. Very convenient!

For more information, please contact me at jeroen@datarush.nl

Any feedback is more than welcome!
