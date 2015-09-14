#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging, sys

import requests
from bs4 import BeautifulSoup

from urllib.parse import urlparse, parse_qs

import time

class CageMatch:
	URLS = {
		'SEARCH': 'http://www.cagematch.net/?id=666',
		'PROMOTION': 'http://www.cagematch.net/?id=8',
		'WRESTLER': 'http://www.cagematch.net/?id=2',
		'MATCHES': 'http://www.cagematch.net/?id=2&page=4',
		'TITLE_SEARCH': 'http://www.cagematch.net/?id=5&view=names',
		'TITLE': 'http://www.cagematch.net/?id=5'
	}

	_requests = requests.session()

	_last_scrape = 0

	_title_cache = None

	def __init__(self):
		try:
			from cachecontrol import CacheControl
			from cachecontrol.caches import FileCache
			import tempfile
			self._requests = CacheControl(self._requests, cache=FileCache(tempfile.gettempdir()+'/cagematch-cache', forever=True))
		except:
			logging.warning('CacheControl not available')

		self._requests.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'})


	def search(self, name):
		'''
			Search wrestler cagematch ID
		'''

		page = self.get(self.URLS['SEARCH'], params={'search': name}).text

		soup = BeautifulSoup(page)
		workers = soup.find('a', href='#wrestler').parent.parent.find_all('img', class_='WorkerPicture')

		'''
			Create list of found wrestlers, where key is cagematch id and value is
			number of counts wrestler was listed in cagematch.net search results
		'''

		wrestlers = {}

		for worker in workers:
			nr = self.id_from_url(worker.parent['href'])
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

		details['name'] = soup.find('h1', class_='TextHeader').text

		promotion = soup.select('td.InformationBoxContents a[href^="?id=8&nr="]')
		if promotion:
			details['promotion'] = int(parse_qs(promotion[0]['href'])['nr'][0])

		parent_gimmick = ''
		gimmicks = soup.select('td.InformationBoxContents a[href^="?id=2&nr=%d&page=4&gimmick="]' % id)
		for gimmick in gimmicks:
			prev = gimmick.previous_sibling

			# They use &nbsp; in a.k.a. tag.
			if prev and prev == '  ':
				details['gimmicks'].append((parent_gimmick, gimmick.get_text()))
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

	def get(self, url, **kwargs):
		if self._last_scrape:
			sleeptime = max(0, 5 - (time.time() - self._last_scrape))
			time.sleep(sleeptime)

		self._last_scrape = time.time()
		return self._requests.get(url, **kwargs)
