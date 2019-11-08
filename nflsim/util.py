abbreviations = {
    'ARI':'Arizona Cardinals','ATL':'Atlanta Falcons','BAL':'Baltimore Ravens',
    'BUF':'Buffalo Bills','CAR':'Carolina Panthers','CHI':'Chicago Bears',
    'CIN':'Cincinnati Bengals','CLE':'Cleveland Browns','DAL':'Dallas Cowboys',
    'DEN':'Denver Broncos','DET':'Detroit Lions','GB' :'Green Bay Packers',
    'HOU':'Houston Texans','IND':'Indianapolis Colts','JAC':'Jacksonville Jaguars',
    'KC' :'Kansas City Chiefs','LAC':'Los Angeles Chargers','LAR':'Los Angeles Rams',
    'MIA':'Miami Dolphins','MIN':'Minnesota Vikings','NE' :'New England Patriots',
    'NO' :'New Orleans Saints','NYG':'New York Giants','NYJ':'New York Jets',
    'OAK':'Oakland Raiders','PHI':'Philadelphia Eagles','PIT':'Pittsburgh Steelers',
    'SEA':'Seattle Seahawks','SF' :'San Francisco 49ers','TB' :'Tampa Bay Buccaneers',
    'TEN':'Tennessee Titans','WAS':'Washington Redskins','JAX':'Jacksonville Jaguars',
    'LARM':'Los Angeles Rams','LACH':'Los Angeles Chargers','SD':'San Diego Chargers',
    'STL':'St. Louis Rams'}
    
playoff_game_ids = {
    ('AFC', 1):('AFC','Wild Card',1),('AFC', 2):('AFC','Wild Card',2),
    ('AFC', 3):('AFC','Divisional',1),('AFC', 4):('AFC','Divisional',2),
    ('NFC', 1):('NFC','Wild Card',1),('NFC', 2):('NFC','Wild Card',2),
    ('NFC', 3):('NFC','Divisional',1),('NFC', 4):('NFC','Divisional',2),
    ('AFC', 5):('AFC','Championship',1),('NFC', 5):('NFC','Championship',1)}

def extractText(tosearch, delim_left='', delim_right= None,
                reverse_left=False, reverse_right=False,
                optional_left=False, optional_right=False):
    rdelim = delim_left if delim_right is None else delim_right
    returnval = tosearch
    if delim_left != '':
        returnval = extractHelper(returnval, delim_left, reverse_left, optional_left, True)
    if rdelim != '':
        returnval = extractHelper(returnval, rdelim, reverse_right, optional_right, False)
    return returnval

def extractHelper(tosearch, delim, reverse_order, is_optional, is_left):
    cond1 = (is_left == (is_optional == reverse_order))
    cond2 = (not reverse_order) and is_left
    n = 2 if is_left else 0
    basefunc = str.rpartition if reverse_order else str.partition
    partitioned = basefunc(tosearch, delim)
    return partitioned[n] if (cond1 or partitioned[1] == delim) else partitioned[0] if cond2 else ''
