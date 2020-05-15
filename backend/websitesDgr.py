import pandas as pd
import sqlite3
from dateparser import parse
from bs4 import BeautifulSoup
import requests
import os
import logging as LOG
from pathlib import Path

DIRPATH = Path(os.path.dirname(__file__)).parent
DBLOCATION = os.path.join(DIRPATH, "db/marketdata.db")
LOGLOCATION = os.path.join(DIRPATH, "log/backend.log")

# create the log folder, in case it does not exist
# the logging could crash in case the folder is not present
os.makedirs(os.path.dirname(LOGLOCATION), exist_ok=True)

LOG.basicConfig(format='%(asctime)s %(message)s',
                filename=LOGLOCATION,
                level=LOG.INFO)


class UpdateDGR:

    def __init__(self):
        try:
            LOG.info("Start UpdateDGR object")
            self.urls = {"ABP":
                         "https://www.abp.nl/over-abp/"
                         "financiele-situatie/dekkingsgraad/",
                         "PFZW":
                         "https://www.pfzw.nl/over-ons/"
                         "dit-presteren-we/dekkingsgraad.html",
                         "BPF Bouw":
                         "https://www.bpfbouw.nl/over-bpfbouw/financiele-"
                         "situatie/overzicht-beleidsdekkingsgraad.aspx",
                         "PMT": "https://www.bpmt.nl/dekkingsgraden"}

        except Exception as err:
            LOG.error("Unable to load UpdateDGR object: {}".format(err))

    def updateDB(self):
        try:
            LOG.info("Starting the update dekkingsgraad process")
            # get the latest values from db
            _latestdgrdb = self.getLatestDgrFromDB()
            _insertquery = "INSERT INTO dekkingsgraad (date, name, value) " + \
                "VALUES (?, ?, ?)"

            _maxdatedgrwebsite = {}  # max date of the dekkingsgraad per fund
            _dgrwebsite = {}  # the dekkingsgraad value equal to site max date
            # get the latest values from websites

            # ABP
            _df_abp = self.getABP()
            _maxdatedgrwebsite.update({"ABP": max(_df_abp["date"])})
            _dgrwebsite.update({"ABP": _df_abp[
                _df_abp["date"] == max(_df_abp["date"])].values[0][2]})

            # PFZW
            _df_pfzw = self.getPFZW()
            _maxdatedgrwebsite.update({"PFZW": max(_df_pfzw["date"])})
            _dgrwebsite.update({"PFZW": _df_pfzw[
                _df_pfzw["date"] == max(_df_pfzw["date"])].values[0][2]})

            # Bouw
            _df_bouw = self.getBouw()
            _maxdatedgrwebsite.update({"BPF Bouw": max(_df_bouw["date"])})
            _dgrwebsite.update({"BPF Bouw": _df_bouw[
                _df_bouw["date"] == max(_df_bouw["date"])].values[0][2]})

            # PMT
            _df_pmt = self.getPMT()
            _maxdatedgrwebsite.update({"PMT": max(_df_pmt["date"])})
            _dgrwebsite.update({"PMT": _df_pmt[
                _df_pmt["date"] == max(_df_pmt["date"])].values[0][2]})

            for latestdb in _latestdgrdb:
                # latestdb[0] = date
                # latestdb[1] = name
                # latestdb[2] = value

                if _maxdatedgrwebsite[latestdb[1]] > parse(latestdb[0]):
                    LOG.info("{} heeft nieuwe dekkingsgraden gepubliceerd: "
                             "{:.1f}% per {}".format(
                                latestdb[1],
                                _dgrwebsite[latestdb[1]] * 100,
                                _maxdatedgrwebsite[
                                    latestdb[1]].strftime("%Y-%m-%d")))
                    conn = sqlite3.connect(DBLOCATION)
                    cur = conn.cursor()
                    cur.execute(_insertquery, [_maxdatedgrwebsite[
                        latestdb[1]].strftime("%Y-%m-%d"),
                                            latestdb[1],
                                            _dgrwebsite[latestdb[1]]])
                    conn.commit()
                    cur.close()
                else:
                    LOG.info("Geen nieuwe dekkingsgraden voor {}. "
                             "Laatste is per {}".format(
                                latestdb[1],
                                latestdb[0]))

        except Exception as err:
            LOG.error("updateDB result in error: {}".format(err))

    def getLatestDgrFromDB(self) -> list:
        try:
            _query = "SELECT MAX(date) AS [date], name, value FROM " + \
                    "dekkingsgraad GROUP BY name"

            conn = sqlite3.connect(DBLOCATION)
            cur = conn.cursor()
            cur.execute(_query)
            _list = cur.fetchall()
            cur.close()

            return _list
        except Exception as err:
            LOG.error("getLatestDgrFromDB result in error: {}".format(err))

    def getABP(self) -> pd.DataFrame:
        try:
            LOG.info("Retrieving latest dekkingsgraad from website ABP")
            _df = pd.read_html(self.urls["ABP"],
                               header=0)[0]

            # drop last value, given that is the "Beleidsdekkingsgraad"
            _df = _df[:-1]

            # change the percentage value to a floating type
            _df["Dekkingsgraad"] = _df["Dekkingsgraad"].str.replace(",", ".")
            _df["Dekkingsgraad"] = _df["Dekkingsgraad"].str.rstrip("%").astype(
                float) / 100

            # now make the format of the df equal to the structure in the db
            _df["name"] = "ABP"
            _df.rename(columns={"Maanden": "date", "Dekkingsgraad": "value"},
                       inplace=True)

            _df = _df[["date", "name", "value"]]

            # transform the date values to datetime
            _df = self.transformMonthsToDate(_df)

            LOG.info("Successfully retrieved latest dekkingsgraad"
                     "from website ABP")
            # return the df
            return _df

        except Exception as err:
            LOG.error("Retrieving dekkingsgraad from ABP result "
                      "in error: {}".format(err))

    def getPFZW(self) -> pd.DataFrame:
        try:
            LOG.info("Retrieving latest dekkingsgraad from website PFZW")
            # since PFZW does publish the dekkingsgraden as a table,
            # we need to scrape the values using bs4
            attrs = {"slot": "pfzw-collapsible--head"}

            _response = requests.get(self.urls["PFZW"])
            _soup = BeautifulSoup(_response.text, "html.parser")
            _results = _soup.find_all(name="span", attrs=attrs)

            # create empty dataframe where we will put the results
            _df = pd.DataFrame(columns=["date", "name", "value"])

            index = 0
            for dgrinfo in _results:
                # split the response in a list
                # for instance ["Februari 2020", "90,0%"]
                split = dgrinfo.get_text().strip().rsplit(" ", 1)
                _df.loc[index, "date"] = split[0]
                _df.loc[index, "name"] = "PFZW"
                # format the percentage string (eg 98,2%) to float
                # then copy to df
                _df.loc[index, "value"] = float(split[1].replace(
                    ",", ".").rstrip("%")) / 100
                index += 1

            # transform the date values to datetime
            _df = self.transformMonthsToDate(_df)

            LOG.info("Successfully retrieved latest dekkingsgraad"
                     "from website PFZW")

            return _df

        except Exception as err:
            LOG.error("Retrieving dekkingsgraad from PFZW result "
                      "in error: {}".format(err))

    def getPMT(self) -> pd.DataFrame:
        try:
            LOG.info("Retrieving latest dekkingsgraad from website PMT")
            # since PMT does publish the dekkingsgraden as a table,
            # we need to scrape the values using bs4
            attrs = {"class": "panel-body accordion-item"}

            _response = requests.get(self.urls["PMT"])
            _soup = BeautifulSoup(_response.text, "html.parser")
            _results = _soup.find_all(name="div", attrs=attrs)

            # create empty dataframe where we will put the results
            _df = pd.DataFrame(columns=["date", "name", "value"])

            index = 0
            for dgrinfo in _results:
                # first get the month
                _df.loc[index, "date"] = dgrinfo.find(name="span",
                                                      attrs={"class": "month"}
                                                      ).get_text()
                _df.loc[index, "name"] = "PMT"
                # format the percentage string (eg 98,2%) to float
                # then copy to df
                _df.loc[index, "value"] = float(
                    dgrinfo.find(
                        name="span",
                        attrs={"class": "data"}
                        ).get_text().replace(",", ".").rstrip("%")) / 100
                index += 1

            # transform the date values to datetime
            _df = self.transformMonthsToDate(_df)

            LOG.info("Successfully retrieved latest dekkingsgraad"
                     "from website PMT")

            return _df

        except Exception as err:
            LOG.error("Retrieving dekkingsgraad from PMT result "
                      "in error: {}".format(err))

    def getBouw(self) -> pd.DataFrame:
        try:
            LOG.info("Retrieving latest dekkingsgraad from website BPF Bouw")
            _df = pd.read_html(self.urls["BPF Bouw"],
                               header=0)[0]

            # change the percentage value to a floating type
            _df["Dekkingsgraad"] = _df["Dekkingsgraad"].str.replace(",", ".")
            _df["Dekkingsgraad"] = _df["Dekkingsgraad"].str.rstrip("%").astype(
                float) / 100

            # now make the format of the df equal to the structure in the db
            _df["name"] = "BPF Bouw"
            _df.rename(columns={"Datum": "date", "Dekkingsgraad": "value"},
                       inplace=True)

            _df = _df[["date", "name", "value"]]

            # transform the date values to datetime
            _df = self.transformMonthsToDate(_df)

            LOG.info("Successfully retrieved latest dekkingsgraad"
                     "from website BPF Bouw")

            return _df

        except Exception as err:
            LOG.error("Retrieving dekkingsgraad from BPF Bouw result "
                      "in error: {}".format(err))

    def transformMonthsToDate(self, df: pd.DataFrame) -> pd.DataFrame:
        try:
            # use the package from dateparser for ease of use
            _df_return = df.copy()

            for index, row in df.iterrows():
                _newdate = parse(row["date"],
                                 languages=["nl"],
                                 settings={"PREFER_DAY_OF_MONTH": "last"})

                _df_return.loc[index, "date"] = _newdate

            return _df_return
        except Exception as err:
            LOG.error("transformMonthsToDate restult in error: {}".format(err))
