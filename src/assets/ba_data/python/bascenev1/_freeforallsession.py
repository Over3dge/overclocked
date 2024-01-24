# Released under AGPL-3.0-or-later. See LICENSE for details.
#
# This file incorporates work covered by the following permission notice:
#   Released under the MIT License. See LICENSE for details.
#
"""Functionality related to free-for-all sessions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import time

from era import gdata
import babase
import _bascenev1
from era.utils import inform
from bascenev1._multiteamsession import MultiTeamSession

if TYPE_CHECKING:
    import bascenev1


class FreeForAllSession(MultiTeamSession):
    """bascenev1.Session type for free-for-all mode games.

    Category: **Gameplay Classes**
    """

    use_teams = False
    use_team_colors = False
    _playlist_selection_var = 'Free-for-All Playlist Selection'
    _playlist_randomize_var = 'Free-for-All Playlist Randomize'
    _playlists_var = 'Free-for-All Playlists'

    def get_ffa_point_awards(self, spl: list | None = None) -> dict[int, int]:
        """Return the number of points awarded for different rankings.

        This is based on the current number of players.
        """
        spld = spl or self.sessionplayers
        point_awards: dict[int, int]
        if len(spld) == 1:
            point_awards = {}
        elif len(spld) == 2:
            point_awards = {0: 6}
        elif len(spld) == 3:
            point_awards = {0: 6, 1: 3}
        elif len(spld) == 4:
            point_awards = {0: 8, 1: 4, 2: 2}
        elif len(spld) == 5:
            point_awards = {0: 8, 1: 4, 2: 2}
        elif len(spld) == 6:
            point_awards = {0: 8, 1: 4, 2: 2}
        else:
            point_awards = {0: 8, 1: 4, 2: 2, 3: 1}
        return point_awards

    def __init__(self) -> None:
        babase.increment_analytics_count('Free-for-all session start')
        super().__init__()

    def _switch_to_score_screen(self, results: bascenev1.GameResults) -> None:
        # pylint: disable=cyclic-import
        from efro.util import asserttype
        from bascenev1lib.activity.multiteamvictory import (
            TeamSeriesVictoryScoreScreenActivity,
        )
        from bascenev1lib.activity.freeforallvictory import (
            FreeForAllVictoryScoreScreenActivity,
        )
        from bascenev1lib.activity.drawscore import DrawScoreScreenActivity

        winners = results.winnergroups

        # If there's multiple players and everyone has the same score,
        # call it a draw.
        if len(self.sessionplayers) > 1 and len(winners) < 2:
            self.setactivity(
                _bascenev1.newactivity(
                    DrawScoreScreenActivity, {'results': results}
                )
            )
        else:
            # Award different point amounts based on number of players.
            point_awards = self.get_ffa_point_awards()
            for i, winner in enumerate(winners):
                for team in winner.teams:
                    points = point_awards[i] if i in point_awards else 0
                    team.customdata['previous_score'] = team.customdata['score']
                    team.customdata['score'] += points

            if babase.app.classic and babase.app.classic.server:
                cidl = []
                pidl = []
                for i, winner in enumerate(winners):
                    for team in winner.teams:
                        sp = team.players[0]
                        if (sp.get_v1_account_id() or 'anon') not in pidl:
                            cidl.append(sp.inputdevice.client_id)
                            pidl.append(sp.get_v1_account_id() or 'anon')
                spoint_award = self.get_ffa_point_awards(cidl)

                for i, pid in enumerate(pidl):
                    spoints = spoint_award[i] * 2 if i in spoint_award else 0
                    if spoints > 0:
                        topsdatapath = gdata.getpath('stops')
                        topsdata = gdata.load(topsdatapath) or {}
                        topsdata.setdefault('end', 0)
                        if topsdata['end'] < time.time():
                            tl = list(topsdata.keys())
                            tl.remove('end')
                            for y, toppid in enumerate(tl[:3]):
                                tplrdatapath = gdata.getpath('gstats/' + toppid)
                                tplrdata = gdata.load(tplrdatapath) or {}
                                tplrdata.setdefault('spoints', 0)
                                match y:
                                    case 0:
                                        tplrdata['spoints'] += 10000
                                    case 1:
                                        tplrdata['spoints'] += 5000
                                    case 2:
                                        tplrdata['spoints'] += 2500
                                gdata.write(tplrdatapath, tplrdata)
                            topsdata = {'end': time.time() + 2592000}
                        topsdata.setdefault(pid, 0)
                        topsdata[pid] += spoints
                        topsdata = dict(sorted(
                            topsdata.items(), key=lambda x: x[1], reverse=True
                        ))
                        gdata.write(topsdatapath, topsdata)
                        leaguesdatapath = gdata.getpath('gleagues')
                        leaguesdata = gdata.load(leaguesdatapath) or {}
                        leaguesdata.setdefault('end', 0)
                        leaguesdata.setdefault('leagues',
                                               [{}, {}, {}, {}, {}, {}])
                        if leaguesdata['end'] < time.time():
                            nleaguesdata = {'end': time.time() + 604800,
                                            'leagues': [{}, {}, {}, {}, {}, {}]}
                            for l, league in enumerate(leaguesdata['leagues']):
                                lplrs = list(league.keys())
                                tlp = len(lplrs)
                                for lpi, lplr in enumerate(lplrs, 1):
                                    if l != 0 and lpi / tlp < 0.5:
                                        nleaguesdata['leagues'][l - 1][lplr] = 0
                                    elif l != 5 and lpi / tlp > 0.5:
                                        nleaguesdata['leagues'][l + 1][lplr] = 0
                                    else:
                                        nleaguesdata['leagues'][l][lplr] = 0
                            nleaguesdata['leagues'][5] = {}
                            leaguesdata = nleaguesdata
                            gdata.write(leaguesdatapath, leaguesdata)
                        le = 5
                        for lei, league in enumerate(leaguesdata['leagues']):
                            if pid in list(league.keys()):
                                le = lei
                                break
                        leaguesdata['leagues'][le].setdefault(pid, 0)
                        leaguesdata['leagues'][le][pid] += spoints
                        leaguesdata['leagues'][le] = dict(
                            sorted(leaguesdata['leagues'][le].items(),
                                   key=lambda x: x[1], reverse=True)
                        )
                        gdata.write(leaguesdatapath, leaguesdata)
                        plrdatapath = gdata.getpath('gstats/' + pid)
                        plrdata = gdata.load(plrdatapath) or {}
                        plrdata.setdefault('items', [])
                        spoints *= (2 if any(o.split('␟')[0] == 'vip@other'
                                             for o in plrdata['items']) else 1)
                        plrdata.setdefault('spoints', 0)
                        plrdata.setdefault('lang', None)
                        plrdata['spoints'] += spoints
                        gdata.write(plrdatapath, plrdata)
                        inform('youEarnedSPoints', 'success', cidl[i],
                               plrdata['lang'], [str(spoints)])
                        plrdata.setdefault('equipped', [])
                        if len(plrdata['items'] + plrdata['equipped']) == 0:
                            inform('shopGuide', 'error', cidl[i],
                                   plrdata['lang'])

            series_winners = [
                team
                for team in self.sessionteams
                if team.customdata['score'] >= self._ffa_series_length
            ]
            series_winners.sort(
                reverse=True,
                key=lambda t: asserttype(t.customdata['score'], int),
            )
            if len(series_winners) == 1 or (
                len(series_winners) > 1
                and series_winners[0].customdata['score']
                != series_winners[1].customdata['score']
            ):
                self.setactivity(
                    _bascenev1.newactivity(
                        TeamSeriesVictoryScoreScreenActivity,
                        {'winner': series_winners[0]},
                    )
                )
            else:
                self.setactivity(
                    _bascenev1.newactivity(
                        FreeForAllVictoryScoreScreenActivity,
                        {'results': results},
                    )
                )
