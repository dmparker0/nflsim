import numpy as np
import pandas as pd

#define resolution functions
def resolveWinPercentage(gamelog):
    grouped = gamelog.groupby(['Team']).agg({'Wins':'sum','Losses':'sum'}).reset_index()
    return resolveMaxWins(grouped, 'Wins', 'Losses')

def resolveScheduleStrength(gamelog):
    grouped = gamelog.drop_duplicates(['Team','Opponent Total Wins','Opponent Total Losses'])
    return resolveMaxWins(grouped, 'Opponent Total Wins', 'Opponent Total Losses')

def resolveMaxWins(df, wincol, losscol):
    percent = (df[wincol].values / (df[wincol].values + df[losscol].values)).round(10)
    ismax = (percent == percent.max())
    return df[ismax]['Team'].values

def resolveH2HSweep(gamelog):
    teams = set(gamelog['Team'].values)
    if len(teams) == 2:
        return resolveWinPercentage(gamelog)
    grouped = gamelog.groupby(['Team']).agg({'Wins':'sum','Losses':'sum'}).reset_index()
    undefeated = grouped['Wins'].values == (len(teams) - 1)
    if undefeated.sum() > 0:
        return grouped[undefeated]['Team'].values
    swept = grouped['Losses'].values == (len(teams) - 1)
    if swept.sum() > 0:
        return grouped[~swept]['Team'].values
    return list(teams)

def getCommonOpponents(gamelog, teams):
    teamgames = gamelog[gamelog['Team'].isin(teams)].groupby('Team')
    return set.intersection(*[set(g['Opponent'].values) for t, g in teamgames])

#define filters
def teamfilter(df, lst):
    return df['Team'].isin(lst)

def h2hfilter(df, lst):
    return teamfilter(df, lst) & df['Opponent'].isin(lst)

def sweepfilter(df, lst):
    n_groups = len(df[h2hfilter(df, lst)].groupby(['Team','Opponent']))
    return (n_groups == (len(lst) * (len(lst) - 1))) & h2hfilter(df, lst)

def divisionfilter(df, lst):
    return teamfilter(df, lst) & (df['Division'] == df['OppDivision'])

def cgfilter(df, lst, n):
    common = getCommonOpponents(df, lst)
    return teamfilter(df, lst) & (df['Opponent'].isin(common)) & (len(common) >= n)

def cgfilter_min1(df, lst):
    return cgfilter(df, lst, 1)

def cgfilter_min4(df, lst):
    return cgfilter(df, lst, 4)

def conferencefilter(df, lst):
    return teamfilter(df, lst) & (df['Conference'] == df['OppConference'])

def victoryfilter(df, lst):
    return teamfilter(df, lst) & (df['Wins'] == 1)

#define tiebreaker steps
divsteps = [{'Filter':h2hfilter, 'Resolution':resolveWinPercentage},
            {'Filter':divisionfilter, 'Resolution':resolveWinPercentage},
            {'Filter':cgfilter_min1, 'Resolution':resolveWinPercentage},
            {'Filter':conferencefilter, 'Resolution':resolveWinPercentage},
            {'Filter':victoryfilter, 'Resolution':resolveScheduleStrength},
            {'Filter':teamfilter, 'Resolution':resolveScheduleStrength}]

wcsteps  = [{'Filter':sweepfilter, 'Resolution':resolveH2HSweep},
            {'Filter':conferencefilter, 'Resolution':resolveWinPercentage},
            {'Filter':cgfilter_min4, 'Resolution':resolveWinPercentage},
            {'Filter':victoryfilter, 'Resolution':resolveScheduleStrength},
            {'Filter':teamfilter, 'Resolution':resolveScheduleStrength}]

def getPlayoffSeeding(gamelog):
    teamwins = gamelog.groupby(['Team','Division'])['Wins'].sum()
    topteams = teamwins[teamwins.groupby('Division').rank(method='min', ascending=False).values == 1]
    divwinners = set()
    for d, g in topteams.groupby('Division'):
        divwinners.add(breakDivisionalTie(gamelog, [{'Team':t,'Division':d} for t in g.index.get_level_values('Team').values]))
    remainingteams = set(gamelog['Team'].values) - divwinners
    return pd.DataFrame(getSeeds(gamelog, ([1,2,3,4], [5,6]), (divwinners, remainingteams)))

def getSeeds(gamelog, seed_groups, winner_groups):
    wins = gamelog.groupby(['Team','Conference','Division'])['Wins'].sum()
    seeding = []
    for conf, g in wins.groupby('Conference'):
        for sg, seed_group in enumerate(seed_groups):
            filtered = g[[x in winner_groups[sg] for x in g.index.get_level_values('Team').values]]
            c_rank = filtered.rank(method='min', ascending=False).values
            for s, seed in enumerate(seed_group):
                indices = [x for x in filtered[c_rank <= s + 1].index.values if x[0] not in [x['Team'] for x in seeding]]
                winner = breakWildCardTie(gamelog, [{'Team':t, 'Division':d} for t, c, d in indices])
                seeding.append({'Conference':conf,'Team':winner,'Seed':seed})
    return seeding

#breaks ties using divisional rules
def breakDivisionalTie(gamelog, tiedteams):
    if len(tiedteams) == 1:
        return tiedteams[0]['Team']
    return breakTies(gamelog, divsteps, tiedteams, breakDivisionalTie)
    
#breaks ties using wildcard rules
def breakWildCardTie(gamelog, tiedteams):
    divisions = set([team['Division'] for team in tiedteams])
    if len(divisions) == 1:
        return breakDivisionalTie(gamelog, tiedteams)
    currentteams = set()
    for division in divisions:
        currentteams.add(breakDivisionalTie(gamelog, [x for x in tiedteams if x['Division'] == division]))
    return breakTies(gamelog, wcsteps, [x for x in tiedteams if x['Team'] in currentteams], breakWildCardTie)

#breaks ties between 2 or more teams by applying an ordered list of filters/functions to a game log
def breakTies(gamelog, steps, tiedteams, caller):
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
