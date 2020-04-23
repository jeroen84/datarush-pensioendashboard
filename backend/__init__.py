from marketdata import MarketData
from websitesDgr import UpdateDGR
from uploadtoAzure import AzureUpload
import sys

# this script runs all the backend script in sequence.

if __name__ == "__main__":
    # update market data
    data = MarketData()
    data.UpdateEquityAndFX()
    data.UpdateInterestRates()

    # # update dekkingsgraad data
    update = UpdateDGR()
    update.updateDB()
    if len(sys.argv) == 1:  # no arguments
        # upload to Azure
        backup = AzureUpload()
        backup.backupDB()
        backup.copyToAzure()
    elif sys.argv[1] == "--no-azure":
        print("No upload to Azure")
    else:
        # ignore any other arguments
        pass
