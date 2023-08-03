#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug  2 22:53:21 2023

@author: gimli2
"""

from trueskill import Rating


class Player:
    def __init__(self, name='Nobody', rating=None):
        self.name = name
        self.rating = rating if rating is not None else Rating()
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
        self.history = []
        self.matches = []
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

    def count_avg_score(self, n=None):
        if n is None:
            return sum(map(lambda x: float(x.rating), self.players.values())) / len(self.players)
        else:
            return sum(map(lambda x: float(x.rating), self.get_players_top(n))) / n

    def __len__(self):
        return len(self.players)

    def __str__(self):
        return f'{self.name} ({", ".join(map(lambda x: str(x), self.players.values()))})'

    def __repr__(self):
        return self.__str__()

    @classmethod
    def get_dummy_players(cls, n: int = 5):
        return [Player(f'Dummy{i}') for i in range(n)]
