#!/usr/bin/env python3
'''
Various functions for model handling.
'''

from . import session
from .models import Gimmick, Match, MatchWrestler, Wrestler

from sqlalchemy import asc, desc


def get_last_match(wrestler: Wrestler) -> Match:
    '''Return wrestler last match.'''
    q = session.query(Match).join(MatchWrestler).filter_by(wrestler_id=wrestler.nr).order_by(desc(Match.date)).limit(1)
    return q.one()


def get_gimmick_id(id, gimmick: str) -> int:
    '''Get gimmick ID by gimmick name.'''
    gimmick_query = session.query(Gimmick).filter_by(wrestler_nr=id, gimmick=gimmick)
    if gimmick_query.count() >= 1:
        return gimmick_query.first().id