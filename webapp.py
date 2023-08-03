#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug  2 23:17:18 2023

@author: gimli2
"""

import re
import streamlit as st
import trueskill
import pandas as pd
from pathlib import Path
from datetime import datetime
from utils.models import Player, Team
from utils.processing import preprocess_history, process_match, regex_filter


CACHEFN = Path('data/sunset-vysledky.pkl')
SHEETID = "..."
url = f"https://docs.google.com/spreadsheets/d/{SHEETID}/export?format=csv&id={SHEETID}&gid=0"

st.set_page_config(
    page_title="Sunset Trueskill playground",
    page_icon=":flying_disc:",
)

# get historical data
df = preprocess_history(url, cache_fn=CACHEFN)

st.sidebar.markdown("<p style='text-align: center;'><img src='https://www.sunsetfrisbee.cz/img/logo.jpg'</p>", unsafe_allow_html=True)
st.sidebar.title('Trueskill playground')
st.sidebar.write("Based on data from Libor's table no older than 1 hour.")

st.sidebar.subheader('Rating distribution params')
mu = st.sidebar.slider('mu', 0, 50, 25)
sigma = st.sidebar.slider('sigma', 1.0, 20.0, 8.33)
trueskill.setup(mu=mu, sigma=sigma)

st.sidebar.subheader('History range')
hr = st.sidebar.slider(
    "Select interval",
    value=(df['Date'].iloc[-1].to_pydatetime(), df['Date'].iloc[0].to_pydatetime()),
    format="YYYY-MM-DD")

st.sidebar.subheader('Tournaments filter')
rein = st.sidebar.text_input('Regexp include', '.*')
reout = st.sidebar.text_input('Regexp exclude', '')


st.header("Results from Libor's table")
st.write("History range:", hr[0], hr[1])
df = df[(df['Date'] >= hr[0]) & (df['Date'] <= hr[1])]
st.write("Matches within the given range:", len(df))
st.text(f"Tournament name regexp include: {rein} AND exclude: {reout}")
if rein != '':
    df = df[df['Tournament'].apply(regex_filter, regex=rein, negative=False)]
if reout != '':
    df = df[df['Tournament'].apply(regex_filter, regex=reout, negative=True)]

st.write("Matches after tournaments name constraints applied:", len(df))

st.write(df)

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
    if re.match(rein, row['Tournament'], re.IGNORECASE):
        if reout == '':
            teams, sunset = process_match(teams, sunset, i, row)  # lets count always from 0
        else:
            if not re.match(reout, row['Tournament'], re.IGNORECASE):
                teams, sunset = process_match(teams, sunset, i, row)  # lets count always from 0


st.header("Sunset ranking")
st.write("You can sort column by clicking its header.")
sunset_tp = sunset.get_players_top()
stpdf = pd.DataFrame(
    {
        "rank": [x for x in range(1, len(sunset_tp) + 1)],
        "name": [p.name for p in sunset_tp],
        "mu": [p.rating.mu for p in sunset_tp],
        "sigma": [p.rating.sigma for p in sunset_tp],
        "matches": [len(p.rating_history) for p in sunset_tp],
        "rank_history_mu": [[r.mu for r in p.rating_history] for p in sunset_tp],
        # "rank_history_s": [[r.sigma for r in p.rating_history] for p in sunset_tp],
    }
)
st.dataframe(
    stpdf,
    column_config={
        "rank": "Rank",
        "name": "Player",
        "mu": "TS mu",
        "sigma": "TS sigma",
        "matches": "Matches",
        "rank_history_mu": st.column_config.BarChartColumn("TS - mu history", y_min=trueskill.MU, y_max=40),
        # "rank_history_s": st.column_config.BarChartColumn("TS - sigma history", y_min=trueskill.SIGMA, y_max=10),
    },
    use_container_width=True,
    hide_index=True,
)
top7 = stpdf.loc[0:7, ('mu', 'sigma')].mean()
top10 = stpdf.loc[0:10, ('mu', 'sigma')].mean()
topall = stpdf.loc[:, ('mu', 'sigma')].mean()
st.subheader('Skill of top N Sunset players')
st.write(pd.concat([top7, top10, topall], keys=['Top 7', 'Top 10', 'all'], axis=1))

st.header("Opponents teams")
opdf = pd.DataFrame(
    {
        "rank": [x for x in range(1, len(teams) + 1)],
        "name": [t.name for t in teams.values()],
        "skill": [t.count_avg_score() for t in teams.values()],
        "skill7": [t.count_avg_score(7) for t in teams.values()],
        "matches": [len(t.matches) for t in teams.values()],
        "skill_history_mu": [t.history for t in teams.values()],
    }
)
st.dataframe(
    opdf,
    column_config={
        "rank": "Rank",
        "name": "Team",
        "skill": "TS all",
        "skill7": "TS Top 7",
        "matches": "Matches with Sunset",
        "skill_history_mu": st.column_config.BarChartColumn("TS all - mu history", y_min=trueskill.MU, y_max=40),
    },
    use_container_width=True,
    hide_index=True,
)

