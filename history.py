#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 26 13:42:41 2023

@author: gimli2

https://trueskill.org
"""

import re
import numpy as np
import pandas as pd
from pathlib import Path
from trueskill import Rating, rate
from matplotlib import pyplot as plt
from matplotlib.ticker import (MultipleLocator)

CACHE = True
CACHEFN = Path('sunset-vysledky.pkl')
SHEETID = "..."
SHEETNAME = "Sheet1"
url = f"https://docs.google.com/spreadsheets/d/{SHEETID}/export?format=csv&id={SHEETID}&gid=0"
print(url)


class Player:
    def __init__(self, name='Nobody', rating=Rating()):
        self.name = name
        self.rating = rating
        self.rating_history = []
        self.matches = []

    def update_rating(self, newr: Rating):
        self.rating_history.append(self.rating)
        self.rating = newr

    def add_match(self, idx):
        self.matches.append(idx)

    def __str__(self):
        return f'{self.name} (r={float(self.rating):.1f})'

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.rating == other.rating

    def __lt__(self, other):
        return self.rating < other.rating


class Team:
    def __init__(self, name='Team', players: dict = None, min_players=0):
        self.name = name
        if players is None:
            if min_players == 0:
                self.players = dict()
            else:
                players = Team.get_dummy_players(min_players)
                names = [p.name for p in players]
                self.players = {n: p for n, p in zip(names, players)}
        else:
            self.players = players

    def add_player(self, p):
        if isinstance(p, Player):
            self.players[p.name] = p

    def get_players(self, n):
        return list(self.players.values())[0: n]

    def get_players_by_name(self, names: list):
        return [p for p in self.players.values() if p.name in set(names)]

    def get_players_top(self, n: int = None):
        if n is None or n >= len(self.players):
            n = len(self.players)

        p = list(self.players.values())
        p.sort(reverse=True)
        return p[0:n]

    def __len__(self):
        return len(self.players)

    def __str__(self):
        return f'{self.name} ({", ".join(map(lambda x: str(x), self.players.values()))})'

    def __repr__(self):
        return self.__str__()

    @classmethod
    def get_dummy_players(cls, n: int = 5):
        return [Player(f'Dummy{i}') for i in range(n)]


def get_ratings(players: list):
    return [p.rating for p in players]


def sanitize_name(s):
    while len(s) > 0 and ord(s[-1]) > 2000:
        s = s[:-1]
    return s


def preprocess_history():
    if CACHE and CACHEFN.exists():
        print('Using cached file')
        df = pd.read_pickle(CACHEFN)
    else:
        df = pd.read_csv(url, header=0, index_col=False)
        df.to_pickle(CACHEFN)

    df.rename(columns={
        '113': 'Date',
        'Unnamed: 1': 'Tournament',
        'Unnamed: 2': 'Oponent',
    }, inplace=True)
    # sanitize emojis from names
    orig_pl_names = df.columns[10:]
    clear_names = [sanitize_name(n).strip() for n in orig_pl_names]
    rename_dict = {k: v for k, v in zip(orig_pl_names, clear_names)}
    df.rename(columns=rename_dict, inplace=True)

    df.dropna(subset=['Date'], inplace=True)  # skip empty lines
    df.drop(index=0, inplace=True)  # skip summary line
    df['Date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y')  # make date as datetime
    return df


def process_match(teams: dict, sunset: Team, matchid, match: pd.Series):
    # print(match)
    # who played as sunset
    played_idxs = match[10:].notna().to_numpy()
    # no evidence of players
    if not played_idxs.any():
        return teams, sunset
    played_names = set(match.keys()[10:][played_idxs].values)
    # take oponent
    oponent = teams[match.Oponent]
    # t_opo = oponent.get_players(len(played_names))  # take first N players
    t_opo = oponent.get_players_top(len(played_names))  # teke N best players
    t_sun = sunset.get_players_by_name(played_names)
    t_opo_r = get_ratings(t_opo)
    t_sun_r = get_ratings(t_sun)
    # t_sun_r = [Rating(r.mu * 1.0, r.sigma * 1.02) for r in t_sun_r]  # increase a sigma when there is uncertainty about player skills
    # take results
    bs = int(match[0:10].fillna(0)['Body Sunset'])
    bo = int(match[0:10].fillna(0)['Body Oponent'])
    # ranks = lower is better
    if bs > bo:
        ranks = [0, 1]
    elif bs < bo:
        ranks = [1, 0]
    else:
        ranks = [0, 0]
    # recalculate trueskill ratings
    sun_new_r, opo_new_r = rate([t_sun_r, t_opo_r], ranks=ranks)
    # update players rating
    for i, p in enumerate(t_sun):
        sunset.players[p.name].update_rating(sun_new_r[i])
        sunset.players[p.name].add_match(matchid)
    for i, p in enumerate(t_opo):
        oponent.players[p.name].rating = opo_new_r[i]  # no care about rating history

    # print(sunset)
    # print(oponent)

    return teams, sunset


########################################################################################################################
# get historical data
df = preprocess_history()

# create sunset from names starting at column 11
sunset = Team(name='Sunset')
for p in df.columns[10:]:
    sunset.add_player(Player(p))

# create oponent teams
teams = dict()
team_names = sorted(list(set(df.Oponent.to_list())))
for tn in team_names:
    teams[tn] = Team(name=tn, min_players=len(sunset))

# iterate over matches
match_names = []
df.sort_values(by=['Date'], inplace=True)
df = df.reset_index()
for i, row in df.iterrows():
    match_names.append(f"{row['Tournament']} ({row['Oponent']})")
    # if not re.match('.*MCR.*', row['Tournament'], re.IGNORECASE) and not re.match('.*Kvalif.*', row['Tournament'], re.IGNORECASE):
    if re.match('.*Paluf.*', row['Tournament'], re.IGNORECASE):
        print(i, row['Date'], row['Tournament'])
        teams, sunset = process_match(teams, sunset, i - 1, row)  # lets count always from 0


print('-' * 80)
print('top sunset:')

fig = plt.figure(figsize=(30, 9))
ax = fig.add_subplot(111)

for p in sunset.get_players_top():
    print(p)
    x = p.matches
    if len(x) == 0:
        continue
    ax.plot(x, p.rating_history, label=p.name)
    ax.annotate(p.name, xy=(x[-1], p.rating_history[-1]))


# ax.legend(bbox_to_anchor=(1.1, 1.05))
ticks = np.arange(0, len(match_names), 1)
# print(len(ticks), ticks)
ax.set_xticks(ticks)
ax.set_xticklabels(match_names, rotation=90)
ax.xaxis.set_major_locator(MultipleLocator(1))
ax.grid()
# ax.set_title('Sunset frisbee - TrueSkill score\n(no MCR, no kvalifikace)')
ax.set_title('Sunset frisbee - TrueSkill score\n(only PALUF)')
plt.savefig('sunset_trueskill_only(paluf).png', bbox_inches='tight')
plt.show()
