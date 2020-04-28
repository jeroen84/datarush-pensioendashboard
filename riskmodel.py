import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
from sklearn import linear_model
import logging as LOG
import os

# create the log folder, in case it does not exist
# the logging could crash in case the folder is not present
os.makedirs("log", exist_ok=True)

LOG.basicConfig(format='%(asctime)s %(message)s',
                filename="log/riskmodel.log",
                level=LOG.INFO)


class RiskModelPF:

    def __init__(self):
        # to do: check whether df's are provided
        # in specific format
        try:
            LOG.info("Start MarketData object")
            pass
        except Exception as err:
            LOG.error("Unable to load RiskModelPF object: {}".format(err))

    def runLinearModel(self,
                       df_marketdata: pd.DataFrame,
                       df_dgr: pd.DataFrame):
        try:

            self.df_marketdata = df_marketdata.dropna()
            self.df_dgr = df_dgr.pivot_table(values="dekkingsgraad",
                                             index="date",
                                             columns="fonds")
            self.fondsen = self.df_dgr.columns

            # first, forward fill the market data
            # df to include weekends and holidays
            _df_marketdata_ffil = self.df_marketdata.copy()

            _idx = pd.date_range(_df_marketdata_ffil.index.min(),
                                 _df_marketdata_ffil.index.max())
            _df_marketdata_ffil.index = pd.DatetimeIndex(
                _df_marketdata_ffil.index)
            _df_marketdata_ffil = _df_marketdata_ffil.reindex(_idx,
                                                              method="ffill")

            # initiate the dict for the models
            self.regr_model = {}

            for fund in self.fondsen:
                _df_dgr = pd.DataFrame(self.df_dgr[fund])
                # join the dataframes, given the difference
                # in frequency (dgr are monthly)

                _df_join = _df_dgr.join(_df_marketdata_ffil,
                                        how="left").dropna()

                # create features and label sets
                _X = _df_join.drop(columns=fund)
                _y = _df_join[fund]

                # create test and train sets
                _X_train, _X_test, _y_train, _y_test = train_test_split(_X, _y)

                # Create linear regression object
                _regr = linear_model.LinearRegression()

                # Train the model using the training sets
                _regr.fit(_X_train, _y_train)

                _y_pred = _regr.predict(_X_test)

                LOG.info("Linear model succesfully fitted for {}.".format(
                    fund))
                LOG.info("The specifics for the model of {} are:".format(fund))
                LOG.info("Period from {} to {}".format(_df_join.index.min(),
                                                       _df_join.index.max()))
                LOG.info("Coefficients: {}".format(
                    list(zip(_df_marketdata_ffil.columns,
                             _regr.coef_))))
                LOG.info("Intercept: {:3f}".format(_regr.intercept_))
                LOG.info("Coefficient of determination: {:3f}".format(
                    r2_score(_y_test, _y_pred)))

                self.regr_model.update({fund: _regr})

            return self.regr_model
        except Exception as err:
            LOG.error("runLinearModel results in an error: {}".format(err))

    def makePrediction(self, df_input: pd.DataFrame = None):
        # predict using an input df with the
        # 5 (for now) market data risk factors
        # default behavior: predict with data point beyond
        # the latest know official dgr numbers

        if self.regr_model is None:
            raise Exception("No model available. First run the model.")

        try:
            # if df_input is None, that means no override of df
            if df_input is None:
                # make a copy of marketdata df, since we need to
                # do some changes
                _df_marketdata = self.df_marketdata.copy()
            else:
                _df_marketdata = df_input.copy()

            _df_dgr = self.df_dgr.copy()

            # now predict for each fund
            # we could use self.funds, or based the funds on
            # the dict of self.regr_model
            # since we can only predict with the models in the
            # dict, do a loop on the dict
            # and return the dict
            _dfs_predict = {}

            for fund in self.regr_model:
                _df_input = _df_marketdata[
                    _df_marketdata.index > _df_dgr[fund].dropna().index.max()
                    ]
                _predict_values = self.regr_model[fund].predict(_df_input)
                _dfs_predict.update({fund:
                                     pd.DataFrame(data=_predict_values,
                                                  index=_df_input.index,
                                                  columns={"dekkingsgraad"})})
                LOG.info("Succesfully predicted values for {}".format(fund))
                LOG.info("Predictions are for period {} to {}".format(
                    _df_input.index.min(), _df_input.index.max()
                ))

            self.df_predict = _dfs_predict

        except Exception as err:
            LOG.error("makePrediction results in an error: {}".format(err))

    def makeContribution(self, df_input: pd.DataFrame = None):
        # predict using an input df with the
        # 5 (for now) market data risk factors
        # default behavior: predict with data point beyond
        # the latest know official dgr numbers

        if self.regr_model is None:
            raise Exception("No model available. First run the model.")

        try:
            # if df_input is None, that means no override of df
            if df_input is None:
                # make a copy of marketdata df, since we need to
                # do some changes
                _df_marketdata = self.df_marketdata.copy()
            else:
                _df_marketdata = df_input.copy()

            _df_dgr = self.df_dgr.copy()

            # now predict for each fund and determine
            # the contribution of each risk factor
            _dfs_contribution = {}

            for fund in self.regr_model:
                _df_input = _df_marketdata[
                    _df_marketdata.index > _df_dgr[fund].dropna().index.max()
                    ]

                _df_input_firstrow = _df_input.iloc[:1]

                # create blank dataframe for each fund, which is
                # then added to the return dict per fund
                _predict_values = pd.DataFrame(index=_df_input.index)

                for riskfactor in _df_input.columns:
                    _df_input_contribution = _df_input.copy()

                    # fill all columns other than riskfactor
                    # with the first value of the df
                    _df_input_contribution.loc[
                        :, ~_df_input_contribution.columns.isin([riskfactor])
                        ] = _df_input_firstrow.loc[
                        :, ~_df_input_firstrow.columns.isin([riskfactor])
                        ]
                    _df_input_contribution.ffill(inplace=True)
                    _predict = self.regr_model[fund].predict(
                        _df_input_contribution)
                    _predict_values = _predict_values.merge(right=pd.DataFrame(
                                                  data=_predict,
                                                  index=_df_input.index,
                                                  columns={riskfactor}).diff(
                                                  ).fillna(0),
                                                  on="date")

                # return the contributions as a df
                _dfs_contribution.update({fund: _predict_values})

                LOG.info("Succesfully made contribution values for {}".format(
                    fund))
                LOG.info("Contributions are for period {} to {}".format(
                    _df_input.index.min(), _df_input.index.max()
                ))

            self.df_contribution = _dfs_contribution

        except Exception as err:
            LOG.error("makeContribution results in an error: {}".format(err))
