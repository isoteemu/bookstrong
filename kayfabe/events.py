#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import date

'''
	Notable events
'''

wwe_events = {
	"WrestleMania III":							date(1987,3,29),
	'New Generation':							date(1993,1,11),
	'Stampede 1994':							date(1994,4,17),
	'Monday Night Wars':						date(1995,9,4),
	'Survivor Series 1995':						date(1995,11,19),
	'NWO':										date(1996,7,7),
	'Canadian Stampede':						date(1997,7,6),
	'Attitude Era':								date(1997,11,9),
	'Montreal Screwjob':						date(1997,11,27),
	'ECW Heat Wave 1998':						date(1998,8,2),
	'Royal Rumble 2000':						date(2000,1,23),
#	'No Way Out 2001':							date(2001,2,25),
	'WrestleMania X-Seven':						date(2001,4,1),
	'One Night Stand 2005':						date(2005,6,12),
	'Backlash 2009':							date(2009,4,26),
	#'Pipe Bomb':								date(2011,6,27),
	'Money in the Bank 2011':					date(2011,7,17),
	'Extreme Rules 2012':						date(2012,4,29),
	'Shield':									date(2012,11,18),
	'SummerSlam 2013':							date(2013,8,18),
	'#DivasRevolutio':							date(2015,7,13),
}

njpw_events = {
	'Super J Cup':								date(2009,12,23),
	'Super Jr. Tag Tournament':					date(2014,11,3),
	'World Tag League':							date(2014,12,7),
	'New Japan Cup'	:							date(2015,3,15),
	'Best of the Super Juniors':				date(2015,6,7),
	'G1 Climax 25':								date(2015,8,16),
}

events = {
	1: wwe_events,
	7: njpw_events
}
