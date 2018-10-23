# nflsim

This package simulates the NFL regular season and playoffs using a simple, customizable Monte Carlo method.

### How it works

During each simulation, nflsim uses the methods described below to assign a winner to all remaining NFL games in a given season. It then uses the NFL's complex [tiebreaking procedures] to determine playoff seeding, and the playoffs are simulated game-by-game.

Before beginning the simulations, each team is assigned a power rating (PWR) with mean 0, such that a team with a PWR of 3 would be favored by 5 points vs a team with a PWR of -2 on a neutral field. By default, the base power rankings for each team are calculated using an equally-weighted combination of normalized versions of the SRS, FPI, DVOA, and Sagarin rankings. The rankings systems used and their relative weights are configurable, and custom ranking systems are supported. The individual rating systems and the combined rankings can be regressed to the mean (or to custom team-specific values) as desired.

The team PWR rankings are adjusted at the beginning of each season simulation by a random amount, determined using a normal distribution with mean 0 and a user-provided standard deviation (2 points by default):
```
adjusted_pwr = [PWR] - numpy.random.normal(0, [rank_adj])
```
    
This adjustment represents the uncertainty in each team's base PWR projection, which includes both model error and injury risk. Higher values equate to more variance in outcomes.

When simulating a game, the home team's PWR is adjusted upwards by a fixed amount and compared to the away team's PWR. The resulting point differential is used to generate a normal cumulative distribution function, which determines the home team's probability of winning the game. This win probability is compared to a random number to determine the simulated winner of the game:
```
home_pwr_difference = ([Home PWR] + [Home Adj]) - [Away PWR]
home_win_probability = 1 - scipy.stats.norm(home_pwr_difference, [stdev]).cdf(0)
is_home_winner = numpy.random.random() < home_win_probability
```

Both the home adjustment ([3 points by default]) and the standard deviation used to generate the normal distribution ([13 points by default]) are configurable.

### Usage

##### Basics

Each simulation is controlled by a Sim object. You create an object by specifying the season to simulate and the number of simulations:
```python
import nflsim
simulation = nflsim.Sim(season=2018, n_sims=10000)
```
    
If desired, you can customize the values for home-field advantage, the PWR rank adjustment used at the beginning of each simulation, and the standard deviation used when simulating individual games:
```python
simulation = nflsim.Sim(season=2018, n_sims=10000, rank_adj=3, home_adj=2.5, st_dev=13.5)
```    
##### PWRsystems
    
You can customize how the power rankings are generated by creating a PWRsystems object. You create an object by indicating which systems to include:
```python
systems = nflsim.PWRsystems(dvoa=True, fpi=True, sagarin=True)
simulation = nflsim.Sim(season=2018, n_sims=10000, pwr_systems=systems)
```

The weights for each system (default = 1) can be specified using the built-in objects for each system (SRS, DVOA, FPI, and Sagarin):
```python
systems = nflsim.PWRsystems(srs=True, dvoa=nflsim.DVOA(weight=2), fpi=nflsim.FPI(weight=1.5))
```

