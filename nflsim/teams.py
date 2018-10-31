from pandas import DataFrame
from itertools import compress

class Team(object):
    def __init__(self, name, conf=None, div=None, pwr=None, seed=None):
        self.name = name
        self.conference = conf
        self.division = div
        self.pwr = pwr
        self.seed = seed

class Teams(object):
    def __init__(self, values, indexed=False):
        if type(values) is DataFrame:
            teamdict = values.to_dict('records')
            self.values = [Team(name=x['Team'], conf=x['Conference'], div=x['Division'], 
                                pwr=x['PWR'], seed=x['Seed']) for x in teamdict]
        else:
            self.values = values
        self.indexed = indexed

    def index(self, name=False, conf=False, div=False, seed=False):
        attrs = ['name','conference','division','seed']
        bools = [name, conf, div, seed]
        indices = list(compress(attrs, bools))
        multi_index = len(indices) != 1
        val_dict = {}
        for team in self.values:
            if multi_index:
                key = tuple([getattr(team, x) for x in indices])
            else:
                key = getattr(team, indices[0])
            if key in val_dict:
                val_dict[key] = val_dict[key] + [team]
            else:
                val_dict[key] = [team]
        self.values = val_dict
        self.indexed = True
        return self

    def copy(self, reset_index=True):
        if not reset_index:
            return Teams(self.values, indexed=self.indexed)
        elif self.indexed:
            return Teams([x for y in [x for i, x in self.items()] for x in y])
        else:
            return Teams(self.values)            

    def len(self):
        return len(self.values)

    def items(self):
        return self.values.items()

    def keys(self):
        if self.indexed:
            return list(self.values)
