#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pandas as pd

from os.path import realpath

from .events import events
# TODO kasvata, captain new japan liian paska

BASE_SCORE=4000


if not 'DB_FILE' in globals():
	DB_FILE = realpath('%s/../../cagematch.sqlite3' % __file__)

engine = create_engine('sqlite:///%s' % DB_FILE, echo=False)

Session = sessionmaker()
Session.configure(bind=engine)

session = Session()
