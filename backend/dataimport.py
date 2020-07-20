import pandas as pd
from sqlalchemy import create_engine
import os
from pathlib import Path

DIRPATH = Path(os.path.dirname(__file__)).parent
DBLOCATION = os.path.join(DIRPATH, "db/marketdata.db")
DBCONNECTION = create_engine("sqlite:///{}".format(DBLOCATION))


class DataImport:

    def __init__(self):
        # to do: error handling
        pass

    def getMarketData(self) -> pd.DataFrame:
        _query = "SELECT date, name, value FROM marketdata ORDER BY date"
        _df = pd.read_sql(_query, DBCONNECTION, index_col="date",
                          parse_dates={"date": "%Y-%m-%d"})
        _df = _df.pivot_table(values="value", index="date", columns="name")
        _df.ffill(inplace=True)
        return _df

    def getMarketDataNames(self) -> dict:
        _query = "SELECT short_name, long_name FROM marketdata_names"
        _df = pd.read_sql(_query, DBCONNECTION)

        return dict(_df.to_dict("split")["data"])

    def getDekkingsgraden(self) -> pd.DataFrame:
        _query = "SELECT date, name AS fonds, value AS dekkingsgraad " \
            "FROM dekkingsgraad"
        _df_dgr = pd.read_sql(_query, DBCONNECTION,
                              parse_dates={"date": "%Y-%m-%d"}).sort_values(
                                  "date")
        _df_dgr["dekkingsgraad"] = _df_dgr["dekkingsgraad"] * 100

        return _df_dgr

    def getCountryExposure(self) -> pd.DataFrame:
        _query = "SELECT * FROM country_exposures"
        _df = pd.read_sql(_query, DBCONNECTION, index_col="date",
                          parse_dates={"date": "%Y-%m-%d"})

        return _df

    def getDGRPrediction(self) -> pd.DataFrame:
        _query = "SELECT date, fund, value AS dekkingsgraad FROM " \
            "dgr_prediction_latest"
        _df = pd.read_sql(_query, DBCONNECTION, index_col="date",
                          parse_dates={"date": "%Y-%m-%d"})

        return _df

    def getDGRContribution(self) -> pd.DataFrame:
        _query = "SELECT date, fund, [index], value FROM " \
            "dgr_contribution_latest"
        _df = pd.read_sql(_query, DBCONNECTION, index_col="date",
                          parse_dates={"date": "%Y-%m-%d"})

        return _df

    def closeConnection(self):
        pass
        # self.engine.close()

    @property
    def marketdata(self):
        return self.getMarketData()

    @property
    def marketdatanames(self):
        return self.getMarketDataNames()

    @property
    def dekkingsgraden(self):
        return self.getDekkingsgraden()

    @property
    def countryexposure(self):
        return self.getCountryExposure()

    @property
    def dgr_prediction(self):
        return self.getDGRPrediction()

    @property
    def dgr_contribution(self):
        return self.getDGRContribution()
