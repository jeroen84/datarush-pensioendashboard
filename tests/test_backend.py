# test if environment variables are set

# test if connections to API's can be made

# test if connection to DB can be made

# test if DB is filled

# test dependencies

# from tests.conftest import market_data
from ..backend.marketdata import EQUITYTICKER, SWAPTICKER, MarketData
from dateutil.relativedelta import relativedelta
from datetime import date

data = MarketData()
# number of days in which you can say that the
# data is 'recent'. Is very arbitrary.
RECENTDAYS = 3


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

    # is the dataframe empty? should not be
    assert df.empty is False
    # do you get recent data?
    assert max(df.index) >= date.today() - relativedelta(days=RECENTDAYS)


def test_iexscraper_equity_available():
    for equity in EQUITYTICKER:
        if EQUITYTICKER[equity] is not None:
            df = data.IEXScraper(equity, EQUITYTICKER[equity])

            # is the dataframe empty? should not be
            assert df.empty is False
            # do you get recent data?
            assert max(df.index) >= date.today() - \
                relativedelta(days=RECENTDAYS)
