# Released under AGPL-3.0-or-later. See LICENSE for details.
#
# This file incorporates work covered by the following permission notice:
#   Released under the MIT License. See LICENSE for details.
#
"""Functionality related to teams sessions."""
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


class DualTeamSession(MultiTeamSession):
    """bascenev1.Session type for teams mode games.

    Category: **Gameplay Classes**
    """

    # Base class overrides:
    use_teams = True
    use_team_colors = True

    _playlist_selection_var = 'Team Tournament Playlist Selection'
    _playlist_randomize_var = 'Team Tournament Playlist Randomize'
    _playlists_var = 'Team Tournament Playlists'

    def __init__(self) -> None:
        babase.increment_analytics_count('Teams session start')
        super().__init__()

    def _switch_to_score_screen(self, results: bascenev1.GameResults) -> None:
        # pylint: disable=cyclic-import
        from bascenev1lib.activity.multiteamvictory import (
            TeamSeriesVictoryScoreScreenActivity,
        )
        from bascenev1lib.activity.dualteamscore import (
            TeamVictoryScoreScreenActivity,
        )
        from bascenev1lib.activity.drawscore import DrawScoreScreenActivity

        winnergroups = results.winnergroups

        # If everyone has the same score, call it a draw.
        if len(winnergroups) < 2:
            self.setactivity(_bascenev1.newactivity(DrawScoreScreenActivity))
        else:
            winner = winnergroups[0].teams[0]
            winner.customdata['score'] += 1

            if babase.app.classic and babase.app.classic.server:
                cidl = []
                pidl = []
                for plr in winner.players:
                    if (plr.get_v1_account_id() or 'anon') not in pidl:
                        cidl.append(plr.inputdevice.client_id)
                        pidl.append(plr.get_v1_account_id() or 'anon')
                lteam = None
                for team in self.sessionteams:
                    if team is not winner:
                        lteam = team
                if any((plr.get_v1_account_id() or 'anon') not in pidl
                       for plr in lteam.players):
                    for i, pid in enumerate(pidl):
                        spoints = 12
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

            # If a team has won, show final victory screen.
            if winner.customdata['score'] >= (self._series_length - 1) / 2 + 1:
                self.setactivity(
                    _bascenev1.newactivity(
                        TeamSeriesVictoryScoreScreenActivity,
                        {'winner': winner},
                    )
                )
            else:
                self.setactivity(
                    _bascenev1.newactivity(
                        TeamVictoryScoreScreenActivity, {'winner': winner}
                    )
                )
