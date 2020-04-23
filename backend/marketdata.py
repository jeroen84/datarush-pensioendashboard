import pandas as pd
import numpy as np
import sqlite3
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.foreignexchange import ForeignExchange
from dateutil.relativedelta import relativedelta
import logging as LOG
import os


DBLOCATION = "db/marketdata.db"
ALPHAVANTAGE_API = os.environ["ALPHAVANTAGE_API"]
EQUITYTICKER = ["EUNL.DE", "IS3N.DE", "GSG"]
FXTICKER = ["USD"]
# swap ticker slightly different, as a dict including website address
SWAPTICKER = {"EUSA30":
              "https://www.iex.nl/"
              "Rente-Koers/61375432/IRS-30Y-30-360-ANN-6M-EURIBOR/"
              "historische-koersen.aspx?maand={}"}

LOG.basicConfig(format='%(asctime)s %(message)s',
                filename="log/backend.log",
                level=LOG.INFO)


class MarketData:

    def __init__(self, db=DBLOCATION):
        try:
            LOG.info("Start MarketData object")
            _query = "SELECT date, name, value FROM marketdata"
            self.db = db
            self.conn = sqlite3.connect(self.db)
            self.df_db = pd.read_sql(sql=_query,
                                     con=self.conn,
                                     index_col="date",
                                     parse_dates={"date": "%Y-%m-%d"})
            self.df_db = self.df_db.pivot_table(values="value",
                                                index="date",
                                                columns="name")
            self.df_db.sort_index(inplace=True)
            self.ts = TimeSeries(key=ALPHAVANTAGE_API,
                                 output_format="pandas",
                                 indexing_type="date")
            self.cc = ForeignExchange(key=ALPHAVANTAGE_API)
        except Exception as err:
            LOG.error("Unable to load MarketData object: {}".format(err))

    # for the EQUITYTICKER list
    # and FXTICKER
    def UpdateEquityAndFX(self):
        # first, get the EQUITYTICKER
        try:
            for ticker in EQUITYTICKER:
                # get the daily quotes, compact size
                LOG.info("Getting new data for ticker {}".format(ticker))
                _df, _ = self.ts.get_daily(ticker, outputsize="compact")

                self.ProcessToDB(_df, ticker)

            # secon, get the FXTICKER
            for fx in FXTICKER:
                # for fx, Alphavantage returns only json, so need to convert
                # to pandas
                _json = self.cc.get_currency_exchange_daily(
                    from_symbol="EUR",
                    to_symbol=fx,
                    outputsize="compact")
                # add check whether _json returns data...
                _df = pd.DataFrame(data=_json[0], dtype=float).transpose()
                # reformat the index, to be in line with equities
                _df.index = pd.to_datetime(_df.index)
                _df.index.name = "date"

                self.ProcessToDB(_df, "EUR{}".format(fx))
        except Exception as err:
            LOG.error("Updating equity and FX result in error: {}".format(err))

    def UpdateInterestRates(self):
        # this is a IEX website scraper
        # determine last data point
        # is this last data point in the current month?
        # otherwise include suffix to webaddress equal
        # to number of months before
        try:
            # translate table
            _DIC = {" jan": "-01-",
                    " feb": "-02-",
                    " mrt": "-03-",
                    " apr": "-04-",
                    " mei": "-05-",
                    " jun": "-06-",
                    " jul": "-07-",
                    " aug": "-08-",
                    " sep": "-09-",
                    " okt": "-10-",
                    " nov": "-11-",
                    " dec": "-12-"}

            for swapticker in SWAPTICKER:
                _max_date = self.df_db[swapticker].dropna().index.max()
                _today = pd.to_datetime("today")

                _numbermonths = (_today.year * 12) - (_max_date.year * 12) + \
                    _today.month - _max_date.month

                LOG.info("Getting new data for ticker {}".format(swapticker))
                for x in range(0, _numbermonths+1):
                    _df = pd.read_html(SWAPTICKER[swapticker].format(
                                    x),
                                    decimal=",",
                                    thousands=".")[2][["Datum", "Slot"]]

                    for y in _DIC:
                        _df["Datum"] = _df["Datum"].str.replace(y, _DIC[y])

                    # add year
                    _df["Datum"] += str((_today - relativedelta(
                                                months=_numbermonths)).year)

                    _df["Datum"] = pd.to_datetime(_df["Datum"],
                                                  format="%d-%m-%Y")

                    _df.rename(columns={"Datum": "date",
                                        "Slot": "4. close"}, inplace=True)
                    _df.set_index("date", inplace=True)

                    self.ProcessToDB(_df, swapticker)
        except Exception as err:
            LOG.error("UpdateInterestRate resulted in an error: {}".format(
                err))

    def ProcessToDB(self, df_source: pd.DataFrame, ticker):
        # first, extract all data that is not present
        # in database (ie missing dates)
        # then write to db the missing date values
        try:
            if df_source.empty:
                LOG.info("Received no data for ticker "
                         "{}. No data is being processed to DB".format(
                             ticker))
                return
            else:
                LOG.info("Succesfully received data "
                         "for ticker {}".format(ticker))

            _df = pd.DataFrame(df_source["4. close"]).rename(
                columns={"4. close": "value"})
            # add ticker name to the dataframe as a column
            _df["name"] = ticker
            # Compare with db, and filter what is missing
            # we can do this by a outer join, or just say
            # pick all dates from Alphavintage that are beyond the latest
            # date of the db.
            _max_date = self.df_db[ticker].dropna().index.max()
            _df = _df[_df.index > _max_date]

            # exclude today's value, for now?
            # live quotes should be somewhere else ?
            _df = _df[_df.index != np.datetime64("today")]

            if not _df.empty:
                # write to database
                _df = _df.reset_index()
                _df["date"] = _df["date"].dt.strftime("%Y-%m-%d")
                _df.to_sql(name="marketdata",
                           con=self.conn,
                           index=False,
                           if_exists="append")
                LOG.info("Successfully updated ticker {} with dates {} "
                         "and values {}".format(ticker,
                                                _df["date"].values,
                                                _df["value"].values))
            else:
                # include feedback to logging (TO DO)
                LOG.info("No new data for {}".format(ticker))
        except Exception as err:
            LOG.error("ProcessToDB resulted in an error: {}".format(err))
