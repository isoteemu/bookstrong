#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from kayfabe.models import *

from bs4 import BeautifulSoup
from copy import copy

import locale
import logging

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


def get_image_path(obj, t="full"):

    ''' Return suitable image for object.
    '''
    ass_path = 'ass'
    if t.lower() == 'thumb':
        ass_path = '%s/t' % ass_path

    if isinstance(obj, Promotion):
        id = obj.cm_id
        path = '%s/p' % ass_path
    elif isinstance(obj, Wrestler):
        id = obj.nr
        path = '%s/f' % ass_path

    src = get_img(id, path)
    if not src:
        src = 'ass/1.gif'

    return src

def get_img(id, path):
    
    g = '{path}/{id:0>8}.*'.format(path=path,id=id)

    pics = glob(g)
    if len(pics):
        return pics[0]
    return ''
