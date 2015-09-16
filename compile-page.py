#!/usr/bin/env python3

from kayfabe import session
from kayfabe.models import *
from kayfabe.scrapper import WikiData

from sqlalchemy import asc, desc, func

from jinja2 import Template
from jinja2 import Environment, FileSystemLoader

import logging, sys
from datetime import date
from os import path
from urllib.request import urlretrieve
from PIL import Image

tpl = Environment(loader=FileSystemLoader('tpl'))

from teemu.Bing import Bing
from teemu.Image import square_image

def get_face(wrestler):
    '''
        Get wrestler face pic
        TODO: OpenCV3 when supported by my python
        
        http://www.cagematch.net/site/main/img/portrait/00000293.jpg
    '''
    w = 'ass/w/{:0>8}.jpg'.format(wrestler.nr)
    f = 'ass/f/{:0>8}.png'.format(wrestler.nr)
    if not path.isfile(f):
        try:
            if not path.isfile(w):
                r = Bing().imageSearch(u'%s wrestler' % wrestler.name, ImageFilters="'Face:Face'")
                urlretrieve(r[0]['Thumbnail']['MediaUrl'], w)
            im = Image.open(w)
            im = square_image(im, (80,80))
            im = im.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=255)
            im.save(f, 'PNG', colors=255)
        except:
            f = None

    return f

def get_wrestlers():

    today = date.today()
    since = date(today.year, today.month-1, 1)

    a = session.query(Score).order_by(desc(func.max(Score.score))).\
        join(Match).filter(Match.date >= since).\
        join(Wrestler).\
        group_by(Score.wrestler_nr).slice(0,27).all()

    r = []

    for (i, w) in enumerate(a):
        w.wrestler.rank = i + 1
        r.append(w.wrestler)

    return r

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    promotions = session.query(Promotion).join(Wrestler).filter(Wrestler.nr != None).all()
    wrestlers = get_wrestlers()

    for w in wrestlers:
        w.face = get_face(w)

    #print(wrestlers[0].rank)


    print(tpl.get_template('index.tpl.html').render(
        promotions=promotions,
        wrestlers=wrestlers
    ))
