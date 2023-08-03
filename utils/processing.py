#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug  2 23:28:22 2023

@author: gimli2
"""
import re
import pandas as pd
from datetime import datetime
from pathlib import Path
from trueskill import rate
from utils.models import Team


def get_ratings(players: list):
    return [p.rating for p in players]


def sanitize_name(s):
    while len(s) > 0 and ord(s[-1]) > 2000:
        s = s[:-1]
    return s


def preprocess_history(url: str, cache=True, cache_fn=Path('data/data.pkl')):
    before_hour = datetime.now().timestamp() - 3600
    if cache and cache_fn.exists() and cache_fn.stat().st_mtime > before_hour:
        print('Using cached file')
        df = pd.read_pickle(cache_fn)
    else:
        print('Fetching new copy of source data')
        df = pd.read_csv(url, header=0, index_col=False)
        df.to_pickle(cache_fn)

    df.rename(columns={
        'Datum': 'Date',
        'Turnaj': 'Tournament',
    }, inplace=True)

    # sanitize emojis from names
    orig_pl_names = df.columns[10:]
    clear_names = [sanitize_name(n).strip() for n in orig_pl_names]
    rename_dict = {k: v for k, v in zip(orig_pl_names, clear_names)}
    df.rename(columns=rename_dict, inplace=True)

    df.drop(index=0, inplace=True)  # skip summary line
    df.dropna(subset=['Date'], inplace=True)  # skip empty lines
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

    sunset.matches.append(matchid)
    sunset.history.append(sunset.count_avg_score())
    oponent.matches.append(matchid)
    oponent.history.append(oponent.count_avg_score(7))

    # print(sunset)
    # print(oponent)

    return teams, sunset


def regex_filter(val, regex, negative=False):
    # print(val, regex, negative)
    if val:
        if re.match(regex, val, re.IGNORECASE):
            return False if negative else True
        else:
            return True if negative else False
    else:
        return False
