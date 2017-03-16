#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from kayfabe import session, BASE_SCORE
from kayfabe.models import *

from kayfabe.scrapper import cagematchnet, ProWrestlingWiki
from kayfabe.Image import crop_thumb

from kayfabe.proxy import WrestlerProxy
from kayfabe.view import get_image_path

import logging, sys


if __name__ == '__main__':
    import argparse

    cmdline = argparse.ArgumentParser(description='Find wrestler info from different datasources.')

    cmdline.add_argument('wrestler_id', help='Wrestler ID number.',
                         type=int, nargs='?')

    cmdline.add_argument('--name', help="Select wrestler by name.")

    cmdline.add_argument('--add', action='store_true', default=False, help="Add wrestler.")

    cmdline.add_argument('--debug', help='Debug', action='store_true')
    cmdline.add_argument('--update', help='Force updating info', action='store_true')

    args = cmdline.parse_args()

    if args.debug:
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    else:
        logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    force_update = args.update

    if args.add:

        if args.wrestler_id:
            wrestler = Wrestler(nr=args.wrestler_id)
        elif args.name:
            _wrestlers = cagematchnet.search(args.name.strip())
            if len(_wrestlers) == 1:
                w_nr = list(_wrestlers.keys())[0]
                wrestler = Wrestler(nr=w_nr)
                logging.info("Found Wrestler %s from cagematch.net" % w_nr)
            else:
                logging.error('Wrong ammount of results %i', len(_wrestlers))
                sys.exit(2)
        else:
            print('Missing name or id.')
            sys.exit(2)

        session.add(wrestler)
        logging.info('Adding wrestler %s with id %i' % (wrestler.name, wrestler.nr))

    elif args.name:
        wrestler = session.query(Wrestler).filter_by(name=args.name).one()
    else:
        wrestler = session.query(Wrestler).get(args.wrestler_id)


    proxy = WrestlerProxy(wrestler)
    proxy.force_update = force_update

    print("Name: %s" % proxy.name(force_update))
    print("Id: %s" % wrestler.nr)

    ringnames = [g.gimmick for g in proxy.gimmicks(force_update)]
    print("Ringnames: %s" % ', '.join(ringnames))

    print("Promotion: %s" % proxy.promotion(force_update))


    pww = ProWrestlingWiki()
    pww.search_image(proxy.wrestler)


    picture = get_image_path(wrestler)
    print('Picture: %s' % picture)

    if (args.add or args.update) and ( session.dirty or session.new ):
        session.commit()
