from kayfabe.models import *
from kayfabe import session

import operator

def get_biggest_cheater(from_date, to_date) -> Wrestler:
    print(from_date, to_date)
    """ Fetch biggest DQ loser. """
    # Note: case sensitive
    resolutions = ['DQ', 'Count Out']

    q = session.query(MatchWrestler).filter(MatchWrestler.resolution==MatchWrestler.LOSER).\
        join(Match).filter(Match.date >= from_date).filter(Match.date <= to_date).\
        filter(Match.resolution.in_(resolutions))

    counts = {}

    for match in q.all():
        try:
            wrestler = match.wrestler.nr
            ended = match.match.resolution
            if ended == None:
                continue
            counts.setdefault(wrestler, 0)
            counts[wrestler] += 1
        except AttributeError:
            # Participiant we dont track, ignore.
            pass

    s = sorted(counts.items(), key=operator.itemgetter(1), reverse=True)
    nr = s[0][0]
    return session.query(Wrestler).get(nr)

def match_ending_stats(wrestler: Wrestler, from_date, to_date):
    stats = {}
    q = session.query(MatchWrestler).filter(MatchWrestler.wrestler_id==wrestler.nr).join(Match).\
        filter(Match.date >= from_date).filter(Match.date <= to_date)

    for match in q.all():
        ended = match.match.resolution
        if not ended:
            ended = match.resolution
        stats.setdefault(ended, 0)
        stats[ended] += 1

    print(stats)
    return stats

