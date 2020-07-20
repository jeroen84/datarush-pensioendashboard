import pandas as pd
from sqlalchemy import create_engine
import os
from pathlib import Path

DIRPATH = Path(os.path.dirname(__file__)).parent
DBLOCATION = os.path.join(DIRPATH, "db/marketdata.db")
DBCONNECTION = create_engine("sqlite:///{}".format(DBLOCATION))


class DataImport:

    def __init__(self):
        # error handling
        self.conn = DBCONNECTION

        self.df_marketdata = self.loadMarketData()
        self.df_dgr = self.loadDekkingsgraden()
        self.df_marketdatanames = self.loadMarketDataNames()
        self.df_countryexposure = self.loadCountryExposure()
        self.df_predict = self.loadDGRPrediction()
        self.df_contribution = self.loadDGRContribution()

    def loadMarketData(self) -> pd.DataFrame:
        _query = "SELECT date, name, value FROM marketdata ORDER BY date"
        _df = pd.read_sql(_query, self.conn, index_col="date",
                          parse_dates={"date": "%Y-%m-%d"})
        _df = _df.pivot_table(values="value", index="date", columns="name")
        _df.ffill(inplace=True)
        return _df

    def loadMarketDataNames(self) -> dict:
        _query = "SELECT short_name, long_name FROM marketdata_names"
        _df = pd.read_sql(_query, self.conn)

        return dict(_df.to_dict("split")["data"])

    def loadDekkingsgraden(self) -> pd.DataFrame:
        _query = "SELECT date, name AS fonds, value AS dekkingsgraad " \
            "FROM dekkingsgraad"
        _df_dgr = pd.read_sql(_query, self.conn,
                              parse_dates={"date": "%Y-%m-%d"}).sort_values(
                                  "date")
        _df_dgr["dekkingsgraad"] = _df_dgr["dekkingsgraad"] * 100

        return _df_dgr

    def loadCountryExposure(self) -> pd.DataFrame:
        _query = "SELECT * FROM country_exposures"
        _df = pd.read_sql(_query, self.conn, index_col="date",
                          parse_dates={"date": "%Y-%m-%d"})

        return _df

    def loadDGRPrediction(self) -> pd.DataFrame:
        _query = "SELECT date, fund, value AS dekkingsgraad FROM " \
            "dgr_prediction_latest"
        _df = pd.read_sql(_query, self.conn, index_col="date",
                          parse_dates={"date": "%Y-%m-%d"})

        return _df

    def loadDGRContribution(self) -> pd.DataFrame:
        _query = "SELECT date, fund, [index], value FROM " \
            "dgr_contribution_latest"
        _df = pd.read_sql(_query, self.conn, index_col="date",
                          parse_dates={"date": "%Y-%m-%d"})

        return _df

    def closeConnection(self):
        pass
        # self.engine.close()
