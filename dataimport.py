import pandas as pd
from sqlalchemy import create_engine
import os

DIRPATH = os.path.dirname(os.path.realpath(__file__))
DBLOCATION = os.path.join(DIRPATH, "db/marketdata.db")


class DataImport:

    def __init__(self, source=DBLOCATION):
        # by initiating the class, load the datasets
        self.source = source
        # error handling
        self.startConnection()
        self.refreshData()

    def refreshData(self):
        self.df_marketdata = self.loadMarketData()
        self.df_dgr = self.loadDekkingsgraden()
        self.df_marketdatanames = self.loadMarketDataNames()
        self.df_countryexposure = self.loadCountryExposure()

    def startConnection(self):
        self.engine = create_engine("sqlite:///{}".format(self.source))

    def loadMarketData(self) -> pd.DataFrame:
        _query = "SELECT date, name, value FROM marketdata ORDER BY date"
        _df = pd.read_sql(_query, self.engine, index_col="date",
                          parse_dates={"date": "%Y-%m-%d"})
        _df = _df.pivot_table(values="value", index="date", columns="name")
        _df.ffill(inplace=True)
        return _df

    def loadMarketDataNames(self) -> dict:
        _query = "SELECT short_name, long_name FROM marketdata_names"
        _df = pd.read_sql(_query, self.engine)

        return dict(_df.to_dict("split")["data"])

    def loadDekkingsgraden(self) -> pd.DataFrame:
        _query = "SELECT date, name, value FROM dekkingsgraad"
        _df_dgr = pd.read_sql(_query, self.engine,
                              parse_dates={"date": "%Y-%m-%d"}).sort_values(
                                  "date")
        _df_dgr["value"] = _df_dgr["value"] * 100
        _df_dgr.rename(columns={"name": "fonds",
                                "value": "dekkingsgraad"}, inplace=True)

        return _df_dgr

    def loadCountryExposure(self) -> pd.DataFrame:
        _query = "SELECT * FROM country_exposures"
        _df = pd.read_sql(_query, self.engine, index_col="date",
                          parse_dates={"date", "%Y-%m-%d"})

        return _df

    def closeConnection(self):
        pass
        # self.engine.close()
