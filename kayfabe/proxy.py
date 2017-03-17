#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from kayfabe import session
from kayfabe.models import *
from kayfabe.scrapper import WikiData, cagematchnet

from sqlalchemy.orm import exc

import logging
logger = logging.getLogger(__name__)

class ModelProxy():
    force_update = False

class WrestlerProxy(ModelProxy):
    ''' Proxy for wrestler info scraping. 
    TODO: Move into setter/getter
    '''

    _cagematch = None
    wrestler = None
    force_update = False

    def __init__(self, wrestler):
        ''' Create wrestler proxy '''
        self.wrestler = wrestler
        # TODO: Check if wrestler is dirty, or hasn't been updated for a while

    def cagematch(self, wrestler):
        '''
            Fetch wrestler info from cagematch
        '''
        if not self._cagematch:
            self._cagematch = cagematchnet.wrestler(wrestler)
        return self._cagematch

    def promotion(self, force_update=None):
        ''' Get wrestler promotion '''

        if force_update is None:
            force_update = self.force_update

        wrestler = self.wrestler

        if wrestler.promotion_id is None or force_update:

            data = self.cagematch(wrestler.nr)

            if data['promotion'] is None:
                data['promotion'] = 0

            wrestler.promotion = self._get_promotion(data['promotion'])

        return wrestler.promotion

    def _get_promotion(self, promotion_id):
        ''' Get promotion. Create new if necessary '''

        try:
            promotion = session.query(Promotion).get(promotion_id)
        except exc.NoResultFound:
            promotion = None
            pass

        if not promotion:
            promotion_data = cagematchnet.promotion(promotion_id)
            promotion = Promotion(cm_id=promotion_id, name=promotion_data['name'],
                                  abbrevation=promotion_data['abbrevation'])

            logger.debug("Creating new Promotion: %s", promotion)
            session.add(promotion)

        return promotion

    def name(self, force_update=None):
        if force_update is None:
            force_update = self.force_update

        wrestler = self.wrestler

        if not wrestler.name or force_update:
            data = self.cagematch(wrestler.nr)
            wrestler.name = data.get('name', wrestler.name).strip()

            # Causes -sometimes- memory violation on my python3.6m1
            '''
            gmk = self._gimmick(wrestler.name, wrestler)
            gmk.primary = True
            '''
            wd_name = self._wikidata_name(wrestler)
            if wd_name:
                wrestler.name = wd_name
                logger.debug('Set name from WikiData: %s', wd_name)

        return wrestler.name

    def _wikidata_name(self, wrestler: Wrestler):
        ''' Search wikidata for wrestler real name. '''
        wd_name = None
        try:
            data = WikiData().search_wrestler(wrestler.name)
            wd_name = data.get('labels', {}).get('en', {}).get('value', None).strip()
            logger.debug("Found name from WikiData: %s", wd_name)
        except (KeyError, AttributeError):
            pass

        return wd_name

    def _gimmick(self, gimmick: str, wrestler: Wrestler) -> Gimmick:
        logger.debug("Looking for gimmick %s", gimmick)
        '''Return gimmick model. Create one if necessary.'''
        try:
            gmk = session.query(Gimmick).filter_by(gimmick=gimmick, wrestler_nr=wrestler.nr).one()
        except exc.NoResultFound:
            logger.debug('Creating new gimmick "%s"', gimmick)
            gmk = Gimmick(gimmick=gimmick, wrestler_nr=wrestler.nr)

            wrestler.gimmicks.append(gmk)
            session.add(gmk)

        return gmk

    def gimmicks(self, force_update=None):
        ''' Get wrestler gimmicks '''
        if force_update is None:
            force_update = self.force_update

        wrestler = self.wrestler

        if not wrestler.gimmicks or force_update:

            data = self.cagematch(wrestler.nr)

            for gimmick in data['gimmicks']:
                logger.debug("Cagematch gimmick: %s", gimmick)

                if type(gimmick) == str:
                    parent = None
                else:
                    parent, gimmick = gimmick
                    parent = parent.strip()

                gimmick = gimmick.strip()

                gmk = self._gimmick(gimmick, wrestler)

                if parent:
                    alias_of = self._gimmick(parent, wrestler)

                    gmk.alias_of = alias_of.id

                if gmk.gimmick == wrestler.name:
                    gmk.primary = True

            ## TODO: Remove dead ones 

        return wrestler.gimmicks
