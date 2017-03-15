#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from kayfabe import session
from kayfabe.models import *
from kayfabe.scrapper import cagematchnet

from sqlalchemy.orm import exc

import logging

class ModelProxy():
    force_update = False
    model = None

class WrestlerProxy(ModelProxy):
    ''' Proxy for wrestler info scraping '''

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
            promotion_data = cagematchnet.promotion(data['promotion'])
            promotion = Promotion(cm_id=data['promotion'], name=promotion_data['name'],
                                  abbrevation=promotion_data['abbrevation'])

            logging.debug("Creating new Promotion: %s", promotion)
            session.add(promotion)

        return promotion

    def name(self, force_update=None):
        if force_update is None:
            force_update = self.force_update

        wrestler = self.wrestler

        if not wrestler.name or force_update:
            data = self.cagematch(wrestler.nr)
            wrestler.name = data.get('name', wrestler.name)

        return wrestler.name

    def gimmicks(self, force_update=None):
        ''' Get wrestler gimmicks '''
        if force_update is None:
            force_update = self.force_update

        wrestler = self.wrestler

        if not wrestler.gimmicks or force_update:
            data = self.cagematch(wrestler.nr)

            for gimmick in data['gimmicks']:

                if type(gimmick) == str:
                    parent = None
                else:
                    parent, gimmick = gimmick

                gimmick = gimmick.strip()

                try:
                    gmk = session.query(Gimmick).filter_by(gimmick=gimmick,
                                                           wrestler_nr=wrestler.nr).one()
                except exc.NoResultFound:
                    logging.debug('Creating new gimmick "%s"', gimmick)
                    gmk = Gimmick(gimmick=gimmick)
                    wrestler.gimmicks.append(gmk)

                if parent:
                    alias_of = session.query(Gimmick).filter_by(gimmick=parent,
                                                                wrestler_nr=wrestler.nr).one()

                    gmk.alias_of = alias_of.id

                if gmk.gimmick == wrestler.name:
                    gmk.primary = True

            ## TODO: Remove dead ones 
        return wrestler.gimmicks
