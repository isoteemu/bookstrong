#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging, sys

import requests
from bs4 import BeautifulSoup

from urllib.parse import urlparse, parse_qs
from urllib.request import urlretrieve
from urllib.error import HTTPError

import time
from glob import glob
import xattr

from .models import Wrestler

try:
    from teemu.google import CSE
except:
    pass


class Scrapper:
    scrape_delay = 1

    _requests = requests.session()
    _last_scrape = 0

    def __init__(self):
        self._requests.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'})

    def get(self, url, **kwargs):
        if self._last_scrape:
            sleeptime = max(0, self.scrape_delay - (time.time() - self._last_scrape))
            time.sleep(sleeptime)

        self._last_scrape = time.time()
        return self._requests.get(url, **kwargs)


try:
    ''' Set cache control for requests '''
    from cachecontrol import CacheControl
    from cachecontrol.caches import FileCache
    import tempfile

    import calendar
    from cachecontrol.heuristics import BaseHeuristic
    from datetime import datetime, timedelta
    from email.utils import parsedate, formatdate

    class OneWeekHeuristic(BaseHeuristic):
        ''' Class to force storing pages in CacheControl.

        From CacheControl examples.
        '''

        def update_headers(self, response):
            date = parsedate(response.headers['date'])
            expires = datetime(*date[:6]) + timedelta(weeks=1)
            return {
                'expires' : formatdate(calendar.timegm(expires.timetuple())),
                'cache-control' : 'public',
            }

    Scrapper._requests = CacheControl(Scrapper._requests, cache=FileCache(
        tempfile.gettempdir()+'/cagematch-cache', forever=True,
        
    ), heuristic=OneWeekHeuristic())

except Exception as e:
    logging.warning('CacheControl not available:', e)



class WikiData(Scrapper):

    API_URL = 'https://www.wikidata.org/w/api.php'
    COMMONS_URL = 'https://commons.wikimedia.org/wiki/File:'

    WRESTLER_ID = 13474373
    PROMOTION_ID = 131359
    COMPANY_ID = 783794

    CLAIM_IMAGE = 'P18'
    CLAIM_OCCUPATION = 'P106'
    CLAIM_INDUSTRY = 'P452'
    CLAIM_INSTANCE = 'P31'

    def search(self, search, **kwargs):
        kwargs.setdefault('language', 'en')
        kwargs.setdefault('action', 'wbsearchentities')
        kwargs.setdefault('search', search)
        kwargs.setdefault('limit', 25)
        r = self.get(self.API_URL, params=kwargs)
        return r.json()


    def search_wrestler(self, search):
        r = self.search(search)
        ids = []
        for e in r['search']:
            ids.append(e['id'])

        entities = self.entities(ids)

        wrestlers = {}

        for id in entities['entities']:
            entity = entities['entities'][id]

            if entity.get('type') != 'item':
                continue

            jobs = self.get_claim_values(entity, self.CLAIM_OCCUPATION)

            if self.WRESTLER_ID in jobs:
                wrestlers[id] = entity
            elif 'en' in entity['descriptions'] and 'wrestler' in entity['descriptions']['en']['value']:
                wrestlers[id] = entity

        logging.debug('Found %d wrestlers' % len(wrestlers))

        if len(wrestlers) == 1:
            return list(wrestlers.items())[0][1]


    def get_claim_values(self, entity, claim):
        r = []

        for item in entity['claims'].get(claim, []):
            if item['mainsnak']['datavalue']['type'] == 'wikibase-entityid':
                r.append(item['mainsnak']['datavalue']['value']['numeric-id'])
            else:
                r.append(item['mainsnak']['datavalue']['value'])

        return r

    def get_image_url(self, title, **kwargs):
        kwargs.setdefault('action', 'query')
        kwargs.setdefault('titles', 'File:%s' % title)
        kwargs.setdefault('prop', 'imageinfo')
        kwargs.setdefault('iiprop', 'url')

        r = self.get(self.API_URL, params=kwargs).json()
        return r['query']['pages']['-1']['imageinfo'][0]['url']

    def entities(self, ids, **kwargs):
        kwargs.setdefault('action', 'wbgetentities')
        kwargs.setdefault('ids', '|'.join(ids))
        r = self.get(self.API_URL, params=kwargs)
        return r.json()

    def get(self, url, **kwargs):
        params = kwargs.get('params', {})
        params['format'] = 'json'
        kwargs['params'] = params
        return super().get(url, **kwargs)


