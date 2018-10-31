from .teams import Team, Teams
from scipy import stats
import pandas as pd
import numpy as np

#simulates games in a gamelog
def simulateGamelog(gamelog, rankings, home_adj, st_dev, tie_fraction=0.0):
    merged = pd.merge(gamelog, rankings.rename({'Team':'Home'}, axis=1), on='Home').rename({'PWR':'Home PWR'}, axis=1)
    merged = pd.merge(merged, rankings.rename({'Team':'Away'}, axis=1), on='Away').rename({'PWR':'Away PWR'}, axis=1)
    dist = stats.norm((merged['Home PWR'].values + home_adj) - merged['Away PWR'].values, st_dev)
    test_vals = 1 - dist.cdf(0.5)
    random_vals = np.random.random((3, merged.shape[0]))
    home_win = random_vals[0] < test_vals
    regulation_tie = np.logical_and(test_vals < random_vals[0], 1 - dist.cdf(-0.5) > random_vals[0])
    ot_result = np.where(random_vals[1] < tie_fraction, [0.5] * merged.shape[0], random_vals[2] < 1 - dist.cdf(0))
    merged['Home Wins'] = np.where(home_win, home_win, np.where(regulation_tie, ot_result, regulation_tie))
    merged['Away Wins'] = 1 - merged['Home Wins'].values
    return merged[['Home','Away','Home Wins','Away Wins']]

def simulateBracket(teams, home_adj, st_dev, n_winners=1, home_game_list=None):
    n_teams = teams.len()
    n_byes = (1<<(n_teams-1).bit_length()) - n_teams
    remaining = teams
    results = {}
    gameid = 1
    if n_byes > 0:
        non_byes = [x[0] for i, x in teams.copy().index(seed=True).items() if i > n_byes]
        results = simulateBracket(Teams(non_byes), home_adj, st_dev, (n_teams - n_byes)/2, home_game_list)
        losers = pd.DataFrame.from_dict(results, orient='index')['Loser'].values
        remaining = Teams([x[0] for i, x in remaining.copy().index(name=True).items() if i not in losers])
        gameid = len(results) + 1
    while True:
        remaining.index(seed=True)
        remaining_seeds = sorted(remaining.keys())
        winners = []
        for i in range(int(len(remaining_seeds) / 2)):
            home = remaining.values[remaining_seeds[i]][0]
            away = remaining.values[remaining_seeds[-i-1]][0]
            result = simulateGames(home, away, home_adj, st_dev, home_game_list)
            winners.append(result['Winner'])
            if home_game_list is None:
                results[gameid] = {'Winner':result['Winner'].name,'Loser':result['Loser'].name}
            else:
                results[gameid] = {'Winner':result['Winner'].name,'Loser':result['Loser'].name,'Games':result['Games']}
            gameid += 1
        if len(winners) == n_winners:
            return results
        else:
            remaining = Teams(winners)

def simulateGames(home, away, home_adj, st_dev, home_game_list):
    if home_game_list is None:
        return simulateGame(home, away, home_adj, st_dev)
    n_games = len(home_game_list)
    adj = np.where(home_game_list, home_adj, -1 * home_adj)
    home_pwr_difference = (home.pwr + adj) - ([away.pwr] * n_games)
    home_win_probability = 1 - stats.norm(home_pwr_difference, st_dev).cdf(0)
    is_home_winner = (np.random.random(n_games) < home_win_probability).astype(int)
    home_wins = 0
    away_wins = 0
    target_wins = (n_games + 1) / 2
    for i in range(n_games):
        home_wins += is_home_winner[i]
        away_wins += 1 - is_home_winner[i]
        if home_wins == target_wins:
            return {'Winner':home,'Loser':away,'Games':i + 1}
        elif away_wins == target_wins:
            return {'Winner':away,'Loser':home,'Games':i + 1}
            
def simulateGame(home, away, home_adj, st_dev):
    home_pwr_difference = (home.pwr + home_adj) - away.pwr
    home_win_probability = 1 - stats.norm(home_pwr_difference, st_dev).cdf(0)
    is_home_winner = np.random.random() < home_win_probability
    return {'Winner':home if is_home_winner else away,'Loser':away if is_home_winner else home}
