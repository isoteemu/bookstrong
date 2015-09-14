#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, SmallInteger, String, Boolean, Date, ForeignKey
from sqlalchemy.orm import relationship, backref

from sqlalchemy.orm import sessionmaker
from sqlalchemy import func

import pandas as pd

from . import Session, session

Base = declarative_base()

class Wrestler(Base):
	__tablename__ = 'wrestlers'

	nr = Column(Integer, primary_key=True)
	name = Column(String)
	promotion_id = Column(Integer, ForeignKey('promotions.cm_id'))

	pwi = Column(Integer)
	gimmicks = relationship("Gimmick", backref='wrestler')

	def __repr__(self):
		return "<Wrestler(name='{name}', pwi={pwi}, nr={cm})>".format(name=self.name, pwi=self.pwi, cm=self.nr)

class Promotion(Base):
	__tablename__ = 'promotions'
	
	cm_id = Column(Integer, primary_key=True)
	name = Column(String)
	abbrevation = Column(String)

	wrestlers = relationship("Wrestler", backref='promotion')

	def __repr__(self):
		return "<Promotion(promotion='{name}', id={id})>".format(name=self.name, id=self.cm_id)

class Gimmick(Base):
	__tablename__ = 'gimmicks'

	id = Column(Integer, primary_key=True)
	wrestler_nr = Column('wrestler_cm', Integer, ForeignKey('wrestlers.nr'))
	gimmick = Column(String)
	primary = Column(Boolean)
	alias_of = Column(Integer, ForeignKey('gimmicks.id'))

	def __repr__(self):
		return "<Gimmick(gimmick='{gimmick}', id={id}, wrestler_nr={cm})>".format(gimmick=self.gimmick, id=self.id, cm=self.wrestler_cm)

class Match(Base):
	__tablename__ = 'matches'

	id = Column(Integer, primary_key=True)
	event_id = Column(Integer, ForeignKey('matches_event.id'))
	event_name = Column(String)
	type = Column(String)
	date = Column(Date)
	type_desc = Column(String)
	resolution = Column(String)

	wrestlers = relationship("MatchWrestler", backref='match')
	titles =  relationship("MatchTitle")
	promotions = relationship("MatchPromotion", backref='match')

class MatchWrestler(Base):
	__tablename__ = 'matches_wrestlers'

	id = Column(Integer, primary_key=True)
	match_id = Column(Integer, ForeignKey('matches.id'))
	wrestler_id = Column(Integer, ForeignKey('wrestlers.nr'))
	gimmick_id = Column(Integer, ForeignKey('gimmicks.id'))

	wrestler = relationship("Wrestler")
	resolution = Column(SmallInteger)
	gimmick = relationship("Gimmick")

	WINNER = 1
	LOSER = -1
	NC = 0

	def __repr__(self):
		name = ''
		try:
			''' We might not know him/her '''
			name = self.wrestler.name
		except:
			pass
		return "<MatchWrestler(wrestler_id='{wid}' wrestler_name='{name}', match_id={mid}, resolution={r})>".format(wid=self.wrestler_id, mid=self.match_id, r=self.resolution, name=name)


class MatchPromotion(Base):
	__tablename__ = 'matches_promotions'

	id = Column(Integer, primary_key=True)

	match_id = Column(Integer, ForeignKey('matches.id'))
	promotion_id = Column(Integer, ForeignKey('promotions.cm_id'))

class MatchEvent(Base):
	__tablename__ = 'matches_event'

	id = Column(Integer, primary_key=True)
	name = Column(String)
	date = Column(Date)

	matches = relationship("Match", backref='event')

class MatchTitle(Base):
	__tablename__ = 'matches_titles'

	id = Column(Integer, primary_key=True)
	match_id = Column(Integer, ForeignKey('matches.id'))
	title_id = Column(Integer) # TODO ForeignKey('titles.id')
	change = Column(Boolean)

class Score(Base):
	__tablename__ = 'scores'
	id = Column(Integer, primary_key=True)
	match_id = Column(Integer, ForeignKey('matches.id'))
	wrestler_nr = Column(Integer, ForeignKey('wrestlers.nr'))
	score = Column(Integer)

	wrestler = relationship("Wrestler")
	match = relationship("Match")





def get_matches(wrestler):
	'''
		Get wrestler matches scores as pandas.Series(), indexed by date
	'''

	matches = session.query(Score).filter_by(wrestler_nr=wrestler).join(Match).order_by(Match.date)

	start_date = session.query(func.min(Match.date)).join(Score).filter_by(wrestler_nr=wrestler).one()[0]
	end_date =   session.query(func.max(Match.date)).join(Score).filter_by(wrestler_nr=wrestler).one()[0]

	rng = pd.date_range(start=start_date, end=end_date, freq='D')
	s = pd.Series(index=rng)

	for match in matches.all():
		old_score = s[match.match.date]
		score = match.score

		# Calculate combined score. Is shit.
		if not pd.isnull(old_score):
			score = ( old_score + score ) / 2

		s.set_value(match.match.date,  score)

	return s




