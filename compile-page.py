#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from kayfabe import session, BASE_SCORE
from kayfabe.models import *
from kayfabe.scrapper import WikiData, duck_duck_go
from kayfabe.view import *
from kayfabe.scoring import *

from sqlalchemy import asc, desc, func

import gettext, locale

from jinja2 import Template
from jinja2 import Environment, FileSystemLoader

import logging, sys
from datetime import date
from os import path
from urllib.request import urlretrieve
from PIL import Image, ImageOps
from glob import glob
import json


from subprocess import call, check_output


from teemu.google import CSE
from teemu.Bing import Bing
from teemu.Image import square_image

def get_face(wrestler):
    '''
        Get wrestler face pic
        TODO: OpenCV3 when supported by my python

        http://www.cagematch.net/site/main/img/portrait/00000293.jpg
    '''

    thumb_size = (100,100)

    name = wrestler.name.strip()

    w = 'ass/f/{:0>8}.jpg'.format(wrestler.nr)
    f = 'ass/t/f/{:0>8}.jpg'.format(wrestler.nr)
    if not path.isfile(f):
        try:
            if not path.isfile(w):
                img_url = None
                try:
                    data = wd.search_wrestler(name)
                    pic = wd.get_claim_values(data, wd.CLAIM_IMAGE)[0]
                    src = wd.get_image_url(pic)
                    if src:
                        img_url = src
                except:
                    logging.debug('Did not find image from wikipedia')
                    pass

                try:
                    if not img_url:
                        ddg = duck_duck_go(name)
                        img_url = ddg['Image']
                        logging.info('Image %s from duck duck go' % img_url)

                except:
                    pass

                try:
                    if not img_url:
                        params = {
                            'imgType':      'face',
                            'searchType':   'image'
                        }
                        r = CSE().query(name, params=params)
                        if 'items' in r:
                            img_url = r['items'][0]['link']
                except:
                    pass

                try:
                    if not img_url:
                        r = Bing().imageSearch(u'%s' % name, ImageFilters="'Face:Face'")
                        if len(r):
                            img_url = r[0]['Thumbnail']['MediaUrl']
                except:
                    pass

                if not img_url:
                    img_url = 'http://www.cagematch.net/site/main/img/portrait/{:0>8}.jpg'.format(wrestler.nr)
                    logging.warning('Fall back on stealing images: %s' % img_url)

                urlretrieve(img_url, w)

            try:
                im = crop_face(w, thumb_size)
            except:
                im = Image.open(w)
                im = square_image(im, thumb_size)
                #im = im.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=255)

            im.save(f, 'JPEG')
        except Exception as e:
            logging.warning('Could not save image: %s' % e.msg)
            f = None

    return f

def crop_face(picture, size=(64,64)):

    # TODO dont upscale

    x, y, w, h = find_face(picture)

    im = Image.open(picture)

    im = im.crop((x, y, x+w, y+h))
    im.thumbnail(size)
    '''
    im = ImageOps.fit(im, (64,64), Image.ANTIALIAS, 0.2, centering=(left,top))
    #image = ImageOps.fit(image, thumbnail_size, Image.ANTIALIAS)
    im = im.transform((64, 64), im.EXTENT, (x, y, x+w, y+h))
    '''
    return im


def find_face(picture):
    data = check_output(["python2", "face-detect.py", picture]).decode('utf-8')
    faces = json.loads(data)

    max_idx = None
    max_size = 0
    for i, face in enumerate(faces):
        face_size = face[2] * face[3]
        if face_size > max_size:
            max_size = face_size
            max_idx = i

#    print('Biggest face', max_idx, faces[max_idx])

    return faces[max_idx]



def get_wrestler_score(to_date, wrestler):
    month_ago = date(to_date.year, to_date.month-1, 1)
    a = session.query(func.max(Score.score)).\
        join(Wrestler).filter_by(nr=wrestler.nr).\
        join(Match).filter(Match.date <= to_date).\
        filter(Match.date >= month_ago).slice(0,1)

    score, = a.one()
    return score


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


def get_previous_rank(wrestler):
    if not hasattr(get_previous_rank, "ranking"):
        get_previous_rank.ranking
    get_previous_rank.ranking
    return


if __name__ == '__main__':

    config = {
        'items_per_page': 20
    }

    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    translations = gettext.translation('bookstrong', localedir='ass/locale', languages=['ja'])
    translations.install()

    tpl = Environment(loader=FileSystemLoader('tpl'), extensions=['jinja2.ext.i18n'])
    tpl.install_gettext_translations(translations)

    tpl.filters['timetag'] = format_datetime
    tpl.filters['img'] = get_image_path

    wd = WikiData()

    to_date = date.today()
    prev_date = date(to_date.year, to_date.month-1, 1)

    promotions = session.query(Promotion).join(Wrestler).filter(Wrestler.nr != None).all()
    
    ranking = Ranking()
    #wrestlers = get_ranked_wrestlers(to_date=to_date, from_date=prev_date)

    # Find highest riser
    max_risen = -10000
    top_riser = None
    for w in ranking:
        rank =  ranking.get_rank(w)
        prev_rank = ranking.get_previous_rank(w)

        if prev_rank is None or rank is None:
            continue

        rank_diff = prev_rank - rank

        if rank_diff > max_risen:
            max_risen = rank_diff
            top_riser = w

    top_riser.ranks_risen = ranking.get_previous_rank(top_riser) - ranking.get_rank(top_riser)
    riser_events = get_riser_stuff(top_riser)

    for e in riser_events:
        event, location = e.event_name.split('@')
        e.event_name = event
        e.event_location = location.split(',')[0]

    call(['lessc', '-rp=ass/', '-ru', 'style.less', 'style.css']) and exit()

    output = tpl.get_template('index.tpl.html').render(
        promotions=promotions,
        ranking=ranking,
        config=config,
        top_riser=top_riser,
        events=riser_events
    )

    #print(output)
    print(translate_html(output, translations))
