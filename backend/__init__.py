import os
from pathlib import Path
import logging as LOG
from datetime import datetime
import shutil
from sqlalchemy import create_engine

DIRPATH = Path(os.path.dirname(__file__)).parent
DBLOCATION = os.path.join(DIRPATH, "db/marketdata.db")
LOGLOCATION = os.path.join(DIRPATH, "log/backend.log")
DBCONNECTION = create_engine("sqlite:///{}".format(DBLOCATION))


def backupDB():
    # make a backup of the file
    try:
        LOG.info("Start with backup of db")
        _name, _ext = os.path.splitext(DBLOCATION)
        _namecopy = "{}_{}".format(_name, datetime.now().strftime(
            "%Y%m%d"))
        _copylocation = "{}/old/{}{}".format(os.path.dirname(_namecopy),
                                             os.path.basename(_namecopy),
                                             _ext)
        shutil.copyfile(DBLOCATION, _copylocation)

        LOG.info("Succesfully copied db to {}".format(_copylocation))
    except Exception as err:
        LOG.error("Backing up the db resulted in an error: {}".format(err))


# this script runs all the backend script in sequence.
if __name__ == "__main__":
    from marketdata import MarketData
    from websitesDgr import UpdateDGR
    from dataimport import DataImport
    from riskmodel import RiskModelPF

    # first, backup the database
    backupDB()

    # update market data
    data = MarketData()
    data.UpdateEquityAndFX()
    data.UpdateInterestRates()

    # # update dekkingsgraad data
    update = UpdateDGR()
    update.updateDB()

    # update the risk metrics
    dataimport = DataImport()
    riskmodel = RiskModelPF(dataimport.df_marketdata, dataimport.df_dgr)
    riskmodel.runLinearModel()
    riskmodel.makePrediction()
    riskmodel.makeContribution()
