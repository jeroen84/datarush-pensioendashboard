import plotly.graph_objects as go
import dash_core_components as dcc
from plotly.subplots import make_subplots
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd

LINECOLORS = {"ABP": "indianred",
              "PFZW": "mediumseagreen",
              "BPF Bouw": "goldenrod",
              "PMT": "black"}


class GraphLibrary:

    def __init__(self, ready):
        self.ready = ready
        self.dgrgraphs = {}
        self.equitygraphs = {}
        self.ratesgraphs = {}

    def buildGraphs(self,
                    df_dgr: pd.DataFrame,
                    df_predict: pd.DataFrame,
                    df_marketdata: pd.DataFrame,
                    df_marketdatanames: pd.DataFrame,
                    rates_indices: list,
                    intervals: list):
        self.df_dgr = df_dgr
        self.df_predict = df_predict
        self.df_marketdata = df_marketdata
        self.df_marketdatanames = df_marketdatanames
        self.rates_indices = rates_indices
        self.intervals = intervals

        _today = datetime.now()
        graphConfig = {"displayModeBar": False}

        for interval in self.intervals:
            if interval == "3m":
                _startdate = _today + relativedelta(months=-3)
            elif interval == "6m":
                _startdate = _today + relativedelta(months=-6)
            elif interval == "1y":
                _startdate = _today + relativedelta(years=-1)
            elif interval == "YTD":
                _startdate = datetime(year=_today.year - 1,
                                      month=12,
                                      day=31)
            elif interval == "all":
                _startdate = None

            figureDGR = self.buildDGRGraph(_startdate)
            figureEquity = self.buildEquityGraph(_startdate)
            figureRates = self.buildRatesGraph(_startdate)

            self.dgrgraphs.update(
                {interval:
                    [
                        dcc.Graph(
                            figure=figureDGR,
                            responsive="auto",
                            config=graphConfig
                            )
                    ]}
                )

            self.equitygraphs.update(
                {interval:
                    [
                        dcc.Graph(
                            figure=figureEquity,
                            responsive="auto",
                            config=graphConfig
                            )
                    ]}
                )

            self.ratesgraphs.update(
                {interval:
                    [
                        dcc.Graph(
                            figure=figureRates,
                            responsive="auto",
                            config=graphConfig
                            )
                    ]}
                )

        self.ready.set()

    def buildDGRGraph(self, start_date=None):

        fig_dgr = go.Figure()
        hovertemplate = "<b>Datum:</b> %{x}<br><br>" \
                        "<b>Dekkingsgraad:</b> %{y:.1f}%<br>"

        # add lines for each pensionfund
        for fund in self.df_dgr["fonds"].sort_values().unique():
            df = self.df_dgr[self.df_dgr["fonds"] == fund]

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

            df_predict_fund = self.df_predict[fund]
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
        return fig_dgr

    def buildEquityGraph(self,
                         start_date=None):
        # ----------
        # first filter on start_date
        if start_date is None:
            df = self.df_marketdata
        else:
            df = self.df_marketdata[self.df_marketdata.index >= start_date]

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

            long_name = self.df_marketdatanames[x]
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
        return fig_equity

    def buildRatesGraph(self, start_date=None):
        # ----------
        # create market indices graphs (EUSA30 and EURUSD)
        df_rates = self.df_marketdata[self.rates_indices]

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

        return fig_rates
