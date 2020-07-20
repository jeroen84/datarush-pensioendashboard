import pandas as pd
import numpy as np
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.foreignexchange import ForeignExchange
from dateutil.relativedelta import relativedelta
import logging as LOG
import os
from dateparser import parse

# for some reason, pytest and my python interpretor have
# inconsistencies in the way the __init__ module should
# be imported
try:
    from .__init__ import LOGLOCATION, DBCONNECTION
except ImportError:
    try:
        from __init__ import LOGLOCATION, DBCONNECTION
    except Exception as e:
        LOG.error(
            "Marketdata.py: Error while importing the __init__: {}".format(e))


ALPHAVANTAGE_API = os.environ["ALPHAVANTAGE_API"]

# equity ticker dict, whereby the keys are the links to
# the fallback scenario, in case Alpha Vantage does not
# provide quotes
EQUITYTICKER = {"IWDA.AS":
                "https://www.iex.nl/"
                "Beleggingsfonds-Koers/319919/"
                "iShares-Core-MSCI-World-UCITS-ETF/"
                "historische-koersen.aspx?maand={}",
                "EMIM.AS":
                "https://www.iex.nl/"
                "Beleggingsfonds-Koers/608862/"
                "iShares-Core-MSCI-Emerging-Markets-IMI-UCITS-ETF/"
                "historische-koersen.aspx?maand={}",
                "GSG":
                None}

FXTICKER = ["USD"]
# swap ticker slightly different, as a dict including website address
SWAPTICKER = {"EUSA30":
              "https://www.iex.nl/"
              "Rente-Koers/61375432/IRS-30Y-30-360-ANN-6M-EURIBOR/"
              "historische-koersen.aspx?maand={}"}

# create the log folder, in case it does not exist
# the logging could crash in case the folder is not present
os.makedirs(os.path.dirname(LOGLOCATION), exist_ok=True)

LOG.basicConfig(format='%(asctime)s %(message)s',
                filename=LOGLOCATION,
                level=LOG.INFO)


class MarketData:

    def __init__(self):
        try:
            LOG.info("Start MarketData object")
            _query = "SELECT date, name, value FROM marketdata"

            self.conn = DBCONNECTION
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
                _df = pd.DataFrame(_df["4. close"]).rename(
                    columns={"4. close": "value"})
                # add ticker name to the dataframe as a column
                _df["name"] = ticker

                _df_fallback = self.IEXScraper(ticker, EQUITYTICKER[ticker])

                self.ProcessToDB(_df, ticker, _df_fallback)

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
                _df = pd.DataFrame(_df["4. close"]).rename(
                    columns={"4. close": "value"})
                _df["name"] = "EUR{}".format(fx)

                # reformat the index, to be in line with equities
                _df.index = pd.to_datetime(_df.index)
                _df.index.name = "date"

                self.ProcessToDB(_df, "EUR{}".format(fx), pd.DataFrame())
        except Exception as err:
            LOG.error("Updating equity and FX result in error: {}".format(err))

    def UpdateInterestRates(self):
        try:
            for ticker in SWAPTICKER:
                _df = self.IEXScraper(ticker, SWAPTICKER[ticker])

                self.ProcessToDB(_df, ticker, pd.DataFrame())
        except Exception as err:
            LOG.error("UpdateInterestRates resulted in an error: {}".format(
                err))

    def IEXScraper(self, ticker, link) -> pd.DataFrame:
        # this is a IEX website scraper
        # determine last data point
        # is this last data point in the current month?
        # otherwise include suffix to webaddress equal
        # to number of months before
        try:
            if link is not None:
                _max_date = self.df_db[ticker].dropna().index.max()
                _today = pd.to_datetime("today")

                # determine the number of months required to download
                _numbermonths = (_today.year * 12) - (_max_date.year * 12) + \
                    _today.month - _max_date.month

                for x in range(0, _numbermonths+1):
                    # the link requires a "yyymm" extension in order
                    # to get the history of a specific year and month
                    # so, determine the extension
                    _query = (_today - relativedelta(months=x)).strftime(
                        "%Y%m")
                    _df = pd.read_html(link.format(
                                    _query),
                                    decimal=",",
                                    thousands=".")[1][["Datum", "Slot"]]

                    # format the date string to a datetime64 object
                    # using dateparser library
                    _df["Datum"] = _df["Datum"].apply(parse)

                    _df.rename(columns={"Datum": "date",
                                        "Slot": "value"}, inplace=True)
                    _df.set_index("date", inplace=True)
                    _df["name"] = ticker

                    return _df
            else:
                return pd.DataFrame()  # empty dataframe if no link is provided

        except Exception as err:
            LOG.error("IEXScraper resulted in an error: {}".format(
                err))

    def ProcessToDB(self, df_source: pd.DataFrame, ticker,
                    df_fallback: pd.DataFrame):
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

            # Compare with db, and filter what is missing
            # we can do this by a outer join, or just say
            # pick all dates from Alphavintage that are beyond the latest
            # date of the db.
            _max_date = self.df_db[ticker].dropna().index.max()
            _df = df_source[df_source.index > _max_date]
            _df_fallback = df_fallback[df_fallback.index > _max_date]
            # exclude today's value, for now?
            # live quotes should be somewhere else ?
            _df = _df[_df.index != np.datetime64("today")]
            _df_fallback = _df_fallback[_df_fallback.index !=
                                        np.datetime64("today")]

            _df_write = pd.DataFrame()
            # in case there is no new data from AlphaVantage
            if _df.empty:
                LOG.info("No new data for {} from AlphaVantage, trying "
                         "alternative source...".format(ticker))

                if _df_fallback.empty:
                    LOG.info("Also no data from alternative data source "
                             "for {}. The latest data point is: {}".format(
                                 ticker, _max_date))
                else:
                    _df_write = _df_fallback
                    LOG.info("Found new data points from alternative "
                             "data source for {}".format(ticker))
            else:  # i.e. when there are new data points from AlphaVantage
                _df_write = _df
                LOG.info("Found new data points from AlphaVantage for "
                         "{}".format(ticker))

            if not _df_write.empty:
                # write to database
                _df_write = _df_write.reset_index()
                _df_write["date"] = _df_write["date"].dt.strftime("%Y-%m-%d")
                _df_write.to_sql(name="marketdata",
                                 con=self.conn,
                                 index=False,
                                 if_exists="append")
                LOG.info("Successfully updated ticker {} with dates {} "
                         "and values {}".format(ticker,
                                                _df_write["date"].values,
                                                _df_write["value"].values))
        except Exception as err:
            LOG.error("ProcessToDB resulted in an error: {}".format(err))
