import shutil
from ftplib import FTP
import os
from datetime import datetime
import logging as LOG

CONN_STRING = os.environ["AZURE_CONN_STRING"]
USER_NAME = os.environ["AZURE_USER_NAME"]
PASSWORD = os.environ["AZURE_PASSWORD"]
ROOT_DIR = os.environ["AZURE_ROOT_DIR"]
DB_LOCATION = "db/marketdata.db"

# create the log folder, in case it does not exist
# the logging could crash in case the folder is not present
os.makedirs("log", exist_ok=True)

LOG.basicConfig(format='%(asctime)s %(message)s',
                filename="log/backend.log",
                level=LOG.INFO)


class AzureUpload():

    def __init__(self):
        pass

    def backupDB(self):
        # make a backup of the file
        try:
            LOG.info("Start with backup of db")
            _name, _ext = os.path.splitext(DB_LOCATION)
            _namecopy = "{}_{}".format(_name, datetime.now().strftime(
                "%Y%m%d"))
            _copylocation = "{}/old/{}{}".format(os.path.dirname(_namecopy),
                                                 os.path.basename(_namecopy),
                                                 _ext)
            shutil.copyfile(DB_LOCATION, _copylocation)

            LOG.info("Succesfully copied db to {}".format(_copylocation))
        except Exception as err:
            LOG.error("Backing up the db resulted in an error: {}".format(err))

    def copyToAzure(self):
        # copy to the FTP server of Azure
        try:
            LOG.info("Starting connection to Azure SFTP")
            ftp = FTP(CONN_STRING)
            ftp.login(user=USER_NAME, passwd=PASSWORD)
            ftp.cwd(ROOT_DIR)

            LOG.info("Start copy file to Azure SFTP")
            # copy to the server
            with open(DB_LOCATION, "rb") as f:
                ftp.storbinary("STOR {}".format(
                    os.path.basename(DB_LOCATION)), f)
                f.close()
            LOG.info("Succesfully copied {}".format(DB_LOCATION))
            ftp.quit()

            LOG.info("Succesfully logged off from Azure SFTP")
        except Exception as err:
            LOG.error("Backing up the db resulted in an error: {}".format(err))
