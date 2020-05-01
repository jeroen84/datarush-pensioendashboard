import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import plotly.io as pio
from datetime import datetime
from dataimport import DataImport
from riskmodel import RiskModelPF
from graphs import GraphLibrary
from newsapi import NewsApiClient
from threading import Event, Thread
import os
from flask_caching import Cache

pio.templates.default = "seaborn"

RATES = ["EUSA30", "EURUSD"]
TABINTERVALS = ["6m"]

# initiate DataImport and RiskModelPF class
DATA = DataImport()
RISKMODEL = RiskModelPF()

# for threadign purposes
READY = Event()
global FIGURES
FIGURES = GraphLibrary(READY)

# set news api
NEWSAPI_KEY = os.environ["NEWSAPI_KEY"]
NEWSAPI = NewsApiClient(api_key=NEWSAPI_KEY)

# set up the server, using a bootstrap theme
dash_app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.LUX],
    meta_tags=[
        {
            "name": "description",
            "content": "Actuele situatie van Nederlandse pensioenfondsen"
                       "in een overzichtelijk dashboard"
        },
        {
            "name": "keywords",
            "content": "dekkingsgraad, pensioenfondsen, dashboard, datarush"
        },
        {
            "name": "author",
            "content": "Jeroen van de Erve"
        },
        {
            "name": "viewport",
            "content": "width=device-width, initial-scale=1.0"
        },
        {
            "http-equiv": "X-UA-Compatible",
            "content": "IE=edge"
        },
    ]
    )
app = dash_app.server
cache = Cache(app, config={
    "CACHE_TYPE": "filesystem",
    "CACHE_DIR": "cache-directory"
})
CACHE_TIMEOUT = 600


def getNews():
    topics = ["pensioenfondsen",
              "beurs",
              "rente",
              "valuta"]

    response = {}
    for topic in topics:
        response.update({topic:
                         NEWSAPI.get_everything(q=topic,
                                                language="nl",
                                                sort_by="publishedAt",
                                                page_size=10,
                                                page=1)})

    return response


def buildNewsFeed(topic):
    results = getNews()[topic]
    news_items = [dbc.ListGroupItemHeading("Laatste nieuws [{}]".format(
        datetime.now().strftime("%H:%M:%S")
        ))]
    for item in results["articles"]:
        news_items.append(dbc.ListGroupItem("{} [{}, {}]".format(
            item["title"],
            item["source"]["name"].lower(),
            item["publishedAt"][0:10]),
                                            href=item["url"],
                                            target="_blank"))
    return news_items


def getMarketData():
    # first refresh the dataset
    DATA.refreshData()

    # then run model
    RISKMODEL.runLinearModel(DATA.df_marketdata, DATA.df_dgr)
    RISKMODEL.makePrediction()
    RISKMODEL.makeContribution()

    # threading because otherwise not all graphs are completed
    # at startup
    thread = Thread(target=FIGURES.buildGraphs, args=(
        DATA.df_dgr,
        RISKMODEL.df_predict,
        DATA.df_marketdata.dropna(),
        DATA.df_marketdatanames,
        RISKMODEL.df_contribution,
        RATES,
        TABINTERVALS
    ))

    thread.start()
    READY.wait()


