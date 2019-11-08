import pandas as pd
import numpy as np

class Regression(object):
    def __init__(self, to=None, weight=None, n_games=16):
        self.regression_values = to
        self.regression_weight = weight
        self.num_games = n_games
    
    def regress(self, df, pwrcol):
        mydf = pd.DataFrame()
        if self.regression_values is None:
            self.regression_values = np.mean(df[pwrcol].values)
        if type(self.regression_values) is not pd.DataFrame:
            reg_values = [self.regression_values] * df.shape[0]
            mydf = df
        else:
            merged = df.merge(self.regression_values, on='Team')
            reg_values = merged['Baseline'].values
            mydf = merged
        if self.regression_weight is not None:
            reg_weight = self.regression_weight * df.shape[0]
            played_weight = (1 - self.regression_weight) * df.shape[0]
            weight_sum = 1
        else:
            reg_weight = np.maximum(self.num_games - mydf['Games Played'].values, [0] * mydf.shape[0])
            played_weight = mydf['Games Played'].values
            weight_sum = reg_weight + played_weight
        played_weighted = mydf[pwrcol].values * played_weight
        regressed_weighted =  reg_values * reg_weight
        return (played_weighted + regressed_weighted) / weight_sum
