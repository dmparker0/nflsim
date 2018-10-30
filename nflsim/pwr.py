from .util import abbreviations, extractText
from requests import get
from bs4 import BeautifulSoup
from scipy import stats
import numpy as np
import pandas as pd
import re

class PWR(object):
    def __init__(self, weight=1, regress_to=None, values=None):
        self.weight = weight
        self.regress_to = regress_to
        if values is None:
            self.values = None
        else:
            self.values = values.copy()
        
    def calculate(self, **kwargs):
        self.pwrcol = [x for x in list(self.values) if x not in ['Team','Games Played']][0]
        return self
        
    def regress(self, df):
        self.values[self.pwrcol] = self.regress_to.regress(df, self.pwrcol)

    def addGamesPlayed(self, gamelog):
        if 'Games Played' not in self.values:
            grouped = gamelog.groupby('Team')['Games Played'].first().reset_index()
            self.values = pd.merge(self.values, grouped, on='Team')
        
class SRS(PWR):
    def __init__(self, weight=1, regress_to=None):
        PWR.__init__(self, weight, regress_to)
    
    def calculate(self, **kwargs):
        grouped = kwargs['gamelog'].groupby('Team').agg({'Difference':'sum','Opponent':lambda x: list(x)})
        grouped['Games Played'] = grouped['Opponent'].str.len()
        grouped['Margin'] = grouped['Difference'].values / grouped['Games Played'].values
        grouped['SRS'] = grouped['Margin']
        grouped['OldSRS'] = grouped['Margin']
        teams = grouped.to_dict('index')
        for i in range(10000):
            delta = 0.0
            for name, team in teams.items():
                sos = 0.0
                for opponent in team['Opponent']:
                    sos += teams[opponent]['SRS']
                teams[name]['OldSRS'] = team['SRS']
                teams[name]['SRS'] = team['Margin'] + (sos / team['Games Played'])
                delta = max(delta, abs(teams[name]['SRS'] - teams[name]['OldSRS']))
            if delta < 0.001:
                break
        srs_sum = 0.0
        for name, team in teams.items():
            srs_sum += teams[name]['SRS']
        srs_avg = srs_sum / len(teams)
        for name, team in teams.items():
            teams[name]['SRS'] = team['SRS'] - srs_avg
        df = pd.DataFrame.from_dict(teams, orient='index').reset_index()
        self.values = df.rename({'index':'Team'}, axis=1)[['Team','SRS']]
        self.pwrcol = 'SRS'
        return self
        
class FPI(PWR):
    def __init__(self, weight=1, regress_to=None):
        PWR.__init__(self, weight, regress_to)
        
    def calculate(self, **kwargs):
        url = 'http://www.espn.com/nfl/story/_/page/Football-Power-Index/espn-nfl-football-power-index'
        html = BeautifulSoup(get(url).text, features='lxml')
        tbl = html.select('article[data-id=Football-Power-Index] > div > div > aside > table')[0]
        self.values = pd.DataFrame(pd.read_html(str(tbl))[0].values, columns=['Team','X','X','X','X','FPI'])[['Team','FPI']]
        self.values['Team'] = [abbreviations[x.split()[1]] for x in self.values['Team'].values]
        self.pwrcol = 'FPI'
        return self
        
class DVOA(PWR):
    def __init__(self, weight=1, regress_to=None):
        PWR.__init__(self, weight, regress_to)
    
    def calculate(self, **kwargs):
        url = 'https://www.footballoutsiders.com/stats/teameff' + str(kwargs['season'])
        html = BeautifulSoup(get(url).text, features='lxml')
        tbl = html.select('table[class*=stats]')[0]
        data = pd.read_html(str(tbl), header=0)[0].values.tolist()
        data = [[abbreviations[x[1]], float(x[4].replace('%',''))] for x in data if '%' in x[4]]
        self.values = pd.DataFrame(data, columns=['Team','DVOA'])
        self.pwrcol = 'DVOA'
        return self

class Sagarin(PWR):
    def __init__(self, weight=1, regress_to=None):
        PWR.__init__(self, weight, regress_to)
    
    def calculate(self, **kwargs):
        url = 'https://www.usatoday.com/sports/nfl/sagarin/' + str(kwargs['season']) + '/rating/'
        html = BeautifulSoup(get(url).text, features='lxml')
        tbltext = html.select('section[id=section_sports]')[0].text
        tbltext = tbltext.replace('nbsp','').replace('\xa0','')
        tbltext = tbltext.replace('49ers','XXers')
        tbltext = extractText(tbltext, delim_left='HOME ADVANTAGE=', delim_right='__')
        tbltext = extractText(tbltext, delim_left=']&', delim_right='')
        tbltext = ''.join([x for x in tbltext if x not in ['&','(',')','|']])
        pattern = re.compile('([a-zA-Z ]+[ ])[=]([^a-zA-Z]*)')
        teamlist = []
        for (team, stats) in re.findall(pattern, tbltext):
            teamlist.append({'Team':team.strip().replace('XXers','49ers'),'Sagarin':float(stats.split()[0])})
        self.values = pd.DataFrame(teamlist)
        self.pwrcol = 'Sagarin'
        return self
        
class PWRsystems(object):
    def __init__(self, regress_to=None, srs=None, fpi=None, dvoa=None, sagarin=None, others=None):
        self.regress_to = regress_to
        self.systems = []
        if (srs is None) and (fpi is None) and (dvoa is None) and (sagarin is None) and (others is None):
            self.systems.append(SRS())
            self.systems.append(FPI())
            self.systems.append(DVOA())
            self.systems.append(Sagarin())
        else:
            pairs = [(srs, SRS),(fpi, FPI),(dvoa, DVOA),(sagarin, Sagarin)]
            for system in [{'Arg':x,'Class':y} for x, y in pairs]:
                if type(system['Arg']) is bool:
                    if system['Arg']:
                        self.systems.append(system['Class']())
                elif system['Arg'] is not None:
                    self.systems.append(system['Arg'])
            if others is not None:
                if isinstance(others, PWR):
                    self.systems.append(others)
                else:
                    for system in others:
                        self.systems.append(system)

    def combine(self):
        self.combined = self.systems[0].values[['Team']]
        for system in self.systems:
            self.combined = pd.merge(self.combined, system.values, on='Team', suffixes=('','_'))
            self.combined = self.combined[[x for x in self.combined if x != 'Games Played_']]
            new_z = stats.zscore(self.combined[system.pwrcol].values)
            new_weights = [system.weight] * self.combined.shape[0]
            if 'z_scores' not in self.combined:    
                self.combined['z_scores'] = [[x] for x in new_z]
                self.combined['weights'] = [[x] for x in new_weights]
            else:
                self.combined['z_scores'] = [x[0] + [x[1]] for x in list(zip(self.combined['z_scores'].values, new_z))]
                self.combined['weights'] = [x[0] + [x[1]] for x in list(zip(self.combined['weights'].values, new_weights))]
        zipped = zip(self.combined['z_scores'].values, self.combined['weights'].values)
        self.combined['Avg_z'] = [np.inner(x, y) / np.sum(y) for x, y in zipped]
        self.combined['PWR'] = self.combined['Avg_z'].values * 5
        return PWR(regress_to=self.regress_to, values=self.combined[['Team','PWR','Games Played']]).calculate()
