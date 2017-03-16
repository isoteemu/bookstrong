#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# TODO: Depracete - siirrä jinjan functioksi jos on niikseen.

from kayfabe.models import *
from kayfabe.scrapper import FaceFetcher
from kayfabe.Image import get_thumb

from bs4 import BeautifulSoup
from copy import copy

import locale
import logging

import os
from glob import glob

IMAGES_PATH = 'ass/img/'

def translate_html(page, translation):
    ''' Translate lang elements.
    Goes throug HTML tree, and searches <span lang="en"></span>
    tags translating them.
    '''

    lang = translation.info()['language']

    soup = BeautifulSoup(page, 'lxml')

    tags = soup.select('span[lang="en"]') + soup.select('title[lang="en"]')

    for span in tags:
        t_span = copy(span)
        t_span['lang'] = lang

        try:
            t_span['title'] = translation.gettext(t_span['title'])
        except KeyError:
            pass

        t_span.string = translation.gettext(t_span.string)

        # TODO Title check
        if t_span.string != span.string:
            span.insert_before(t_span)
        else:
            del span['lang']

    return soup


def format_datetime(value, format='date'):
    ''' Jinja2 filter for generating locale appropriate <time> tag
    '''
    el = '<time datetime="{iso}">{locale}</time>'

    if format == 'date':
        lang = 'en'
        try:
            lang = locale.getlocale()[0].split('_')[0]
        except:
            pass

        innards = value.strftime('%Y.%m.%d (<span lang="{lang}">%a</span>)'.format(lang=lang))

    return el.format(iso=value.isoformat(), locale=innards)


def get_image_path(obj: object, size: str ="full") -> str:
    ''' Return suitable image for object.

        :param obj:     Object to create image url for.
        :param size:    Image size. "full" for full size, otherwise "WIDTHxHEIGHT".
    '''

    image = None
    ass_path = IMAGES_PATH

    # Select suitable folder based on object type.
    if isinstance(obj, Promotion):
        image = os.path.join(ass_path, 'p', '{:0>8}'.format(obj.cm_id))
        image = _get_image(image)

    elif isinstance(obj, Wrestler):
        image = os.path.join(ass_path, 'w', '{:0>8}'.format(obj.nr))
        image = _get_image(image)

        if not image:
            image = FaceFetcher().get_face(obj, path=os.path.join(ass_path, 'w'))

    if not image:
        image = 'ass/1.gif'
    elif size != "full":
        # Set size into tuple.
        if size == "thumb":
            size = (100,100)
        else:
            size = tuple(size.split('x'))

        image = get_thumb(image, thumb_size=size)
    return image


def _get_image(basename):
    ''' Get suitable image.
        TODO: Implement extension checking.
    '''

    g = '{basename}.*'.format(basename=basename)

    pics = glob(g)
    if len(pics):
        return pics[0]

    return None
