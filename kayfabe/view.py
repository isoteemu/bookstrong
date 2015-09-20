#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from kayfabe.models import *

from bs4 import BeautifulSoup
from copy import copy

import locale

from glob import glob


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


def get_image_path(obj):
    ''' Return suitable image for object.
    '''
    if isinstance(obj, Promotion):
        return get_promotion_logo(obj)
    elif isinstance(obj, Wrestler):
        return get_wrestler_photo(obj)


def get_promotion_logo(promotion):
    ''' Get promotion logo image.
    '''
    pics = glob('ass/p/{:0>8}.*'.format(promotion.cm_id))
    if len(pics):
        return pics[0]
    return None


def get_wrestler_photo(wrestler):
    ''' Get wrestler image.
    '''
    pics = glob('ass/f/{:0>8}.*'.format(wrestler.nr))
    if len(pics):
        return pics[0]
    return None
