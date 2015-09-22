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

def get_face(wrestler):
    '''
        Get wrestler face pic
        TODO: OpenCV3 when supported by my python

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
            except Exception as e:
                logging.warning('Failed copping face, squaring. Error: %s' % e)

                im = crop_thumb(w, thumb_size)

                #im = im.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=255)

            #im.show()
            im.save(f, 'JPEG')
        except Exception as e:
            logging.warning('Could not save image: %s' % e.msg)
            f = None

    return f

def crop_thumb(picture, size):
    im = Image.open(picture)

    w,h = im.size
    if h > w:
        y = int(max(h / 3 - (w/2), 0))
        h = w
        x = 0
    else:
        y = 0
        x = int(max(w/2 - (h/2), 0))
        w = h

    x,y,w,h = img_bounding_box((x,y,w,h), size, img_size=im.size)

    im = im.crop((x, y, x+w, y+h))
    im.thumbnail(size)
    return im

def crop_face(picture, size):


    im = Image.open(picture)

    box = find_face(picture)

    box = zoom_box(box, img_size=im.size)

    x, y, w, h = img_bounding_box(box, size, img_size=im.size)

    im = im.crop((x, y, x+w, y+h))
    im.thumbnail(size)

    '''
    im = ImageOps.fit(im, (64,64), Image.ANTIALIAS, 0.2, centering=(left,top))
    #image = ImageOps.fit(image, thumbnail_size, Image.ANTIALIAS)
    im = im.transform((64, 64), im.EXTENT, (x, y, x+w, y+h))
    '''
    return im


def zoom_box(box, img_size, scale=0.6):
    ''' Dummy function for zooming cropbox outwards
    '''
    x, y, w, h = box
    width, height = img_size

    scale = max(scale, w / width, h / height)

    z_w = w / scale
    z_h = h / scale

    x = x - ((z_w - w) / 2)
    y = y - ((z_h - h) / 2)

    return (int(x),int(y),int(z_w),int(z_h))


def img_bounding_box(box, size, img_size):

    x,y,w,h = box

    width, height = img_size

    # TODO width and height checks
    if x < 0:
        w -= x
        x = 0
    if y < 0:
        h -= y
        y = 0

    if width >= size[0] and w < size[0]:
        center = x + (w/2)
        x = int(center - size[0] / 2)
        w = int(size[0])

        if x < 0:
            x = 0
        elif x + w > width:
            x = x - (x + w - width)

    if height >= size[1] and h < size[1]:
        
        middle = y + h/2
        y = int(middle - size[1] / 2)
        h = int(size[1])

        if y < 0:
            y = 0
        elif y + h > height:
            y -= y + h - height

    return (x,y,w,h)

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
    wrestler.ranks_risen = ranking.get_previous_rank(wrestler) - ranking.get_rank(wrestler)
    wrestler_events = get_riser_stuff(wrestler)

    for e in wrestler_events:
        if '@' in e.event_name:
            event, location = e.event_name.split('@')
            e.event_name = event
            e.event_location = location.split(',')[0]
        else:
            e.event_name = e.event_name

    return (wrestler, wrestler_events)

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

    ranking = Ranking(limit=20)

    # Find highest riser, and worst
    max_r_risen = max_s_risen = -10000
    max_r_dropped = 0
    score_riser = rank_riser = rank_dropper = None
    for w in ranking:

        get_face(w)

        rank =  ranking.get_rank(w)
        prev_rank = ranking.get_previous_rank(w)

        if prev_rank is None or rank is None:
            continue

        score = ranking.get_score(w)
        prev_score = ranking.get_previous_score(w)

        rank_diff = prev_rank - rank
        score_diff = score / prev_score
        if rank_diff > max_r_risen:
            max_r_risen = rank_diff
            rank_riser = w
        elif score_diff > max_s_risen:
            max_s_risen = score_diff
            score_riser = w
        elif rank_diff < max_r_dropped:
            rank_dropper = w
            max_r_dropped = rank_diff
    
    carousel = [
        get_event_stuff(rank_riser),
        get_event_stuff(score_riser),
        get_event_stuff(rank_dropper)
    ]

    call(['lessc', '-rp=ass/', '-ru', 'style.less', 'style.css']) and exit()

    output = tpl.get_template('index.tpl.html').render(
        promotions=promotions,
        ranking=ranking,
        config=config,
        carousel=carousel
    )

    #print(output)
    print(translate_html(output, translations))
