from typing import List, Set, Dict, Tuple, Any, Optional, Callable
import numpy as np
import pandas as pd

#define resolution functions
def resolveWinPercentage(gamelog:pd.DataFrame) -> List[str]:
    grouped = gamelog.groupby(['Team']).agg({'Wins':'sum','Losses':'sum'}).reset_index()
    return resolveMaxWins(grouped, 'Wins', 'Losses')

def resolveScheduleStrength(gamelog:pd.DataFrame) -> List[str]:
    grouped = gamelog.groupby(['Team','Opponent Total Wins','Opponent Total Losses']).first().reset_index()
    return resolveMaxWins(grouped, 'Opponent Total Wins', 'Opponent Total Losses')

def resolveMaxWins(df:pd.DataFrame, wincol:str, losscol:str) -> List[str]:
    percent = (df[wincol].values / (df[wincol].values + df[losscol].values)).round(10)
    ismax = (percent == percent.max())
    return df[ismax]['Team'].tolist()

def resolveH2HSweep(gamelog:pd.DataFrame) -> List[str]:
    teams = list(set(gamelog['Team'].values))
    if len(teams) == 2:
        return resolveWinPercentage(gamelog)
    grouped = gamelog.groupby(['Team']).agg({'Wins':'sum','Losses':'sum'}).reset_index()
    undefeated = grouped['Wins'].values == (len(teams) - 1)
    swept = grouped['Losses'].values == (len(teams) - 1)
    if undefeated.sum() > 0:
        return grouped[undefeated]['Team'].tolist()
    elif swept.sum() > 0:
        return grouped[~swept]['Team'].tolist()
    else:
        return teams

def getCommonOpponents(gamelog:pd.DataFrame, teams:List[str]) -> List[str]:
    teamgames = gamelog[gamelog['Team'].isin(teams)]
    opplists = teamgames.groupby('Team')['Opponent'].apply(list).reset_index()
    opponents = opplists['Opponent'].values
    if len(opponents) > 0:
        return list(set.intersection(*[set(lst) for lst in opponents]))
    else:
        return []

#define filters
def teamfilter(df:pd.DataFrame, lst:List[str]) -> pd.Series:
    return (df['Team'].isin(lst))

def h2hfilter(df:pd.DataFrame, lst:List[str]) -> pd.Series:
    return teamfilter(df, lst) & (df['Opponent'].isin(lst))

def sweepfilter(df:pd.DataFrame, lst:List[str]) -> pd.Series:
    grouped = df[h2hfilter(df, lst)].groupby(['Team','Opponent'])
    return (len(grouped) == (len(lst) * (len(lst) -1))) & h2hfilter(df, lst)

def divisionfilter(df:pd.DataFrame, lst:List[str]) -> pd.Series:
    return teamfilter(df, lst) & (df['Division'] == df['OppDivision'])

def cgfilter(df:pd.DataFrame, lst:List[str], n:int) -> pd.Series:
    common = getCommonOpponents(df, lst)
    return teamfilter(df, lst) & (df['Opponent'].isin(common)) & (len(common) >= n)

def cgfilter_min1(df:pd.DataFrame, lst:List[str]) -> pd.Series:
    return cgfilter(df, lst, 1)

def cgfilter_min4(df:pd.DataFrame, lst:List[str]) -> pd.Series:
    return cgfilter(df, lst, 4)

def conferencefilter(df:pd.DataFrame, lst:List[str]) -> pd.Series:
    return teamfilter(df, lst) & (df['Conference'] == df['OppConference'])

def victoryfilter(df:pd.DataFrame, lst:List[str]) -> pd.Series:
    return teamfilter(df, lst) & (df['Wins'] == 1)

#define tiebreaker steps
divsteps:List[Tuple[Callable[[pd.DataFrame,List[str]],pd.Series],Callable[[pd.DataFrame],List[str]]]]
wcsteps:List[Tuple[Callable[[pd.DataFrame,List[str]],pd.Series],Callable[[pd.DataFrame],List[str]]]]
divsteps = [(h2hfilter, resolveWinPercentage), 
            (divisionfilter, resolveWinPercentage), 
            (cgfilter_min1, resolveWinPercentage), 
            (conferencefilter, resolveWinPercentage), 
            (victoryfilter, resolveScheduleStrength), 
            (teamfilter, resolveScheduleStrength)]