class ProWrestlingWiki(Scrapper):

    SEARCH_URL = "http://prowrestling.wikia.com/api/v1/Search/List"
    ARTICLE_URL = "http://prowrestling.wikia.com/api/v1/Articles/Details"

    def search_id(self, wrestler, **kwargs):
        ''' Search for article ID. Uses name to compare title.'''

        kwargs.setdefault('namespaces', 0)

        gimmicks = ['%s' % g.gimmick.lower().strip() for g in wrestler.gimmicks]

        query = ', '.join(gimmicks)

        r = self.search(query, **kwargs)
        for entry in r['items']:

            title = entry['title'].lower()
            if title in gimmicks:
                return entry['id']

    def search(self, query: str, **kwargs):
        ''' Search for article '''
        kwargs.setdefault('limit', 25)
        kwargs['query'] = query

        r = self.get(self.SEARCH_URL, params=kwargs)
        return r.json()

    def search_image(self, wrestler: Wrestler) -> str:
        ''' Search for wrestler image. '''

        image = None

        id = self.search_id(wrestler)
        if id:
            article = self.article(id)

            image = article['thumbnail']
            if image:
                image = image[:image.find('/revision/latest')]

        return image

    def article(self, id, **kwargs):
        ''' Return article contents.
            :param id:     article id
            :param titles:  Titles with underscores instead of spaces, comma-separated
            :param abstract: The desired length for the article's abstract
            :param width:   The desired width for the thumbnail
            :param height:  The desired height for the thumbnail
        '''

        kwargs['ids'] = id

        r = self.get(self.ARTICLE_URL, params=kwargs)
        a = r.json()['items'].popitem()[1]

        return a


