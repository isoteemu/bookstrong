#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging, sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from kayfabe.models import *
from kayfabe.scrapper import CageMatch, cagematchnet
from kayfabe import session

from random import randint
from time import strptime

import re

from bs4 import BeautifulSoup, NavigableString, Tag

from urllib.parse import urlparse, parse_qs

from datetime import date

from time import sleep

import argparse

def get_gimmick_id(id, gimmick):
    '''
        Get gimmick ID by gimmick name
    '''
    gimmick_query = session.query(Gimmick).filter_by(wrestler_nr=id, gimmick=gimmick)
    if gimmick_query.count() >= 1:
        return gimmick_query.first().id

def scrape_matches(wrestler_nr, match_offset=0):
    print('Processing %d:%d' % (wrestler_nr, match_offset))

    c_file = 'cache/matches-{wrestler}-{offset}.txt'.format(wrestler=wrestler_nr, offset=match_offset)

    try:
        page = open(c_file)
    except:
        page = cm.get('http://www.cagematch.net/?id=2&page=4', params={'nr': wrestler_nr, 's':match_offset}).text
        open(c_file, 'w').write(page)

    soup = BeautifulSoup(page)

    # First row is header
    rows = soup.select('div.TableContents tr')[1:]

    if len(rows) == 0:
        print('Zero rows, whaaaaat?')
        return

    for row in rows:

        cols = row.select('td')

        event_id = 0
        event_name = ''
        event_date = None
        promotions = []
        titles = []
        match_type_desc = None
        winners = []
        losers = []
        by = None
        event_type = 'Event'

        group = winners
        title_change = False

        winners_resolution = MatchWrestler.WINNER
        losers_resolution = MatchWrestler.LOSER

        event_date = date(*(strptime(cols[1].get_text().strip(),'%d.%m.%Y')[0:3]))

        for promotion in cols[2].select('a'):
            promotions.append(cm.id_from_url(promotion['href']))

        match_type = cols[3].find('span', class_='MatchType')
        if match_type:
            for cm_match_type in match_type.find_all('a'):
                title_nr = None
                try:
                    title_nr = cm.id_from_url(cm_match_type['href'])
                except:
                    title_name = cm_match_type.get_text().strip()
                    try:
                        title_name = parse_qs(cm_match_type['href'])['search'][0].strip()
                    except:
                        pass

                    try:
                        titles_search = cm.search_title(title_name)
                        print('Found titles:', titles_search)
                        if len(titles_search) == 1:
                            title_nr = titles_search[0]
                    except:
                        logging.warning('Exception while searching title.')

                if title_nr:
                    print('related title title_nr:', title_nr)
                    titles.append(title_nr)

            match_type_desc = match_type.get_text().strip().strip(':')

        card = cols[3].find('span', class_='MatchCard')

        event_details = cols[3].select('div.MatchEventLine a')[0]
        event_id = cm.id_from_url(event_details['href'])
        event_name = cols[3].select('div.MatchEventLine')[0].get_text()

        match_detail = card.get_text()
        if not re.search('(^|\\b|\s)defeat(:?s*)($|\\b|\s)', match_detail, flags=re.IGNORECASE):

            by = 'No Contest'
            winners_resolution = MatchWrestler.NC
            losers_resolution = MatchWrestler.NC

            # Try detecting how
            nc_how = re.search(r' - (.*)( [\(\[][\d:]+[\)\]]|$)', match_detail)
            if nc_how:
                nc_how.group(1)
                by = nc_how.group(1).strip()

            logging.info("No contest: '%s' (%s)" % (match_detail, by))

        for element in card:
            if isinstance(element,NavigableString):
                by_match = re.search('(^|\\b|\s)(by|-)\s+([\w\s]+)($|\\b)', element, flags=re.IGNORECASE)
                if by_match:
                    by = by_match.group(3).strip()

                elif re.search('(^|\s|\\b)defeat(:?s*)($|\s|\\b)', element, flags=re.IGNORECASE):
                    group = losers
                else:
                    if element.strip() not in ['and','[', ']', '(', ')', '&', ',', '-']:
                        logging.debug("NavigableString: '%s'" % element)

            elif element.name == 'a':
                parts = parse_qs(element['href'])
                if parts['?id'][0] == '2' and parts['nr']:
                    group.append((int(parts['nr'][0]), parts['name'][0].strip()))

        event_type = cols[4].get_text()

        if cols[3].select('.MatchTitleChange'):
            title_change = True

        print(event_id, event_name, event_date, promotions, event_type, match_type_desc, winners, 'vs.', losers, 'by', by, titles, '(%s)' % title_change)

        '''
            Find existing matces.
            First, retieve approximation of suitable matches, and later check if it
            might be one we are just processing.
        '''
        
        existing_match = False
        winner_list = [i[0] for i in winners]
        loser_list = [i[0] for i in losers]

        participiant_list = winner_list + loser_list

        event_matches = session.query(Match.id).filter_by(
            event_id=event_id, type=event_type, date=event_date, resolution=by
        ).join(MatchWrestler).filter_by(wrestler_id=wrestler_nr).distinct('Match.id')

        ''' Loop throug all participiants, and check for correct resolution. '''
        for (match_id,) in event_matches.all():
            match_wrestlers = session.query(MatchWrestler).filter_by(
                match_id=match_id
            )

            if len(participiant_list) != match_wrestlers.count():
                print('DIFFERENT MATCH, DIFFERENT COUNT')
                continue

            existing_match = True
            for wrestler in match_wrestlers.all():
                ''' check for correct resolution '''
                if wrestler.resolution >= MatchWrestler.NC and wrestler.wrestler_id not in winner_list:
                    existing_match = False;
                    break
                elif wrestler.resolution < MatchWrestler.NC and wrestler.wrestler_id not in loser_list:
                    existing_match = False;
                    break

            if existing_match == True:
                break

        if existing_match == True:
            logging.info("Match '%s' exists, skipping" % event_name)
            print('!!! EXISTING MATCH')
            continue

        ''' End of existing match checks ... '''

        match = Match(
            event_id=event_id,
            event_name=event_name,
            date=event_date,
            type=event_type,
            type_desc=match_type_desc
        )

        if by:
            match.resolution = by

        session.add(match)

        for (wrestler_id, gimmick) in winners:
            match.wrestlers.append(
                MatchWrestler(
                    wrestler_id=wrestler_id,
                    gimmick_id=get_gimmick_id(wrestler_id, gimmick),
                    resolution=winners_resolution
                )
            )
        for (wrestler_id, gimmick) in losers:
            match.wrestlers.append(
                MatchWrestler(
                    wrestler_id=wrestler_id,
                    gimmick_id=get_gimmick_id(wrestler_id, gimmick),
                    resolution=losers_resolution
                )
            )

        # Promotion for match
        for promotion in promotions:
            match.promotions.append(
                MatchPromotion(promotion_id=promotion)
            )

        for title in titles:
            match.titles.append(
                MatchTitle(title_id=title, change=title_change)
            )

        ## TODO: Add event?

    if len(rows) == 100:
        return scrape_matches(wrestler_nr, match_offset + 100)

    return




if __name__ == '__main__':

    cmdline = argparse.ArgumentParser(description='Find wrestler matches from cagematch.')

    cmdline.add_argument('wrestler_id', help='Wrestler ID number[s].',
                            type=int, nargs='*')
    cmdline.add_argument('--debug', help='Debug', action='store_true')

    args = cmdline.parse_args()

    if args.debug:
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    cm = cagematchnet

    # HACK
    #workers = session.query(Wrestler).filter(Wrestler.nr < 1000000).filter(Wrestler.pwi == None).order_by(Wrestler.nr)
    workers = session.query(Wrestler).filter(Wrestler.nr.in_(args.wrestler_id))

    print("Wrestler to process:", workers.count())

    #workers = [session.query(Wrestler).get(12698)]

    i = 1
    for worker in workers.all():
        print('Processing wrestler #', i, worker.name)

        scrape_matches(worker.nr)

        ''' Less than 100 rows, break '''
        print('Processed wrestler #', i, worker.name)
        i = i +1

        if session.dirty or session.new:
            session.commit()

print("DONE")
    #print(cols)
