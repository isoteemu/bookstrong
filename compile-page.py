#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from kayfabe import BASE_SCORE, session
from kayfabe.models import *
from kayfabe.scrapper import WikiData
from kayfabe.view import *
from kayfabe.scoring import *
from kayfabe.stats import get_biggest_cheater, match_ending_stats

from sqlalchemy import asc, desc, func

import gettext, locale

from jinja2 import Template
from jinja2 import Environment, FileSystemLoader

import argparse
import logging, sys
from datetime import date, timedelta
from os import path
from PIL import Image, ImageOps
from glob import glob
import json

from subprocess import call, check_output

def get_riser_stuff(wrestler):
    scores = session.query(Score).filter_by(wrestler_nr=wrestler.nr).\
        join(Match).order_by(asc(Match.date))

    matches = []

    prev_score = BASE_SCORE

    for score in scores:
        score_diff = score.score / prev_score
        prev_score = score.score
        matches.append((score_diff, score.match))

    top = sorted(matches, key=lambda diff: diff[0], reverse=True)[0:5]
    return [i[1] for i in top]

def get_event_stuff(wrestler):
    logger.debug('Event stuff for wrestler %s', wrestler.name)

    try:
        wrestler.ranks_risen = ranking.get_previous_rank(wrestler) - ranking.get_rank(wrestler)
    except (TypeError, AttributeError):
        wrestler.ranks_risen = 0

    wrestler_events = get_riser_stuff(wrestler)

    for e in wrestler_events:
        if '@' in e.event_name:
            event, location = e.event_name.split('@')
            e.event_name = event
            e.event_location = location.split(',')[0]
        else:
            e.event_name = e.event_name

    return (wrestler, wrestler_events)


def carousel_cheater(date_from, date_to):
    cheater = get_biggest_cheater(date_from, date_to)
    cheater_stats = match_ending_stats(cheater, date_from, date_to)

    return ('carousel-cheater.tpl.html', {
        'wrestler': cheater,
        'stats': cheater_stats
    })


def carousel_rank_riser(riser: Wrestler):
    return ('carousel-rank-riser.tpl.html', {
        'wrestler': riser,
        'stats': get_event_stuff(riser)
    })


def carousel_score_riser(riser: Wrestler):
    return ('carousel-score-riser.tpl.html', {
        'wrestler': riser,
        'stats': get_event_stuff(riser)
    })


if __name__ == '__main__':

    Session.configure(autoflush=False)

    config = {
        'items_per_page': 20
    }

    limit = 1000

    cmdline = argparse.ArgumentParser(description='Compile page.')

    cmdline.add_argument('--debug', help='Debug', action='store_true')
    cmdline.add_argument('--output-file', help='Output file.')
    cmdline.add_argument('--limit', help='Limit wrestler count.',
                         type=int, default=limit)

    args = cmdline.parse_args()

    if args.debug:
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    else:
        logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    if args.limit:
        limit = args.limit

    logger = logging.getLogger()

    translations = gettext.translation('bookstrong', localedir='ass/locale', languages=['ja'])

    translations.install()

    tpl = Environment(loader=FileSystemLoader('tpl'), extensions=['jinja2.ext.i18n'])
    tpl.install_gettext_translations(translations)

    tpl.filters['timetag'] = format_datetime
    tpl.filters['img'] = get_image_path

    to_date = date.today()
    from_date = date(to_date.year, to_date.month, 1) - 3 * timedelta(days=30)

    promotions = dict()

    ranking = Ranking(limit=limit, from_date=from_date, to_date=to_date)

    # Find highest riser, and worst
    max_r_risen = max_s_risen = -10000
    max_r_dropped = -1
    score_riser = rank_riser = rank_dropper = None
    for w in ranking:

        logger.info("Processing Wrestler %s [%d]", w.name, w.nr)

        if w.promotion_id not in promotions:
            promotions[w.promotion_id] = session.query(Promotion).filter_by(cm_id=w.promotion_id).one()

        rank = ranking.get_rank(w)
        prev_rank = ranking.get_previous_rank(w)

        if prev_rank is None or rank is None:
            continue

        score = ranking.get_score(w)
        prev_score = ranking.get_previous_score(w)

        rank_diff = prev_rank - rank
        score_diff = score / prev_score

        if rank_diff > max_r_risen:
            logger.debug("New rank riser: %s [%d], rised %d", w.name, w.nr, rank_diff)
            max_r_risen = rank_diff
            rank_riser = w
        if score_diff > max_s_risen:
            logger.debug("New score riser: %s [%d], rised %d", w.name, w.nr, rank_diff)
            max_s_risen = score_diff
            score_riser = w
        if rank_diff < max_r_dropped:
            logger.debug("New rank dropper: %s [%d], dropper %d", w.name, w.nr, rank_diff)
            rank_dropper = w
            max_r_dropped = rank_diff

    carousel = []

    '''
    if rank_riser:
        carousel.append(get_event_stuff(rank_riser))

    if score_riser:
        carousel.append(get_event_stuff(score_riser))

    if rank_dropper:
        carousel.append(get_event_stuff(rank_dropper))
    '''


    carousel.append(carousel_rank_riser(rank_riser))
    carousel.append(carousel_score_riser(score_riser))
    carousel.append(carousel_cheater(date_from=ranking.from_date, date_to=to_date))

    output = tpl.get_template('index.tpl.html').render(
        promotions=promotions,
        ranking=ranking,
        config=config,
        carousel=carousel
    )

    call(['lessc', '-rp=ass/', '-ru', 'ass/less/style.less', 'style.css']) and exit()

    output = str(translate_html(output, translations))
    if args.output_file:
        open(args.output_file, 'w').write(output)
    else:
        print(output)