class CageMatch(Scrapper):
    URLS = {
        'SEARCH': 'http://www.cagematch.net/?id=666',
        'PROMOTION': 'http://www.cagematch.net/?id=8',
        'WRESTLER': 'http://www.cagematch.net/?id=2',
        'MATCHES': 'http://www.cagematch.net/?id=2&page=4',
        'TITLE_SEARCH': 'http://www.cagematch.net/?id=5&view=names',
        'TITLE': 'http://www.cagematch.net/?id=5'
    }


    scrape_delay = 5

    _title_cache = None

    def search(self, name):
        '''
            Search wrestler cagematch ID
        '''

        page = self.get(self.URLS['SEARCH'], params={'search': name}).text

        soup = BeautifulSoup(page)

        workers = soup.select('td a[href^="?id=2&nr="]')

        '''
            Create list of found wrestlers, where key is cagematch id and value is
            number of counts wrestler was listed in cagematch.net search results
        '''

        wrestlers = {}

        for worker in workers:
            nr = self.id_from_url(worker['href'])
            wrestlers.setdefault(nr, 0)
            wrestlers[nr] = wrestlers[nr] + 1

        return wrestlers

        #print(container.find_all('img', class_='WorkerPicture'))
        #?id=2&nr=2250&gimmick=Seth+Rollins

    def search_title(self, name):
        name = name.strip()

        if name in self._title_cache:
            return self._title_cache.get(name)

        ''' Search title by name '''
        page = self.get(self.URLS['TITLE_SEARCH'], params={'search':name}).text
        soup = BeautifulSoup(page)

        titles = []

        for result in soup.select('td a[href^="?id=5&nr="]'):
            title_nr = self.id_from_url(result['href'])
            if title_nr not in titles:
                titles.append(title_nr)

        self._title_cache[name] = titles

        return titles


    def wrestler(self, id):

        details = {
            'name': '',
            'promotion': None,
            'gimmicks': []
        }

        page = self.get(self.URLS['WRESTLER'], params={'nr': id}).text
        soup = BeautifulSoup(page)

        details['name'] = soup.find('h1', class_='TextHeader').text.strip()

        promotion = soup.select('td.InformationBoxContents a[href^="?id=8&nr="]')
        if promotion:
            details['promotion'] = int(parse_qs(promotion[0]['href'])['nr'][0])

        parent_gimmick = ''
        gimmicks = soup.select('td.InformationBoxContents a[href^="?id=2&nr=%d&page=4&gimmick="]' % id)
        for gimmick in gimmicks:
            prev = gimmick.previous_sibling

            # They use &nbsp; in a.k.a. tag.
            if prev and prev == '  ':
                details['gimmicks'].append((parent_gimmick, gimmick.get_text().strip()))
            else:
                parent_gimmick = gimmick.get_text().strip()
                details['gimmicks'].append(parent_gimmick)

        return details

    def promotion(self, id):

        data = {
            'name': '',
            'abbrevation': ''
        }

        page = self.get(self.URLS['PROMOTION'], params={'nr': id}).text
        soup = BeautifulSoup(page)

        soup.find('h1', class_='TextHeader').text

        name = soup.find('td', class_='InformationBoxTitle', text='Current name:').\
            find_next_sibling('td', class_='InformationBoxContents')
        data['name'] = name.get_text().strip()

        abbr = soup.find('td', class_='InformationBoxTitle', text='Current abbreviation:').\
            find_next_sibling('td', class_='InformationBoxContents')
        data['abbrevation'] = abbr.get_text().strip()

        return data

    def title(self, nr):
        details = {
            'name': '',
            'nr': nr,
            'promotion': 0
        }

        page = self.get(self.URLS['TITLE'], params={'nr': id}).text
        soup = BeautifulSoup(page)
        details['name'] = soup.select('h1.TextHeader')[0].get_text()
        details['promotion'] = id_from_url(soup.select('a[href^="?id=8&nr="]')[0]['href'])


    def matches(self, id):
        ''' Too complicated to add here, see scrape-matches.py '''
        return

    def id_from_url(self, url):
        parts = urlparse(url)
        href = parse_qs(parts[4])
        nr = href['nr'][0]
        return int(nr)


