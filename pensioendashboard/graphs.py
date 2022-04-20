import plotly.graph_objects as go
from dash import dcc, html
import dash_bootstrap_components as dbc
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from .backend.dataimport import DataImport

INTERVAL = -6  # months
STARTDATE = datetime.now() + relativedelta(months=INTERVAL)

LINECOLORS = {"ABP": "indianred",
              "PFZW": "mediumseagreen",
              "BPF Bouw": "goldenrod",
              "PMT": "white"}

RANGESELECTOR = dict(
    buttons=list([
        dict(count=1,
             label="1m",
             step="month",
             stepmode="backward"),
        dict(count=3,
             label="3m",
             step="month",
             stepmode="backward"),
        dict(count=6,
             label="6m",
             step="month",
             stepmode="backward"),
        dict(count=1,
             label="1y",
             step="year",
             stepmode="backward"),
        dict(count=1,
             label="YTD",
             step="year",
             stepmode="todate"),
        dict(step="all")
    ]))


class GraphLibrary(DataImport):

    def __init__(self,
                 rates_indices: list,
                 graphConfig: dict = {"displayModeBar": False}):
        self.rates_indices = rates_indices
        self.graphConfig = graphConfig

    def buildDGRGraph(self, start_date=STARTDATE):

        fig_dgr = go.Figure()
        hovertemplate = "<b>Datum:</b> %{x}<br><br>" \
                        "<b>Dekkingsgraad:</b> %{y:.1f}%<br>"

        # add lines for each pensionfund
        for fund in self.dekkingsgraden["fonds"].sort_values().unique():
            df = self.dekkingsgraden[self.dekkingsgraden["fonds"] == fund]

            if start_date is None:
                pass
            else:
                df = df[df["date"] >= start_date]  # filter based on start_date

            _x = df["date"]
            _y = df["dekkingsgraad"]
            fig_dgr.add_trace(go.Scatter(x=_x,
                                         y=_y,
                                         hovertemplate=hovertemplate,
                                         mode="lines",
                                         line=dict(width=3,
                                                   color=LINECOLORS[fund]),
                                         name=fund))

            df_predict_fund = self.dgr_prediction[self.dgr_prediction[
                "fund"] == fund]
            # add prediction line
            fig_dgr.add_trace(go.Scatter(x=df_predict_fund.index,
                                         y=df_predict_fund["dekkingsgraad"],
                                         hovertemplate=hovertemplate,
                                         line=dict(dash="dash",
                                                   width=3,
                                                   color=LINECOLORS[fund]),
                                         name="{} schatting".format(fund),
                                         showlegend=False))
        fig_dgr.update_layout(xaxis_rangeslider_visible=False,
                              title="Verloop dekkingsgraden plus prognose",
                              legend_orientation="h")

        return dcc.Graph(id="fig_dgr",
                         figure=fig_dgr,
                         responsive="auto",
                         config=self.graphConfig)

    def buildEquityGraph(self,
                         start_date=STARTDATE):
        # ----------
        # first filter on start_date
        if start_date is None:
            df = self.marketdata
        else:
            df = self.marketdata[self.marketdata.index >= start_date]

        # create market indices graphs (equities and commodities)
        df_dailyreturns = df.drop(
            columns=self.rates_indices).pct_change().fillna(0)
        df_cumreturns = (df_dailyreturns + 1).cumprod() * 100

        # create the graph
        fig_equity = go.Figure()
        hovertemplate = "<b>Datum:</b> %{x}<br><br>" \
            "<b>Rendement:</b> %{customdata:.1f}%<br>"

        for x in df_cumreturns.columns:
            _x = df_cumreturns.index
            _y = df_cumreturns[x]
            _y_perc = df_cumreturns[x] - 100

            long_name = self.marketdatanames[x]
            fig_equity.add_trace(go.Scatter(x=_x,
                                            y=_y,
                                            customdata=_y_perc,
                                            hovertemplate=hovertemplate,
                                            mode="lines",
                                            line=dict(width=3),
                                            name=long_name))

        fig_equity.update_layout(xaxis_rangeslider_visible=False,
                                 title="Ontwikkeling aandelen en grondstoffen",
                                 legend_orientation="h")

        return dcc.Graph(id="fig_equity",
                         figure=fig_equity,
                         responsive="auto",
                         config=self.graphConfig)

    def buildRatesGraph(self, start_date=STARTDATE):
        # ----------
        # create market indices graphs (EUSA30 and EURUSD)
        df_rates = self.marketdata[self.rates_indices]

        hovertemplate = "<b>Datum:</b> %{x}<br><br>" \
                        "<b>Niveau:</b> %{y:.2f}<br>"

        if start_date is None:
            pass
        else:
            df_rates = df_rates[df_rates.index >= start_date]

        fig_rates = make_subplots(specs=[[{"secondary_y": True}]])
        fig_rates.add_scatter(secondary_y=False,
                              x=df_rates.index,
                              y=df_rates["EUSA30"],
                              line=dict(width=3),
                              hovertemplate=hovertemplate,
                              name="30y EUR swap rate")
        fig_rates.add_scatter(secondary_y=True,
                              x=df_rates.index,
                              y=df_rates["EURUSD"],
                              line=dict(width=3),
                              hovertemplate=hovertemplate,
                              name="EUR/USD currency rate")
        fig_rates.update_layout(xaxis_rangeslider_visible=False,
                                title_text="Ontwikkeling rente en valuta",
                                legend_orientation="h")

        return dcc.Graph(id="fig_rates",
                         figure=fig_rates,
                         responsive="auto",
                         config=self.graphConfig)

    def buildContributionGraph(self, fund, bin=None):
        fig_contr = make_subplots(specs=[[{"secondary_y": True}]])

        hovertemplatebar = "<b>Datum:</b> %{x}<br><br>" \
                           "<b>Impact op dekkingsgraad:</b> %{y:.2f}%<br>" \
                           "t.o.v. de vorige dag"

        hovertemplatepredict = "<b>Datum:</b> %{x}<br><br>" \
                               "<b>Dekkingsgraad:</b> %{y:.1f}%<br>"

        df_contribution_fund = self.dgr_contribution[
            self.dgr_contribution["fund"] == fund]

        if bin is not None:
            df_contribution_fund = df_contribution_fund.groupby(
                ["index", pd.Grouper(level="date", freq=bin)]
            ).sum()

        for market in df_contribution_fund.index.get_level_values(
                "index").unique():
            _x = df_contribution_fund.loc[
                df_contribution_fund.index.get_level_values("index") == market
                ].index.get_level_values("date")
            _y = df_contribution_fund.loc[
                df_contribution_fund.index.get_level_values("index") == market
                ]["value"]
            long_name = self.marketdatanames[market]

            fig_contr.add_trace(go.Bar(x=_x,
                                       y=_y,
                                       hovertemplate=hovertemplatebar,
                                       name=long_name),
                                secondary_y=False)
        # add prediction line
        df_predict_fund = self.dgr_prediction[
            self.dgr_prediction["fund"] == fund]

        # only show the prediction values that are equal to the bins
        if bin is not None:
            # WORKAROUND: given that the latest predict date could be
            # before the last date of the bin, change the date of the
            # last value of the prediction equal to the last date value
            # of the bin
            _idx = df_predict_fund.index.to_list()
            _idx[-1] = max(df_contribution_fund.index.get_level_values("date"))
            df_predict_fund.index = _idx

            df_predict_fund = df_predict_fund[
                df_predict_fund.index.isin(
                    df_contribution_fund.index.get_level_values("date"))
            ]

        fig_contr.add_trace(go.Scatter(x=df_predict_fund.index,
                                       y=df_predict_fund["dekkingsgraad"],
                                       hovertemplate=hovertemplatepredict,
                                       line=dict(dash="dash",
                                                 width=3,
                                                 color=LINECOLORS[fund]),
                                       name="{} schatting".format(fund),
                                       showlegend=False),
                            secondary_y=True)

        fig_contr.update_layout(xaxis_rangeslider_visible=False,
                                title="Wat verklaart het verloop "
                                      "van de dekkingsgraad ({})?".format(
                                          fund),
                                barmode="relative",
                                bargap=0,
                                legend_orientation="h")
        fig_contr.update_xaxes(
            rangebreaks=[
                dict(bounds=["sat", "mon"])
            ]
        )
        return fig_contr

    def buildCountryExposureGraph(self):
        # inspired by
        # https://plotly.com/python/horizontal-bar-charts/#bar-chart-with-line-plot

        hovertemplate = "Totaal geïnvesteerd in %{y}:<br>EUR " \
            "%{customdata:,}<br>"

        df_countryexposure = self.countryexposure

        fig = make_subplots(rows=1, cols=2, specs=[[{}, {}]],
                            shared_xaxes=True,
                            shared_yaxes=False, vertical_spacing=0.001)

        # for now, only ABP and PFZW data available,
        # raise error if number of funds increase so we can have
        # a closer look then
        funds = df_countryexposure["fund"].unique()

        if len(funds) != 2:
            raise Exception("Other than two funds available in the database "
                            "regarding country exposure. Please have a look "
                            "at buildCountryExposureGraph")

        # for column count in the figure
        col = 1

        for fund in funds:
            # TO ADD: only pick the latest date (in case there is more than
            # one data point per fund)

            # filter on only the data of the fund
            df = df_countryexposure[df_countryexposure["fund"] == fund]
            # group by country
            df = df.groupby(by="country").sum()
            # add the percentage allocation per country
            df["percentage"] = df["value"] / df["value"].sum()
            # and then only show the largest 10 countries by value
            df = df.nlargest(10, "value")
            # order ascending because then the largest ends up on top
            # of the plotly graph
            df = df.sort_values(by="value", ascending=True)

            fig.add_trace(go.Bar(
                    x=df.percentage,
                    y=df.index,
                    customdata=df.value,
                    hovertemplate=hovertemplate,
                    marker=dict(
                        color=LINECOLORS[fund],
                        line=dict(
                            color="gray",
                            width=1),
                        ),
                    name=fund,
                    orientation="h"),
                row=1,
                col=col)
            col += 1

        fig.update_layout(
            title="Top 10 landen exposures per eind 2019",
            yaxis=dict(
                showgrid=False,
                showline=False,
                showticklabels=True,
                domain=[0, 0.85],
            ),
            yaxis2=dict(
                showgrid=False,
                showline=False,
                showticklabels=True,
                domain=[0, 0.85],
            ),
            xaxis=dict(
                zeroline=False,
                showline=False,
                showticklabels=True,
                showgrid=True,
                domain=[0, 0.45],
                tickformat=".1%"
            ),
            xaxis2=dict(
                zeroline=False,
                showline=False,
                showticklabels=True,
                showgrid=True,
                domain=[0.55, 1],
                tickformat=".1%"
            ),
            legend=dict(x=0.029, y=1.038, font_size=10),
            margin=dict(l=100, r=20, t=70, b=70),
            font=dict(
                family="Arial",
                size=12
            ),
        )

        fig.update_traces(texttemplate="%{x:.1%}",
                          textposition="inside",
                          cliponaxis=False)

        return fig

    def buildTopCards(self) -> dbc.Col:
        """
        Build the top cards that present the latest dekkingsgraden and
        the latest markets
        """
        dbcLayout = []

        for fund in self.dekkingsgraden["fonds"].sort_values().unique():
            # predictions
            df_predict_fund = self.dgr_prediction[
                self.dgr_prediction["fund"] == fund]
            max_predict_date = max(df_predict_fund.index)
            max_predict_dgr = df_predict_fund[
                df_predict_fund.index == max_predict_date]
            max_predict_dgr = max_predict_dgr["dekkingsgraad"][0]

            # last official number
            df_dgr_fund = self.dekkingsgraden[
                self.dekkingsgraden["fonds"] == fund]
            latest_official_dgr_date = max(df_dgr_fund["date"])
            latest_official_dgr = df_dgr_fund[
                df_dgr_fund["date"] == latest_official_dgr_date]
            latest_official_dgr = latest_official_dgr[
                "dekkingsgraad"].values[0]

            delta_latest_predict = max_predict_dgr - latest_official_dgr

            # ugly, but for now ok. For responsiveness change name to
            # short "Bouw"
            if fund == "BPF Bouw":
                fund_rename = "Bouw"
            else:
                fund_rename = fund

            dbcLayout.append(
                    dbc.Col([
                        self.topCardLayout(fund_rename,
                                           max_predict_dgr,
                                           delta_latest_predict,
                                           max_predict_date,
                                           True,
                                           False),
                        dbc.Tooltip("{:+.1f}% verschil t.o.v. {}".format(
                            delta_latest_predict,
                            latest_official_dgr_date.strftime("%d-%m-%Y")),
                            target="tooltip-dgr-{}".format(fund_rename))
                        ],
                        md=True,
                        sm=6,
                        xs=12
                    )
            )

        _marketdata = self.marketdata.dropna()
        dbcMarkets = []

        for market in _marketdata.columns:
            latest_value = _marketdata[market].iloc[-1:].values[0]
            max_date = _marketdata.index.max()

            if market in self.rates_indices:
                latest_delta = _marketdata[market].diff().iloc[-1:].values[0]
                ratesformat = True
            else:
                latest_delta = _marketdata[market].pct_change().iloc[
                    -1:].values[0] * 100
                ratesformat = False

            dbcMarkets.append(
                dbc.Col([
                    self.topCardLayout(self.marketdatanames[market],
                                       latest_value,
                                       latest_delta,
                                       max_date,
                                       False,
                                       ratesformat)
                    ],
                    md=True,
                    sm=6,
                    xs=12)
            )

        return dbc.Col([
            dbc.Row(
                dbcLayout,
                className="g-0"
            ),
            dbc.Row(
                dbcMarkets,
                className="g-0"
            )
        ])

    def topCardLayout(self,
                      title: str,
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

        # in case the card is for the dekkingsgraden, make the value a
        # percentage, otherwise, make the value without percentage sign
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
