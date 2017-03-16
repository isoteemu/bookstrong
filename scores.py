#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
    Calculate scores.
'''


import logging, sys

from sqlalchemy import asc, desc

from kayfabe.models import *
from kayfabe.scrapper import CageMatch
from kayfabe import session

from kayfabe import BASE_SCORE

import math

from random import randint
from time import strptime

RESOLUTION_PENALTIES={
    'DQ': 1.5,
    'COUNT OUT': 1.5
}

EVENT_MODIFIERS={
    'HOUSE SHOW': 1,
    'EVENT': 2,
    'DARK MATCH': 2.5,
    'TV-SHOW': 4,
    'PAY PER VIEW': 17
}

CHAMPIONSHIP_INCREMENT=1

DIFFERENCE_MAKER=5

SCORE_CACHE={}

def get_wrestler_score(nr):

    if nr in SCORE_CACHE:
        return SCORE_CACHE[nr]

    score = session.query(Score).join(Match).filter(Score.wrestler_nr==nr).order_by(desc(Match.date))

    if score.count() < 1:

        not_jobber = session.query(Wrestler).get(nr)
        if not_jobber:
            logging.info('No score for wrestler: {name}[{nr}], returning base score of {bs}'.format(name=not_jobber.name, nr=nr, bs=BASE_SCORE))
        else:
            logging.debug('No score for jobber [{nr}], returning base score of {bs}'.format(nr=nr, bs=BASE_SCORE))
        SCORE_CACHE[nr] = BASE_SCORE
    else:
        SCORE_CACHE[nr] = score.first().score

    return SCORE_CACHE[nr]


def update_score(nr, match, score):
    score = get_wrestler_score(nr) + score
    score = max(round(score),1)

    new_score = Score(
        match_id=match.id,
        wrestler_nr=nr,
        score=score
    )

    session.add(new_score)

    SCORE_CACHE[nr] = new_score.score

if __name__ == '__main__':

    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    cm = CageMatch()

    '''
    matches = session.query(Match).join(MatchWrestler).join(Wrestler).\
        distinct(Match.id).order_by(Match.date, desc(Match.id))
    '''
    matches = session.query(Match).order_by(asc(Match.date), asc(Match.id))
        #filter(Wrestler.pwi >= 502).\
    #filter(MatchWrestler.wrestler_id.in_(test)).\

    matches_count = matches.count()

    i = 1
    for match in matches.all():

        print('#', i, '/', matches_count, ':', match.date,':', match.id)

        '''
        print('>>>', match.type, match.date, ':', match.event_name, '-', match.type_desc, '-', match.resolution)
        '''

        winners = []
        losers = []

        loser_score = 0
        winner_score = 0

        event_modifier = 1
        champ = 1
        dq_penalty = 1
        m = 1

        rumble_rules = False

        for w in match.wrestlers:
            if w.resolution == MatchWrestler.WINNER:
                winners.append(w)
                winner_score = winner_score + get_wrestler_score(w.wrestler_id)
            elif w.resolution == MatchWrestler.LOSER:
                losers.append(w)
                loser_score = loser_score + get_wrestler_score(w.wrestler_id)

        '''
            Fuck Rumbles....
        '''

        if len(winners) == 1 and len(losers) > 5:
            rumble_rules = True

        if rumble_rules:
            loser_score = 1
            for loser in losers:
                loser_score = max(loser_score, get_wrestler_score(loser.wrestler_id),1)

        if len(winners) == 0 or len(losers) == 0:
            logging.info("Match '{name}' [{id}] at {at} was no contest ({resolution})".format(name=match.event_name, id=match.id, at=match.date, resolution=match.resolution))
            continue

        print('scores', winners, '[%d]' % winner_score, 'v.', losers, '[%d]' % loser_score)

        event_titles = match.titles
        if event_titles:
            for title in event_titles:
                ''' In wrestling, you only count changes '''
                if title.change == True:
                    champ = champ + CHAMPIONSHIP_INCREMENT

            champ = math.sqrt(champ)

        event_type = match.type.upper()
        if event_type in EVENT_MODIFIERS:
            event_modifier = EVENT_MODIFIERS[event_type]

        if match.resolution and match.resolution.upper() in RESOLUTION_PENALTIES:
            dq_penalty = RESOLUTION_PENALTIES[match.resolution.upper()]

        score_diff = math.sqrt((max(loser_score, 1) / max(1,winner_score)))

        # TODO Rumble

        if len(winners) < len(losers) and not rumble_rules:
            ''' Sanitize fatal 4 ways and more '''
            m = math.sqrt(len(losers)/len(winners))
            score_diff = score_diff / m

        score_base = score_diff * DIFFERENCE_MAKER * event_modifier * champ / dq_penalty
        score_base = max(score_base, 1)

        print('score:{score}, sqrt(loser:{loser}[{l_len}] / winner:{winner}[{w_len}]) / m:{m} * {MULT} * event:{event} * champ:{champ} / dq:{dq}'.format(
            score=score_base, loser=loser_score, m=m, winner=winner_score, MULT=DIFFERENCE_MAKER, champ=champ, event=event_modifier, dq=dq_penalty, l_len=len(losers), w_len=len(winners)
        ))

        for winner in winners:
            update_score(winner.wrestler_id, match, score_base)
        for loser in losers:
            update_score(loser.wrestler_id, match, -score_base)

        if i % 1000 == 0:
            session.commit()
        i = i + 1

    session.commit()

    #for (wrestler_nr,) in session.query(Wrestler.cm).order_by(Wrestler.pwi).slice(554,1).all():
