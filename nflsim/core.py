from .gamedata import getTeams, getScores, adjustScores
from .pwr import PWRsystems
from .regression import Regression
from .tiebreak import getPlayoffSeeding
from joblib import Parallel, delayed
from scipy import stats
import pandas as pd
import numpy as np

class Simulate(object):
    def __init__(self, season, n_sims, pwr_systems=None, rank_adj=2, home_adj=3, st_dev=13):
        self.season = season
        self.n_sims = n_sims
        self.rank_adj = rank_adj
        self.home_adj = home_adj
        self.st_dev = st_dev
        if pwr_systems is None:
            self.pwr_systems = PWRsystems()
        else:
            self.pwr_systems = pwr_systems
        self.teams = getTeams(self.season)
        self.scores = getScores(self.season)
        self.played = self.scores[self.scores['HomePts'].notnull()]
        self.unplayed = self.scores[~self.scores['HomePts'].notnull()]
        played_adj = adjustScores(self.played, self.home_adj)
        for system in self.pwr_systems.systems:
            system.calculate(gamelog=played_adj, season=self.season)
            system.addGamesPlayed(played_adj)
            self.regress(system)
        self.pwr = self.pwr_systems.combine()
        self.regress(self.pwr)

    def run(self, parallel=True, combine=True):
        simulations = []
        if parallel:
            simulations = Parallel(n_jobs=-1)(delayed(self.simulate)() for i in range(self.n_sims))
        else:
            for i in range(self.n_sims):
                simulations.append(self.simulate())
        self.simulations = Simulations(simulations, self.teams)
        if combine:
            self.simulations.combine()
            self.playoffs = self.simulations.playoffs
            self.standings = self.simulations.standings
        return self

    def simulate(self):
        return Simulation(self)

    def regress(self, system):
        if system.regress_to is not None:
            if type(system.regress_to) is not Regression:
                system.regress_to = Regression(to=system.regress_to)
            system.regress(system.values)

class Simulation(object):
    def __init__(self, sim):
        self.rankings = sim.pwr.values.copy()
        self.rankings['PWR'] = self.rankings['PWR'].values - np.random.normal(0, sim.rank_adj, self.rankings.shape[0])
        simulated = self.simulateSeason(sim)
        self.regularseason = pd.concat([sim.played, simulated])
        adjusted = adjustScores(self.regularseason, sim.home_adj)
        mapper = {'Team':'Opponent','Conference':'OppConference','Division':'OppDivision'}
        df = pd.merge(pd.merge(adjusted, sim.teams, on='Team'), sim.teams.rename(mapper, axis=1), on='Opponent')
        self.standings = pd.merge(df.groupby(['Team']).agg({'Wins':'sum'}).reset_index(), self.rankings, on='Team')[['Team','Wins','PWR']]
        self.seeding = getPlayoffSeeding(df)
        self.playoffs = self.simulatePlayoffs(sim)

    #simulates games in a gamelog
    def simulateSeason(self, sim) -> pd.DataFrame:
        merged = pd.merge(sim.unplayed, self.rankings.rename({'Team':'Home'}, axis=1), on='Home').rename({'PWR':'Home PWR'}, axis=1)
        merged = pd.merge(merged, self.rankings.rename({'Team':'Away'}, axis=1), on='Away').rename({'PWR':'Away PWR'}, axis=1)
        home_pwr_difference = (merged['Home PWR'].values + sim.home_adj) - merged['Away PWR'].values
        home_win_probability = 1 - stats.norm(home_pwr_difference, sim.st_dev).cdf(0)
        random_values = np.random.random(merged.shape[0])
        is_home_winner = random_values < home_win_probability
        merged['HomePts'] = is_home_winner.astype(int)
        merged['AwayPts'] = (~is_home_winner).astype(int)
        return merged[['Home','Away','HomePts','AwayPts']]
        
    #simulates nfl playoffs
    def simulatePlayoffs(self, sim) -> pd.DataFrame:
        seeds = self.seeding.set_index(['Conference','Seed']).to_dict('index')
        teamseeds = self.seeding.set_index('Team').to_dict('index')
        ranks = self.rankings.set_index('Team').to_dict('index')
        results = {}
        for conf in ['NFC','AFC']:
            #simulate round one
            r1_winners = [self.getWinner(seeds[(conf, pair[0])]['Team'], seeds[(conf, pair[1])]['Team'], ranks, sim.home_adj, sim.st_dev) 
                          for pair in [(3,6),(4,5)]]
            #simulate round two
            better = seeds[(conf, min([teamseeds[x]['Seed'] for x in r1_winners]))]['Team']
            worse = [x for x in r1_winners if x != better][0]
            r2_winners = [self.getWinner(seeds[(conf, pair[0])]['Team'], pair[1], ranks, sim.home_adj, sim.st_dev) 
                          for pair in [(1, worse),(2, better)]]
            #simulate round three
            hometeam = seeds[(conf, min([teamseeds[x]['Seed'] for x in r2_winners]))]['Team']
            awayteam = [x for x in r2_winners if x != hometeam][0]
            r3_winner = self.getWinner(hometeam, awayteam, ranks, sim.home_adj, sim.st_dev)
            results[conf + ' Champion'] = r3_winner
            results[conf + ' Runner-up'] = awayteam if r3_winner == hometeam else hometeam
        nfc_champ = results['NFC Champion']
        afc_champ = results['AFC Champion']
        results['Super Bowl Champion'] = self.getWinner(nfc_champ, afc_champ, ranks, home_adj=0, stdev=sim.st_dev)
        results['Super Bowl Runner-up'] = afc_champ if results['Super Bowl Champion'] == nfc_champ else nfc_champ
        return pd.DataFrame(results, index=[0])

    #simulates a single game and returns the winner
    def getWinner(self, hometeam, awayteam, ranks, home_adj, stdev):
        home_pwr_difference = (ranks[hometeam]['PWR'] + home_adj) - ranks[awayteam]['PWR']
        home_win_probability = 1 - stats.norm(home_pwr_difference, stdev).cdf(0)
        is_home_winner = np.random.random() < home_win_probability
        return hometeam if is_home_winner else awayteam
            
class Simulations(object):
    def __init__(self, values, teams):
        self.values = values
        self.teams = teams

    def combine(self):
        playoffs = pd.concat([x.playoffs for x in self.values]).reset_index(drop=True)
        def pivotseeding(df):
            df['ConferenceSeed'] = df['Conference'].str.cat(df['Seed'].astype(str), sep='-')
            df['Group'] = 1
            return df.pivot(index='Group', columns='ConferenceSeed', values='Team')
        seeding = pd.concat([pivotseeding(x.seeding) for x in self.values]).reset_index(drop=True)
        self.playoffs = pd.concat([seeding, playoffs], axis=1)
        self.standings = pd.concat([x.standings for x in self.values])
        self.standings = self.standings.groupby(['Team']).agg({'Wins':'mean','PWR':'mean'}).reset_index()
        self.standings = pd.merge(self.standings, self.teams, on='Team')[['Team','Wins','PWR','Conference','Division']]
        return self
