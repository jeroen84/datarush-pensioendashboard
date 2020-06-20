from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import plotly.io as pio
from datetime import datetime
from .dataimport import DataImport
from .riskmodel import RiskModelPF
from .graphs import GraphLibrary
from newsapi import NewsApiClient
import os
from flask_caching import Cache
from app import app

pio.templates.default = "plotly_dark"

RATES = ["EUSA30", "EURUSD"]
TABINTERVALS = ["6m"]

# initiate DataImport and RiskModelPF class
DATA = DataImport()
RISKMODEL = RiskModelPF()

# for threadign purposes
global FIGURES
FIGURES = GraphLibrary()

# set news api
NEWSAPI_KEY = os.environ["NEWSAPI_KEY"]
NEWSAPI = NewsApiClient(api_key=NEWSAPI_KEY)

# define the base path of the dashboard
# needed in a multipage dashboard
BASEPATH = "/pensioendashboard"

cache = Cache(app.server, config={
    "CACHE_TYPE": "filesystem",
    "CACHE_DIR": "cache-directory"
})
CACHE_TIMEOUT = 600
cache.clear()


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
    # run risk model
    RISKMODEL.runLinearModel(DATA.df_marketdata, DATA.df_dgr)
    RISKMODEL.makePrediction()
    RISKMODEL.makeContribution()

    FIGURES.buildGraphs(
        DATA.df_dgr,
        RISKMODEL.df_predict,
        DATA.df_marketdata.dropna(),
        DATA.df_marketdatanames,
        RISKMODEL.df_contribution,
        DATA.df_countryexposure,
        RATES,
        TABINTERVALS
    )


def topCardLayout(title: str,
                  value: float,
                  change: float,
                  date,
                  dgr: bool,
                  rates: bool) -> dbc.Card:
    """
    Make a top (summary) card with the value, delta and date.
    """

    # determine the color of the delta: green if positive, red if negative

    if change >= 0:
        fontcolor = "green"
    else:
        fontcolor = "red"

    # in case the card is for the dekkingsgraden, make the value a percentage,
    # otherwise, make the value without percentage sign
    if dgr:
        _valueformat = "{:.1f}% "
        textH = html.H3
    else:
        _valueformat = "{:.2f} "
        textH = html.H5

    if rates:
        _deltaformat = "{:+.2f}"
    else:
        _deltaformat = "{:+.1f}%"

    return dbc.Card([
        dbc.CardHeader(title),
        dbc.CardBody([
            # titleH(title, className="card-title"),
            textH([
                html.Span(_valueformat.format(value)),
                html.Span(_deltaformat.format(change),
                          className="delta-{}".format(title.lower()),
                          style={"color": fontcolor})
            ],
                  className="card-text-{}".format(title.lower())),
            html.Small("per {}".format(
                date.strftime("%d-%m-%Y")),
                        className="card-small-{}".format(title))
        ], id="tooltip-dgr-{}".format(title))
    ])


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
                    topCardLayout(fund_rename,
                                  max_predict_dgr,
                                  delta_latest_predict,
                                  max_predict_date,
                                  True,
                                  False),
                    dbc.Tooltip("{:+.1f}% verschil t.o.v. {}".format(
                        delta_latest_predict,
                        latest_official_dgr_date.strftime("%d-%m-%Y")),
                        target="tooltip-dgr-{}".format(fund_rename))
                ])
        )

    _marketdata = DATA.df_marketdata.dropna()
    dbcMarkets = []

    for market in _marketdata.columns:
        latest_value = _marketdata[market].iloc[-1:].values[0]
        max_date = _marketdata.index.max()

        if market in RATES:
            latest_delta = _marketdata[market].diff().iloc[-1:].values[0]
            ratesformat = True
        else:
            latest_delta = _marketdata[market].pct_change().iloc[-1:].values[0] * 100
            ratesformat = False

        dbcMarkets.append(
            dbc.Col([
                topCardLayout(DATA.df_marketdatanames[market],
                              latest_value,
                              latest_delta,
                              max_date,
                              False,
                              ratesformat)
            ])
        )

    return dbc.Col([
        dbc.Row(
            dbcLayout,
            no_gutters=True
        ),
        dbc.Row(
            dbcMarkets,
            no_gutters=True
        )
    ])


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
            "Overzicht", href="{}/page-1".format(BASEPATH), id="page-1-link")),
        dbc.NavItem(dbc.NavLink(
            "Dekkingsgraadcontributie", href="{}/page-2".format(BASEPATH),
            id="page-2-link")),
        dbc.NavItem(dbc.NavLink(
            "Top 10 landen exposures", href="{}/page-3".format(BASEPATH),
            id="page-3-link")),
        dbc.NavItem(dbc.NavLink(
            "Over", href="{}/page-4".format(BASEPATH), id="page-4-link")),
        ],
        fill=True,
        pills=True)
])

content = html.Div(id="page-content")
# --------------


