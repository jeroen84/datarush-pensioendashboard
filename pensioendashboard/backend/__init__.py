import os
import time
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

        # remove oldest backup; in order to save disk space
        # logic is: remove backups older than 30 days
        days = 30
        seconds = days * 24 * 60 * 60
        now = time.time()
        backupLocation = os.path.dirname(_copylocation)

        LOG.info("Remove old backups")

        for f in os.listdir(backupLocation):
            f = os.path.join(backupLocation, f)
            if os.stat(f).st_mtime < now - seconds:
                if os.path.isfile(f) and f.endswith(".db"):
                    if os.path.isfile(f):
                        os.remove(os.path.join(backupLocation,
                                  f))
                        LOG.info(
                            "Removed old log file {}".format(f)
                        )

    except Exception as err:
        LOG.error("Backing up the db resulted in an error: {}".format(err))


def purgeDB():
    # clean db entries for dgr_prediction and
    # dgr_contribution older than X months
    try:
        _MONTHS = 2
        _query = [
            """DELETE FROM dgr_prediction WHERE """
            """date(date_run) < date("now", "-{} month")""".format(_MONTHS),
            """DELETE FROM dgr_contribution WHERE date(date_run) """
            """< date("now", "-{} month")""".format(_MONTHS)
            ]
        con = DBCONNECTION.connect()

        for query in _query:
            con.execute(query)

        con.close()

    except Exception as err:
        LOG.error("Purging the db resulted in an error: {}".format(err))


# this script runs all the backend script in sequence.
if __name__ == "__main__":
    from marketdata import MarketData
    from websitesDgr import UpdateDGR
    from dataimport import DataImport
    from riskmodel import RiskModelPF

    # first, backup the database
    backupDB()
    purgeDB()

    # update market data
    data = MarketData()
    data.UpdateEquityAndFX()
    data.UpdateInterestRates()

    # update dekkingsgraad data
    update = UpdateDGR()
    update.updateDB()

    # update the risk metrics
    dataimport = DataImport()
    riskmodel = RiskModelPF(dataimport.marketdata, dataimport.dekkingsgraden)
    riskmodel.runLinearModel()
    riskmodel.makePrediction()
    riskmodel.makeContribution()
