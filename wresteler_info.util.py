#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from kayfabe import session, BASE_SCORE
from kayfabe.models import *

from kayfabe.scrapper import cagematchnet, WikiData
from kayfabe.util import get_last_match

from kayfabe.proxy import WrestlerProxy
from kayfabe.view import get_image_path

import logging, sys

from sqlalchemy import asc, desc, func
from sqlalchemy.orm import exc


def get_wrassler(nr):
    try:
        wrestler = session.query(Wrestler).filter_by(nr=nr).one()
    except exc.NoResultFound:
        wrestler = Wrestler(nr=nr)
        session.add(wrestler)
    return wrestler


if __name__ == '__main__':
    import argparse

    cmdline = argparse.ArgumentParser(description='Find wrestler info from different datasources.')

    cmdline.add_argument('wrestler_id', help='Wrestler ID number.',
                         type=int, nargs='*')

    cmdline.add_argument('--name', help="Select wrestler by name.")

    cmdline.add_argument('--add', action='store_true', default=False, help="Add wrestler.")

    cmdline.add_argument('--debug', help='Debug', action='store_true')
    cmdline.add_argument('--update', help='Force updating info', action='store_true')
    cmdline.add_argument('--picture', help='Get picture.', action='store_true')

    args = cmdline.parse_args()

    if args.debug:
        logging.basicConfig(stream=open('log.txt', 'w'), level=logging.DEBUG)
    else:
        logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    logger = logging.getLogger(__name__)

    force_update = args.update

    wrestlers = []

    if args.wrestler_id:
        for nr in args.wrestler_id:
            wrestlers.append(get_wrassler(nr))

    elif args.name:
        try:
            wrestler = session.query(Wrestler).filter_by(name=args.name).one()
        except exc.NoResultFound:
            wrestler = None

        if wrestler:
            wrestlers.append(wrestler)
        else:
            _wrestlers = cagematchnet.search(args.name.strip())
            if len(_wrestlers) == 1:
                w_nr = list(_wrestlers.keys())[0]
                wrestlers.append(get_wrassler(w_nr))
                logger.info('Found Wrestler %s from cagematch.net', w_nr)
            else:
                logging.error('Wrong ammount of results %i', len(_wrestlers))
                sys.exit(2)

    else:
        wrestlers = session.query(Wrestler).filter(Wrestler.nr < 1000000).order_by(Wrestler.nr)

    if args.add or args.update:
        force_update = True

    for wrestler in wrestlers:

        proxy = WrestlerProxy(wrestler)
        proxy.force_update = force_update

        print("Id: %s" % wrestler.nr)
        print("Name: %s" % proxy.name(force_update))

        gimmicks = proxy.gimmicks(force_update)
        ringnames = [g.gimmick for g in gimmicks]
        print("Ringnames: %s" % ', '.join(ringnames))

        print("Promotion: %s" % proxy.promotion(force_update).name)

        try:
            print("Last match: %s" % get_last_match(wrestler).date)
        except:
            pass

        if args.picture:
            picture = get_image_path(wrestler)
            print('Picture: %s' % picture)

        if force_update:
            logger.debug("Storing")
            print('')
            session.commit()
