#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 26 13:42:41 2023

@author: gimli2

https://trueskill.org
"""

from utils.models import Player, Team
from utils.processing import preprocess_history, process_match

import re
import numpy as np
import pandas as pd
from pathlib import Path

from matplotlib import pyplot as plt
from matplotlib.ticker import (MultipleLocator)

CACHEFN = Path('data/sunset-vysledky.pkl')
SHEETID = "..."
url = f"https://docs.google.com/spreadsheets/d/{SHEETID}/export?format=csv&id={SHEETID}&gid=0"
print(url)


########################################################################################################################
# get historical data
df = preprocess_history(url, cache_fn=CACHEFN)

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
    if re.match('.*Paluf.*', row['Tournament'], re.IGNORECASE):
    # if not re.match('.*MCR.*', row['Tournament'], re.IGNORECASE) and not re.match('.*Kvalif.*', row['Tournament'], re.IGNORECASE):
        # print(i, row['Date'], row['Tournament'])
        teams, sunset = process_match(teams, sunset, i, row)  # lets count always from 0

# sunset players
print('-' * 80)
print('top sunset:')

fig = plt.figure(figsize=(30, 9))
ax = fig.add_subplot(111)

for p in sunset.get_players_top():
    print(p)
    x = p.matches
    if len(x) == 0:
        continue
    line = ax.plot(x, p.rating_history, label=p.name)
    c = line[0].get_c()
    ax.plot(x[-1], p.rating_history[-1], color=c, alpha=0.5, marker='o', markersize=2 * p.rating_history[-1].sigma)
    ax.annotate(f'{p.name} ({p.rating_history[-1].sigma:.1f})', xy=(x[-1], float(p.rating_history[-1]) + 0.2), color=c)


# ax.legend(bbox_to_anchor=(1.1, 1.05))
ticks = np.arange(0, len(match_names), 1)
# print(len(ticks), ticks)
ax.set_xticks(ticks)
ax.set_xticklabels(match_names, rotation=90)
ax.xaxis.set_major_locator(MultipleLocator(1))
ax.grid()
# ax.set_title('Sunset frisbee - TrueSkill score\n(no MCR, no kvalifikace)')
ax.set_title('Sunset frisbee - TrueSkill score\n(only PALUF)')
plt.savefig('sunset_trueskill_paluf-only.png', bbox_inches='tight')
# plt.savefig('sunset_trueskill_no(MCR,kval).png', bbox_inches='tight')
plt.show()

# team history stats
fig = plt.figure(figsize=(30, 9))
ax = fig.add_subplot(111)

for t in teams.values():
    # print(t.name, t.matches, t.history)
    x = t.matches
    if len(x) == 0:
        continue
    line = ax.plot(x, t.history, label=t.name, marker='o')
    c = line[0].get_c()
    ax.annotate(f'{t.name} ({t.history[-1]:.1f})', xy=(x[-1], float(t.history[-1]) + 0.05), color=c)

t = sunset
x = t.matches
c = '#000000'
line = ax.plot(x, t.history, label=t.name, marker='o', color=c, lw=3, alpha=0.75)
ax.annotate(f'{t.name} ({t.history[-1]:.1f})', xy=(x[-1], float(t.history[-1]) + 0.05), color=c)

# ax.legend(bbox_to_anchor=(1.1, 1.05))
ticks = np.arange(0, len(match_names), 1)
# print(len(ticks), ticks)
ax.set_xticks(ticks)
ax.set_xticklabels(match_names, rotation=90)
ax.xaxis.set_major_locator(MultipleLocator(1))
ax.grid()
ax.set_title('Sunset frisbee - TrueSkill score history')
# ax.set_title('Sunset frisbee - TrueSkill score\n(only PALUF)')
plt.savefig('sunset_history.png', bbox_inches='tight')
plt.show()
