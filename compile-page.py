#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
from PIL import Image, ImageOps
import json

from subprocess import call, check_output

tpl = Environment(loader=FileSystemLoader('tpl'))

from teemu.Bing import Bing
from teemu.Image import square_image

def get_face(wrestler):
    '''
        Get wrestler face pic
        TODO: OpenCV3 when supported by my python
        
        http://www.cagematch.net/site/main/img/portrait/00000293.jpg
    '''
    
    thumb_size = (124,124)

    w = 'ass/w/{:0>8}.jpg'.format(wrestler.nr)
    f = 'ass/f/{:0>8}.jpg'.format(wrestler.nr)
    if not path.isfile(f):
        try:
            if not path.isfile(w):
                try: 
                    data = wd.search_wrestler(wrestler.name)
                    pic = wd.get_claim_values(data, wd.CLAIM_IMAGE)[0]
                    src = wd.get_image_url(pic)
                    if not src:
                        raise RuntimeError('No picture found')
                    urlretrieve(src, w)
                except e:
                    logging.warning('Could not crop face: %s' % e)
                    r = Bing().imageSearch(u'%s wrestler' % wrestler.name, ImageFilters="'Face:Face'")
                    urlretrieve(r[0]['Thumbnail']['MediaUrl'], w)
            try:
                im = crop_face(w, thumb_size)
            except:
                
                im = Image.open(w)
                im = square_image(im, thumb_size)
                #im = im.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=255)


            im.save(f, 'JPEG')
        except:
            f = None

    return f

def crop_face(picture, size=(64,64)):
    x,y,w,h = find_face(picture)

    im = Image.open(picture)

    im = im.crop((x, y, x+w, y+h))
    im.thumbnail(size)

    #im = ImageOps.fit(im, (64,64), Image.ANTIALIAS, 0.2, centering=(left,top))
    ##image = ImageOps.fit(image, thumbnail_size, Image.ANTIALIAS)
    #im = im.transform((64, 64), im.EXTENT, (x, y, x+w, y+h))
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

def get_wrestlers(from_date=date.today()):

    since = date(from_date.year, from_date.month-1, 1)

    a = session.query(Score).order_by(desc(func.max(Score.score))).\
        join(Match).filter(Match.date >= since).\
        join(Wrestler).\
        group_by(Score.wrestler_nr).slice(0,100).all()

    r = []

    for (i, w) in enumerate(a):
        w.wrestler.rank = i + 1
        r.append(w.wrestler)

    return r

if __name__ == '__main__':

    config={
        'items_per_page': 20
    }

    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    wd = WikiData()
    
    promotions = session.query(Promotion).join(Wrestler).filter(Wrestler.nr != None).all()
    wrestlers = get_wrestlers()

    for w in wrestlers:
        w.face = get_face(w)

    #print(wrestlers[0].rank)

    call(['lessc', '-rp=ass/', '-ru', 'style.less', 'style.css']) and exit()

    print(tpl.get_template('index.tpl.html').render(
        promotions=promotions,
        wrestlers=wrestlers,
        config=config
    ))
