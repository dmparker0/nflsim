import pandas as pd

class Regression(object):
    def __init__(self, to=0, weight=None, n_games=16, basecol='Baseline'):
        self.regression_values = to
        self.regression_weight = weight
        self.num_games = n_games
    
    def regress(self, df, pwrcol):
        mydf = pd.DataFrame()
        if type(self.regression_values) is not pd.DataFrame:
            reg_values = [self.regression_values] * df.shape[0]
            mydf = df
        else:
            merged = pd.merge(self.regression_values, df, on='Team')
            reg_values = merged[basecol].values
            mydf = merged
        if self.regression_weight is not None:
            reg_weight = self.regression_weight * df.shape[0]
            played_weight = (1 - self.regression_weight) * df.shape[0]
            weight_sum = 1
        else:
            reg_weight = self.num_games - mydf['Games Played'].values
            played_weight = mydf['Games Played'].values
            weight_sum = self.num_games
        played_weighted = mydf[pwrcol].values * played_weight
        regressed_weighted =  reg_values * reg_weight
        return (played_weighted + regressed_weighted) / weight_sum