wcsteps =  [(sweepfilter, resolveH2HSweep), 
            (conferencefilter, resolveWinPercentage), 
            (cgfilter_min4, resolveWinPercentage), 
            (victoryfilter, resolveScheduleStrength), 
            (teamfilter, resolveScheduleStrength)]
            
#returns playoff teams + seeds
def getPlayoffSeeding(gamelog:pd.DataFrame) -> pd.DataFrame:
    divwinners = getDivisionWinners(gamelog)
    wildcards = getWildCards(gamelog, divwinners)
    return pd.DataFrame(divwinners + wildcards) 

#applies tiebreaker rules to determine division winners and set 1-4 seeds for each conference
def getDivisionWinners(gamelog:pd.DataFrame) -> List[Dict[str, str]]:
    teamwins = gamelog.groupby(['Team','Division'])['Wins'].sum()
    topteams = teamwins[teamwins.groupby('Division').rank(method='min', ascending=False).values == 1]
    winners = []
    for d, g in topteams.groupby('Division'):
        winners.append(breakDivisionalTie(gamelog, [{'Team':t,'Division':d} for t in g.index.get_level_values('Team').values]))
    return getSeeds(gamelog, [1,2,3,4], winners)

#applies tiebreaker rules to determine wildcards and set 5-6 seeds for each conference
def getWildCards(gamelog:pd.DataFrame, divisionwinners:List[Dict[str, str]]) -> List[Dict[str, str]]:
    return getSeeds(gamelog, [5,6], list(set(gamelog['Team'].values) - set([x['Team'] for x in divisionwinners])))

#applies tiebreaker rules to determine seeding of a group of teams
#division winners and wildcards are processed separately (division winners go first)
def getSeeds(gamelog:pd.DataFrame, seeds:List[int], teams:List[str]) -> List[Dict[str, Any]]:
    teamwins = gamelog.groupby(['Team','Conference','Division'])['Wins'].sum()
    seeding = []
    for conf, g in teamwins[np.isin(teamwins.index.get_level_values('Team').values, teams)].groupby('Conference'):
        winners:Set[str] = set()
        c_rank = g.rank(method='min', ascending=False).values
        for i, seed in enumerate(seeds):
            indices = [{'Team':t, 'Division':d} for t, c, d in g[c_rank <= i + 1].index.tolist() if t not in winners]
            winner = breakWildCardTie(gamelog, indices)
            winners.add(winner)
            seeding.append({'Conference':conf,'Team':winner,'Seed':seed})
    return seeding

#breaks ties using divisional rules
def breakDivisionalTie(gamelog:pd.DataFrame, tiedteams:List[Dict[str, str]]) -> str:
    if len(tiedteams) == 1:
        return tiedteams[0]['Team']
    steps = [{'Filter':x[0], 'Resolution':x[1]} for x in divsteps]
    return breakTies(gamelog, steps, tiedteams, breakDivisionalTie)
    
#breaks ties using wildcard rules
def breakWildCardTie(gamelog:pd.DataFrame, tiedteams:List[Dict[str, str]]) -> str:
    divisions = set([team['Division'] for team in tiedteams])
    if len(divisions) == 1:
        return breakDivisionalTie(gamelog, tiedteams)
    currentteams = set()
    for division in divisions:
        currentteams.add(breakDivisionalTie(gamelog, [x for x in tiedteams if x['Division'] == division]))
    steps = [{'Filter':x[0], 'Resolution':x[1]} for x in wcsteps]
    return breakTies(gamelog, steps, [x for x in tiedteams if x['Team'] in currentteams], breakWildCardTie)

#breaks ties between 2 or more teams by applying an ordered list of filters/functions to a game log
def breakTies(gamelog:pd.DataFrame, steps:List[Dict[str, Any]], tiedteams:List[Dict[str, str]], 
              caller:Callable[[pd.DataFrame, List[Dict[str, str]]], str]) -> str:
    remainder = [x['Team'] for x in tiedteams]
    for step in steps:
        filtered = gamelog[step['Filter'](gamelog, remainder)]
        if not filtered.empty:
            remainder = step['Resolution'](filtered)
        if len(remainder) == 1:
            return remainder[0]
        elif len(remainder) == 2 and len(tiedteams) != 2:
            return caller(gamelog, [x for x in tiedteams if x['Team'] in remainder])
    return np.random.choice(remainder)