def buildCardLatestDGR(df_dgr, df_predict):
    dbcLayout = []

    for fund in df_dgr["fonds"].sort_values().unique():
        # predictions
        df_predict_fund = df_predict[fund]
        max_predict_date = max(df_predict_fund.index)
        max_predict_dgr = df_predict_fund[
            df_predict_fund.index == max_predict_date]
        max_predict_dgr = max_predict_dgr["dekkingsgraad"][0]

        # last official number
        df_dgr_fund = df_dgr[df_dgr["fonds"] == fund]
        latest_official_dgr_date = max(df_dgr_fund["date"])
        latest_official_dgr = df_dgr_fund[
            df_dgr_fund["date"] == latest_official_dgr_date]
        latest_official_dgr = latest_official_dgr["dekkingsgraad"].values[0]

        delta_latest_predict = max_predict_dgr - latest_official_dgr

        # ugly, but for now ok. For responsiveness change name to short "Bouw"
        if fund == "BPF Bouw":
            fund_rename = "Bouw"
        else:
            fund_rename = fund

        dbcLayout.append(
                dbc.Col([
                    dbc.Card(
                        dbc.CardBody([

                            html.H4(fund_rename, className="card-title"),
                            html.Div([
                                "{:.1f}% ".format(max_predict_dgr),
                                html.Sub("({})".format(
                                    max_predict_date.strftime("%d-%m-%Y")))
                                    ],
                                     className="card-text"),
                            html.Small("{:+.1f}% t.o.v. {}".format(
                                delta_latest_predict,
                                latest_official_dgr_date.strftime("%d-%m-%Y")),
                                     className="card-text")
                        ], id="tooltip-dgr-{}".format(fund[0:3]))
                        # [0:3] ivm spatie bij BPF Bouw
                    ),
                    dbc.Tooltip("Meest recente schatting per {}".format(
                        max_predict_date.strftime("%d-%m-%Y")),
                        target="tooltip-dgr-{}".format(fund[0:3]))
                ])
        )

    return dbc.Row(
            dbcLayout,
            no_gutters=True
        )


# CONTENT OF THE SITE
aboutcontent = [
        dcc.Markdown("""
        ### Over het pensioendashboard

        Dit dashboard geeft een overzicht van de actuele
        financiële stand van zaken van de grootste pensioenfondsen
        van Nederland. Voor dit dashboard wordt gebruik gemaakt van
        openbare databronnen en opensource software. Verschillende
        technieken worden toegepast voor het binnenhalen en bewerken
        van de data, onder andere webscraping en API's. Voor de prognose
        van de dekkingsgraden worden _machine learning_ technieken
        toegepast. Qua software wordt gebruik gemaakt van onder meer
        Python, Azure Web Apps, Plotly en Dash. Dit alles in een volledig
        geautomatiseerde omgeving. De broncode is op
        [Github](https://github.com/jeroen84/datarush-pensioendashboard)
        geplaatst!
        """.format("https://github.com/jeroen84/")
        ),
        dcc.Markdown("""
        Dekkingsgraden worden slechts eenmaal per maand
        gepubliceerd door de fondsen, en pas circa twee
        weken na het einde van de maand. Dit dashboard
        presenteert een inschatting van de dekkingsgraad
        vanaf het laatst gepubliceerde cijfer. Voor de
        inschatting wordt gebruik gemaakt van vijf
        marktindicatoren, zie de tweede en derde grafiek.
        Het aantal fondsen in het overzicht zal uitgebreid
        worden.
        """),
        dcc.Markdown("""
        De historische dekkingsgraden zijn verkregen van de
        websites van de pensioenfondsen. Voor de schatting
        van de dekkingsgraden wordt gebruik gemaakt van een
        lineair regressiemodel, waarbij test en training
        sets worden gebruikt. De schatting bevat
        statistisch gezien vele aannames en beperkingen.
        Afwijkingen ten opzichte van de gepubliceerde
        cijfers zullen er zijn. Daarom dienen de
        schattingen geïnterpreteerd te worden als een
        richting waarop de dekkingsgraden zich ontwikkelen.
        """)
]

topbar = dbc.Row([
    dbc.Nav([
        dbc.NavItem(dbc.NavLink("Contact",
                                href="mailto:jeroen@datarush.nl")),
        dbc.NavItem(dbc.NavLink(
            "LinkedIn",
            href="https://www.linkedin.com/in/jeroen-van-de-erve/")),
        dbc.NavItem(dbc.NavLink(
            "Github",
            href="https://github.com/jeroen84/datarush-pensioendashboard")),
        dbc.NavItem(dbc.NavLink("More",
                                href="https://www.datarush.nl"))
    ]),
],
    justify="center")

navbar = html.Div([
    html.H2("Pensioendashboard", style={"textAlign": "center"}),
    html.Hr(),
    dbc.Nav([
        dbc.NavItem(dbc.NavLink(
            "Overzicht", href="/page-1", id="page-1-link")),
        dbc.NavItem(dbc.NavLink(
            "Pensioenfondsen", href="/page-2", id="page-2-link")),
        dbc.NavItem(dbc.NavLink(
            "Financiële markten", href="/page-3", id="page-3-link")),
        dbc.NavItem(dbc.NavLink(
            "Over", href="/page-4", id="page-4-link")),
        ],
        fill=True,
        pills=True)
])

