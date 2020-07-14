# test if environment variables are set

# test if connections to API's can be made

# test if connection to DB can be made

# test if DB is filled

# test dependencies

# from tests.conftest import market_data
from ..backend.marketdata import EQUITYTICKER, MarketData
import pytest

data = MarketData()
SWAPTICKER = {"EUSA30":
              "https://www.iex.nl/"
              "Rente-Koers/61375432/IRS-30Y-30-360-ANN-6M-EURIBOR/"
              "historische-koersen.aspx"}
EQUITYTICKER = {"IWDA.AS":
                "https://www.iex.nl/"
                "Beleggingsfonds-Koers/319919/"
                "iShares-Core-MSCI-World-UCITS-ETF/"
                "historische-koersen.aspx",
                "EMIM.AS":
                "https://www.iex.nl/"
                "Beleggingsfonds-Koers/608862/"
                "iShares-Core-MSCI-Emerging-Markets-IMI-UCITS-ETF/"
                "historische-koersen.aspx",
                "GSG":
                None}


def test_dbdata_available():
    assert data.df_db.empty is False


def test_alphavantage_available():
    df = data.ts.get_daily("IWDA.AS", outputsize="compact")
    assert df is not None


def test_foreignexchange_available():
    df = data.cc.get_currency_exchange_daily(
        from_symbol="EUR",
        to_symbol="USD",
        outputsize="compact")
    assert df is not None


def test_iexscraper_swap_available():
    ticker = list(SWAPTICKER)[0]
    df = data.IEXScraper(ticker, SWAPTICKER[ticker])
    assert df.empty is False


def test_iexscraper_equity_available():
    for equity in EQUITYTICKER:
        if EQUITYTICKER[equity] is not None:
            df = data.IEXScraper(equity, EQUITYTICKER[equity])
            assert df.empty is False
