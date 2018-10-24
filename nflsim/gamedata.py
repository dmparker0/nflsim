from bs4 import BeautifulSoup
from requests import get
import numpy as np
import pandas as pd

#gets list of each team + their conference/division for a given nfl season
def getTeams(year):
    url = 'https://www.pro-football-reference.com/years/' + str(year) + '/'
    html = BeautifulSoup(get(url).text, features='lxml')
    afcteams = parseStandings(html.select('table[id=AFC] > tbody > tr'), 'AFC')
    nfcteams = parseStandings(html.select('table[id=NFC] > tbody > tr'), 'NFC')
    return pd.DataFrame(afcteams + nfcteams)

#determines division of each team in a conference standings table
def parseStandings(rows, conference):
    teams = []
    division = ''
    for row in rows:
        if 'class' in row.attrs:
            division = row.text.strip()
        else:
            teams.append({'Team':row.select('a')[0].text,'Conference':conference,'Division':division})
    return teams

#returns the nfl game log for a given season
def getScores(year):
    url = 'https://www.pro-football-reference.com/years/' + str(year) + '/games.htm'
    df = pd.read_html(str(BeautifulSoup(get(url).text, features='lxml').select('table[id=games]')))[0]
    df.columns = ['Week','Day','Date','Time','Winner','At','Loser','Box','PtsW','PtsL','Del','Del','Del','Del']
    df = df[df['Date'] != 'Playoffs']
    df = df[df['Week'].apply(lambda x: x.isnumeric())]
    df = df[[x for x in list(df) if x not in ['Box','Del','Week','Day','Date','Time']]]
    ishome = (df['At'].values != '@')
    df['Home'] = np.where(ishome, df['Winner'].values, df['Loser'].values)
    df['Away'] = np.where(ishome, df['Loser'].values, df['Winner'].values)
    df['Played'] = df['PtsW'].notnull()
    df['HomePts'] = np.nan_to_num(np.where(ishome, df['PtsW'].values, df['PtsL'].values).astype(float)).astype(int)
    df['AwayPts'] = np.nan_to_num(np.where(ishome, df['PtsL'].values, df['PtsW'].values).astype(float)).astype(int)
    return df[['Home','Away','HomePts','AwayPts','Played']]

#cleans game log + mirrors stats for each game so that each appears twice
#game will appear once with team A as 'Team' and team B as 'Opponent' + once vice versa
def adjustScores(gamelog, home_adj):
    df = pd.DataFrame([x + [True]  for x in gamelog[['Home','Away','HomePts','AwayPts']].values.tolist()] +
                      [x + [False] for x in gamelog[['Away','Home','AwayPts','HomePts']].values.tolist()], 
                      columns= ['Team','Opponent','Points','OppPoints','IsHome'])
    difference = df['Points'].values - df['OppPoints'].values
    wins = (np.sign(difference) + 1) / 2
    df['Difference'] = difference - np.where(df['IsHome'].values, home_adj, -1 * home_adj)
    df['Wins'] = wins
    df['Losses'] = 1 - wins
    teamwins = df.groupby(['Team']).agg({'Wins':'sum','Losses':'sum'}).reset_index()
    teamwins = teamwins.rename(columns={'Wins':'Total Wins','Losses':'Total Losses'})
    oppwins = teamwins.rename(columns={'Team':'Opponent', 'Total Wins':'Opponent Total Wins', 'Total Losses':'Opponent Total Losses'})
    merged = pd.merge(pd.merge(df, teamwins, on='Team'), oppwins, on='Opponent')
    merged['Games Played'] = merged['Total Wins'] + merged['Total Losses']
    return merged