content = html.Div(id="page-content")
# --------------


@cache.memoize(timeout=CACHE_TIMEOUT)
def contentoverview():
    getMarketData()
    latestDGRCards = buildCardLatestDGR(DATA.df_dgr,
                                        RISKMODEL.df_predict)

    return html.Div([
        html.P(latestDGRCards),
        dbc.CardHeader(dbc.Tabs([
            dbc.Tab(tab_id="tab-dgr", label="Dekkingsgraden"),
            dbc.Tab(tab_id="tab-equity", label="Aandelen en grondstoffen"),
            dbc.Tab(tab_id="tab-rates", label="Rente en valuta")
        ],
            id="tabs",
            card=True,
            active_tab="tab-dgr"),
        ),
        html.Div(id="content")
    ])


@cache.memoize(timeout=CACHE_TIMEOUT)
def contentpensioenfondsen():
    return [
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        dcc.Dropdown(
                            id="fund-name-dropdown",
                            options=[
                                {"label": fund, "value": fund}
                                for fund in RISKMODEL.df_contribution.keys()
                            ],
                            value="ABP",
                        )
                    ))
            )
        ),
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        dcc.Graph(id="contribution-graph")))
                )
        )
    ]


@cache.memoize(timeout=CACHE_TIMEOUT)
def contenttabs(tab):
    if tab == "tab-dgr":
        return dbc.Row([
            dbc.Col([
                dbc.Card(dbc.CardBody(FIGURES.dgrgraphs["6m"])),
            ],
                lg=8,
                md=12
            ),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody(buildNewsFeed("pensioenfondsen"))
                ])
            ])
        ])
    elif tab == "tab-equity":
        return dbc.Row([
            dbc.Col([
                dbc.Card(dbc.CardBody(FIGURES.equitygraphs["6m"]))
            ],
                lg=8,
                md=12
            ),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody(buildNewsFeed("beurs"))
                ])
            ])
        ])
    elif tab == "tab-rates":
        return dbc.Row([
            dbc.Col([
                dbc.Card(dbc.CardBody(FIGURES.ratesgraphs["6m"]))
            ],
                lg=8,
                md=12
            ),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody(buildNewsFeed("rente"))
                ])
            ])
        ])


dash_app.config.suppress_callback_exceptions = True
# define the layout of the dashboard
dash_app.title = "Datarush | Pensioendashboard"
dash_app.layout = dbc.Container([
    dcc.Location(id="url"),
    topbar,
    html.Hr(),
    navbar,
    content
])


@dash_app.callback(
    [Output(f"page-{i}-link", "active") for i in range(1, 5)],
    [Input("url", "pathname")],
)
def toggle_active_links(pathname):
    if pathname == "/":
        # Treat page 1 as the homepage / index
        return True, False, False, False
    return [pathname == f"/page-{i}" for i in range(1, 5)]


@dash_app.callback(Output("page-content", "children"),
                   [Input("url", "pathname")])
def render_page_content(pathname):
    if pathname in ["/", "/page-1"]:
        return contentoverview()
    elif pathname == "/page-2":
        return contentpensioenfondsen()
    elif pathname == "/page-3":
        return dbc.Jumbotron(html.P("Work in progress..."))
    elif pathname == "/page-4":
        return dbc.Jumbotron(aboutcontent)
    # If the user tries to reach a different page, return a 404 message
    return dbc.Jumbotron(
        [
            html.H1("404: Not found", className="text-danger"),
            html.Hr(),
            html.P(f"The pathname {pathname} was not recognised..."),
        ]
    )


@dash_app.callback(Output("content", "children"),
                   [Input("tabs", "active_tab")])
def switch_tab(at):
    return contenttabs(at)


@dash_app.callback(
    Output("contribution-graph", "figure"),
    [
        Input("fund-name-dropdown", "value")
    ],
)
def makeContributionGraph(fund):
    return FIGURES.buildContributionGraph(fund)


# run the dashboard
if __name__ == "__main__":
    dash_app.run_server(debug=False)
