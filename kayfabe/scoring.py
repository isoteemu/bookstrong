#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from kayfabe.models import *
from . import session

from sqlalchemy import asc, desc, func

from datetime import date
from collections import Sequence

RANK_TIME = 3

class Ranking(Sequence):

    to_date         = date.today()
    time_range      = RANK_TIME
    limit           = 400

    rank            = None
    prev_rank       = None

    rank_idx        = {}
    prev_rank_idx   = {}
    
    _iterator       = 0

    def __init__(self, **kwargs):
        self.to_date = kwargs.get('to_date', self.to_date)
        self.time_range = kwargs.get('time_range', self.time_range)
        self.limit = kwargs.get('limit', self.limit)
        self.get_ranking()

    def next(self):
        if len(self.rank) >= self._iterator:
            self._iterator = 0
            raise StopIteration
        r = self.rank[self._iterator]
        self._iterator += 1
        return r

    def __getitem__(self, index):
        return self.rank[index]

    def __len__(self):
        return len(self.rank)

    def get_ranking(self):
        if not self.rank:
            self.rank_idx, self.rank = self.get_ranked_wrestlers(self.to_date, time_range=self.time_range, update=True)
        return self.rank

    def get_previus_ranking(self):
        if not self.prev_rank:
            to_date = date(self.to_date.year, self.to_date.month - self.time_range, 1)
            self.prev_rank_idx, self.prev_rank = self.get_ranked_wrestlers(to_date, time_range=self.time_range)

        return self.prev_rank

    def get_ranked_wrestlers(self, to_date=date.today(), from_date=None, time_range=RANK_TIME, update=False):

        if not from_date:
            from_date = date(to_date.year, to_date.month - time_range, 1)

        a = session.query(Score).order_by(desc(func.max(Score.score))).\
            join(Match).filter(Match.date >= from_date).\
            filter(Match.date <= to_date).\
            join(Wrestler).group_by(Score.wrestler_nr).\
            slice(0,self.limit).all()

        r = []
        pos = {}

        for (i, w) in enumerate(a):
            if update:
                w.wrestler.rank = i + 1
                w.wrestler.score = w.score

            r.append(w.wrestler)

            pos[w.wrestler.nr] = i

        return (pos, r)

    def get_rank(self, nr):
        self.get_ranking()

        if isinstance(nr, Wrestler):
            nr = nr.nr

        if nr in self.rank_idx:
            return self.rank_idx[nr]+1
        else:
            return None

    def get_previous_rank(self, nr):
        self.get_previus_ranking()

        if isinstance(nr, Wrestler):
            nr = nr.nr

        if nr in self.prev_rank_idx:
            return self.prev_rank_idx[nr]+1
        else:
            return None