class FaceFetcher():

    METHODS = None

    target_folder   = 'ass/img/w'
    extensions      = ['jpg', 'jpeg', 'gif', 'png']

    wikidata = WikiData()
    pww = ProWrestlingWiki()

    googlecse = None
    bing = None

    # Only try once per session
    processed = []


    def __init__(self, register_default_methods=True):
        '''
            :param register_default_methods:     Register default methods.
        '''
        self.METHODS = []


        if register_default_methods:
            logging.debug("Registering default methods")

            self.register_method(self.url_from_prowrestlingwiki, 10)
            self.register_method(self.url_from_wikidata, 30)
            self.register_method(self.url_from_duckduckgo, 60)

            try:
                if CSE:
                    self.register_method(self.url_from_googlecse, 70)
            except NameError as e:
                pass


    def register_method(self, method, weight=50):

        self.METHODS.append((weight, method))
        logging.debug("Adding method %s. Count %d", method, len(self.METHODS))
        return


    def get_face(self, wrestler, path=None, force_update=False):
        ''' Get wrestler photo.

            TODO: Always scrap, remove existing logic.

            :param wrestler:        Wrestler Model.
            :param path:            Path to lookup/store images.
            :param force_update:    Force retrieving new picture.
        '''

        # Check that wrestler is not processed.
        if wrestler.nr in FaceFetcher.processed and force_update is False:
            return None

        FaceFetcher.processed.append(wrestler.nr)

        if not path:
            path = self.target_folder

        if not force_update:
            glob_path = '{path}/{id:0>8}.*'.format(path=path,id=wrestler.nr)

            pics = glob(glob_path)

            for image in pics:
                ext = image.split('.')[-1].lower().strip()
                if ext in self.extensions:
                    return image

        for url in self.fetch_face(wrestler):

            ext = url.split('.')[-1].lower().strip()
            if ext not in self.extensions:
                ext = 'jpg'
                logging.warning('Could not detect file extension for url \'%s\', fallback to .%s' % (url, ext))

            save = '{path}/{id:0>8}.{ext}'.format(path=path, id=wrestler.nr, ext=ext)

            try:
                fetch = urlretrieve(url, save)

                if fetch:
                    logging.debug('Found wrestler image: "%s". Saving to: %s' % (url, save))

                    attrs = xattr.xattr(save)
                    attrs['user.xdg.origin.url'] = url.encode(encoding='utf_8')

                    return save

            except HTTPError as e:
                logging.warning("URL retrieval error: %s", e)


    def fetch_face(self, wrestler):
        ''' Iterate throug self.METHODS, until something is found.
        '''

        methods = sorted(self.METHODS, key=lambda m: m[0], reverse=False)

        for weight, method in methods:
            try:
                logging.debug("Trying fetch image for '%s' using '%s'", wrestler.name, method)
                url = method(wrestler)
                if url:
                    yield url
                else:
                    next

            except Exception as e:
                logging.warning('Error occured while fetching face: %s' % e)
            time.sleep(2)
        return


    def url_from_prowrestlingwiki(self, wrestler):
        ''' Search image using Pro Wrestling Wikia '''
        if not self.pww:
            self.pww = ProWrestlingWiki()

        return self.pww.search_image(wrestler)


    def url_from_wikidata(self, wrestler):
        if not self.wikidata:
            self.wikidata = WikiData()

        wd = self.wikidata
        name = wrestler.name

        try:
            data = wd.search_wrestler(name)
            pic = wd.get_claim_values(data, wd.CLAIM_IMAGE)[0]
            src = wd.get_image_url(pic)

            if src:
                return src
        except Exception as e:
            logging.debug('Did not find image from wikipedia: %s' % e)

        return None


    def url_from_duckduckgo(self, wrestler):

        name = wrestler.name.strip()
        queries = ['%s wrestler' % name, name]

        for q in queries:
            ddg = duck_duck_go(q)
            if ddg['Image']:
                return ddg['Image']

        return None
    
    def url_from_googlecse(self, wrestler):
        name = wrestler.name.strip()
        queries = ['%s wrestler' % name, name]
        
        if not self.googlecse:
            self.googlecse = CSE()

        params = {
            'imgType':      'face',
            'searchType':   'image'
        }

        for q in queries:
            try:
                r = self.googlecse.query(q, params=params)
                if 'items' in r:
                    return r['items'][0]['link']
            except Exception as e:
                logging.warning('Could not query Google CSE: %s' % e)

        return None


    def url_from_bing(self, wrestler):
        name = wrestler.name.strip()
        queries = ['%s wrestler' % name, name]
        
        if not self.bing:
            self.bing = Bing()

        for q in queries:
            try:
                r = self.bing.imageSearch(u'%s' % name, ImageFilters="'Face:Face'")
                if len(r):
                    return r[0]['Thumbnail']['MediaUrl']
            except Exception as e:
                logging.warning('Could not query Bing: %s' % e)

        return None


def duck_duck_go(query):
    params = {
        'q': query,
        'format': 'json'
    }

    r = requests.get('https://api.duckduckgo.com/', params=params)
    d = r.json()
    if d['Type'] == 'D':
        params['q'] = '%s wrestler' % params['q']
        r = requests.get('https://api.duckduckgo.com/', params=params)
        d = r.json()

    return d

cagematchnet = CageMatch()
