from .gamedata import getTeams, getScores, adjustScores
from .pwr import PWRsystems
from .regression import Regression
from .simulate import simulateBracket, simulateGame, simulateGamelog
from .teams import Team, Teams
from .tiebreak import getPlayoffSeeding
from .util import playoff_game_ids
from joblib import Parallel, delayed
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
        self.played = self.scores[self.scores['Played']][['Home','Away','HomePts','AwayPts']]
        self.unplayed = self.scores[~self.scores['Played']][['Home','Away','HomePts','AwayPts']]
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
        self.simulations = Simulations(simulations, combine)
        return self

    def playoffs(self, reindex=False):
        if self.simulations.combined:
            return self.copied(self.simulations.playoffs.copy(), reindex)

    def regularseason(self, reindex=False):
        if self.simulations.combined:
            return self.copied(self.simulations.regularseason.copy(), reindex)
    
    def seeding(self, reindex=False):
        if self.simulations.combined:
            return self.copied(self.simulations.seeding.copy(), reindex)
    
    def standings(self, reindex=False):
        if self.simulations.combined:
            return self.copied(self.simulations.standings.copy(), reindex)

    def copied(self, df, reindex):
        if reindex:
            return df.reset_index(level='Simulation')
        else:
            return df
            
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
        if not sim.unplayed.empty:
            simulated = simulateGamelog(sim.unplayed, self.rankings, sim.home_adj, sim.st_dev, 0.05)
            self.regularseason = pd.concat([sim.played, simulated.rename({'Home Wins':'HomePts','Away Wins':'AwayPts'}, axis=1)])
        else:
            self.regularseason = sim.played
        adjusted = adjustScores(self.regularseason, sim.home_adj)
        mapper = {'Team':'Opponent','Conference':'OppConference','Division':'OppDivision'}
        df = pd.merge(pd.merge(adjusted, sim.teams, on='Team'), sim.teams.rename(mapper, axis=1), on='Opponent')
        self.standings = pd.merge(df.groupby(['Team','Conference','Division']).agg({'Wins':'sum'}).reset_index(), 
                                  self.rankings, on='Team').drop('Games Played', axis=1)
        self.seeding = getPlayoffSeeding(df)
        self.playoffs = self.simulatePlayoffs(sim)
        
    #simulates nfl playoffs
    def simulatePlayoffs(self, sim):
        teams = Teams(pd.merge(self.standings, self.seeding, on='Team', suffixes=('', '_')).drop('Conference_', axis=1)).index(conf=True)
        results = {}
        for conference in set(teams.keys()):
            bracket = simulateBracket(Teams(teams.values[conference]), sim.home_adj, sim.st_dev)
            results = {**results, **{(conference, i):x for i, x in bracket.items()}}
        results = dict((playoff_game_ids[key], value) for (key, value) in results.items())
        teams = teams.copy().index(name=True)
        afc_champ = teams.values[results[('AFC','Championship',1)]['Winner']][0]
        nfc_champ = teams.values[results[('NFC','Championship',1)]['Winner']][0]
        result = simulateGame(afc_champ, nfc_champ, home_adj=0, st_dev=sim.st_dev)
        results[('NFL','Super Bowl',1)] = {'Winner':result['Winner'].name,'Loser':result['Loser'].name}
        df = pd.DataFrame.from_dict(results, orient='index').reset_index()
        df[['Conference','Round','Game']] = pd.DataFrame(df[['level_0','level_1','level_2']].values.tolist(), index=df.index)
        return df[['Conference','Round','Game','Winner','Loser']]

class Simulations(object):
    def __init__(self, values, combine=True):
        self.combined = combine
        if combine:
            indices = list(range(len(values)))
            self.playoffs = pd.concat([x.playoffs for x in values], keys=indices).rename_axis(['Simulation','Row'])
            self.seeding = pd.concat([x.seeding for x in values], keys=indices).rename_axis(['Simulation','Row'])
            self.standings = pd.concat([x.standings for x in values], keys=indices).rename_axis(['Simulation','Row'])
            self.regularseason = pd.concat([x.regularseason for x in values], keys=indices).rename_axis(['Simulation','Row'])
        else:
            self.values = values