@cache.memoize(timeout=CACHE_TIMEOUT)
def contentoverview():
    DATA.refreshData()
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
                dbc.Card([
                    dbc.CardHeader("Toelichting"),
                    dbc.CardBody("Onderstaand grafiek geeft per tijdshorizon, "
                                 "bijvoorbeeld per dag, de impact van de "
                                 "de risicofactoren aandelen, grondstoffen, "
                                 "valuta en rente op de verandering van de "
                                 "geschatte dekkingsgraad weer. Merk op, dit "
                                 "betreft alleen de periode waarover de "
                                 "dekkingsgraad geschat wordt."
                                 )
                ])
            ),
        ),
        dbc.Row([
            dbc.Col(
                dbc.Card([
                    dbc.CardHeader("Fonds"),
                    dbc.CardBody(
                        dcc.Dropdown(
                            id="fund-name-dropdown",
                            options=[
                                {"label": fund, "value": fund}
                                for fund in RISKMODEL.df_contribution.keys()
                            ],
                            value="ABP",
                            style=dict(color="black")
                        )
                    )
                ]

                    ),
                lg=6,
                md=12
            ),
            dbc.Col(
                dbc.Card([
                    dbc.CardHeader("Tijdshorizon"),
                    dbc.CardBody(
                            dcc.Dropdown(
                                id="bin-dropdown",
                                options=[
                                    {"label": "1 dag", "value": "D"},
                                    {"label": "1 week", "value": "W-FRI"}
                                ],
                                value="D",
                                style=dict(color="black")
                            )
                    )
                ]
                    )
            )
        ],
            no_gutters=True
        ),
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        dcc.Loading(id="loading-icon",
                                    children=dcc.Graph(
                                        id="contribution-graph",
                                        responsive="auto",
                                        config=FIGURES.graphConfig),
                                    type="default")))
                )
        )
    ]


@cache.memoize(timeout=CACHE_TIMEOUT)
def contentcountries():
    return [
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        dcc.Loading(id="loading-icon",
                                    children=dcc.Graph(
                                        id="country-graph",
                                        figure=FIGURES.buildCountryExposureGraph(),
                                        responsive="auto",
                                        config=FIGURES.graphConfig),
                                    type="default")))
                )
        ),
        dbc.Row(
            dbc.Col(
                dbc.Card([
                    dbc.CardHeader("Bronnen"),
                    dbc.CardBody([
                        dcc.Markdown(
                            "De volgende openbare bronnen zijn geraadpleegt "
                            "voor bovenstaande grafiek"),
                        dcc.Markdown(
                            "**ABP:** [https://www.abp.nl/over-abp/duurzaam-en"
                            "-verantwoord-beleggen/waarin-belegt-abp/]"
                        ),
                        dcc.Markdown(
                            "**PFZW:** [https://www.pfzw.nl/over-ons/zo-"
                            "beleggen-we/waarin-we-beleggen.html]"
                        ),
                        dcc.Markdown(
                            "_Opmerking: Voor PFZW zijn alleen de aandelen "
                            "en obligaties gekozen_"
                        )
                    ])
                ]),
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


# dash_app.config.suppress_callback_exceptions = True
# define the layout of the dashboard
# app.title = "Datarush | Pensioendashboard"
layout = dbc.Container([
    dcc.Location(id="url"),
    topbar,
    html.Hr(),
    navbar,
    content
])


@app.callback(
    [Output(f"page-{i}-link", "active") for i in range(1, 5)],
    [Input("url", "pathname")],
)
def toggle_active_links(pathname):
    if pathname == BASEPATH:
        # Treat page 1 as the homepage / index
        return True, False, False, False
    return [pathname == BASEPATH + f"/page-{i}" for i in range(1, 5)]


@app.callback(Output("page-content", "children"),
              [Input("url", "pathname")])
def render_page_content(pathname):
    if pathname in [BASEPATH, "{}/page-1".format(BASEPATH)]:
        return contentoverview()
    elif pathname == "{}/page-2".format(BASEPATH):
        return contentpensioenfondsen()
    elif pathname == "{}/page-3".format(BASEPATH):
        return contentcountries()
    elif pathname == "{}/page-4".format(BASEPATH):
        return dbc.Jumbotron(aboutcontent)
    # If the user tries to reach a different page, return a 404 message
    return dbc.Jumbotron(
        [
            html.H1("404: Not found", className="text-danger"),
            html.Hr(),
            html.P(f"The pathname {pathname} was not recognised..."),
        ]
    )


@app.callback(Output("content", "children"),
              [Input("tabs", "active_tab")])
def switch_tab(at):
    return contenttabs(at)


@app.callback(
    Output("contribution-graph", "figure"),
    [
        Input("fund-name-dropdown", "value"),
        Input("bin-dropdown", "value")
    ],
)
def makeContributionGraph(fund, bin):
    return FIGURES.buildContributionGraph(fund, bin)