You can also incorporate your own rating system by creating a generic PWR object and passing it a pandas DataFrame containing the custom rankings. The DataFrame must include one column called 'Team' containing the full team names and another column containing the team rankings. The name of the ranking column should be unique from those of the other systems being used (so don't use "FPI" or "SRS"):
```python
my_sys_df = pandas.DataFrame([{'Team':'A','Power':-2},{'Team':'B','Power':5}])
my_sys = nflsim.PWR(weight=2, values=my_sys_df)
systems = nflsim.PWRsystems(srs=True, others=my_sys)
```

To use multiple custom systems, pass a list of DataFrames instead of a single DataFrame:
```python
df1 = pandas.DataFrame([{'Team':'A','Power':-2},{'Team':'B','Power':5}])
df2 = pandas.DataFrame([{'Team':'A','Power':0},{'Team':'B','Power':2}])
my_sys_1 = nflsim.PWR(weight=2, values=df1)
my_sys_2 = nflsim.PWR(weight=1.5, values=df2)
systems = nflsim.PWRsystems(srs=True, others=[my_sys_1, my_sys_2])
```

##### Regression

Optionally, you can choose to regress the ratings generated by each system by creating a Regression object (if regress_to is omitted, no regression will be used). By default, PWR values will be regressed to the sample mean:
```python
my_sys = nflsim.SRS(weight=2, regress_to=nflsim.Regression())
```

You can use fixed weighting by specifying a decimal between 0 and 1, or variable weighting based on the percentage of a specified number of games played (the default option):
```python
#(PWR * 0.75) + (sample_mean * 0.25)
regression_fixed = nflsim.Regression(weight=0.25)
#((PWR * games_played) + (sample_mean * max(0, 10 - games_played))) / max(10, games_played)
regression_variable = nflsim.Regression(n_games=10)
```
    
You can regress PWR to a fixed value rather than using the sample mean:
```python
regression = nflsim.Regression(to=0, weight=0.5)
```
    
You can also specify a custom regression value for each team using a pandas DataFrame. The DataFrame must contain one column called 'Team' containing the full team names and another called 'Baseline' for the regression values:
```python
df = pd.DataFrame([{'Team':'A','Baseline':-2},{'Team':'B','Baseline':5}])
regression = nflsim.Regression(to=df, n_games=16)
```
    
In addition to (or instead of) regressing the values for individual PWR systems, you can choose to regress the final results after combining the various systems:
```python
regression = nflsim.Regression(n_games=10)
systems = nflsim.PWRsystems(regress_to=regression, srs=True, dvoa=nflsim.DVOA(weight=2))
```

##### Execution and Analysis

Once you've set up your Sim object, use run() to execute the simulation.
```python
regression = nflsim.Regression(n_games=10)
systems = nflsim.PWRsystems(srs=nflsim.SRS(regress_to=regression), fpi=True, dvoa=nflsim.DVOA(weight=2))
simulation = nflsim.Sim(season=2018, n_sims=10000, pwr_systems=systems)
simulation.run()
```
    
The run() method will return a reference to the Sim object, so this syntax is also acceptable:
```python
simulation = nflsim.Sim(season=2018, n_sims=10000, pwr_systems=systems).run()
```
    
Once the simulation has been executed, you can view the detailed results by iterating through a list of Simulation objects. Each Simulation object contains a number of separate DataFrames containing data from the simulation in question:
```python
for sim in simulation.simulations.values:
    standings = sim.standings
    adjusted_pwr = sim.rankings
    regularseason = sim.regularseason
    seeding = sim.seeding
    playoffs = sim.playoffs
```
    
Some results are aggregated by default, and can be accessed directly from the Sim object. You can view the aggregated playoff results (contains seed information + playoff winners) as a DataFrame using the "playoffs" property:
```python
playoff_df = simulation.playoffs
```

You can also view the aggregated season data (contains average wins + PWR for each team) as a DataFrame using the "standings" property:
```python
standings_df = simulation.standings
```
    
By default, run() will use the joblib package to run the simulations in parallel; this can be overridden by setting parallel=False:
```python
simulation = nflsim.Sim(season=2018, n_sims=100).run(parallel=False)
```
    
If you prefer to generate your own aggregate statistics, you can disable the automatic generation of the aggregated "playoffs" and "standings" properties by setting combine=False:
```python
simulation = nflsim.Sim(season=2018, n_sims=100000).run(combine=False)
```

[//]: #
   [tiebreaking procedures]: <https://operations.nfl.com/the-rules/nfl-tiebreaking-procedures/>
   [3 points by default]: <http://www.espn.com/nfl/story/_/id/20371914/home-field-advantage-nfl-2017-toughest-easiest-teams-play-road-more>
   [13 points by default]: <https://www.pro-football-reference.com/about/win_prob.htm>
