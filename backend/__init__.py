from dotenv import load_dotenv
import os
from pathlib import Path
import logging as LOG
from datetime import datetime
import shutil

DIRPATH = Path(os.path.dirname(__file__)).parent
DBLOCATION = os.path.join(DIRPATH, "db/marketdata.db")
LOGLOCATION = os.path.join(DIRPATH, "log/backend.log")
# load the environment variables
load_dotenv(os.path.join(DIRPATH.parent, ".env"))


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
    # first, backup the database
    backupDB()

    # update market data
    data = MarketData()
    data.UpdateEquityAndFX()
    data.UpdateInterestRates()

    # # update dekkingsgraad data
    update = UpdateDGR()
    update.updateDB()
