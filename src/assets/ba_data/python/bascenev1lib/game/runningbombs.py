# ALL RIGHTS RESERVED. See COPYRIGHT_HOLDERS for details.
#
"""Defines a running-bombs mini-game."""

# Mod by Froshlee14
# Updated to api 7 by SEBASTIAN2059
# Updated to api 8 by Era0S

# ba_meta require api 8
# (see https://ballistica.net/wiki/meta-tag-system)

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import bascenev1 as bs
from bascenev1lib.actor.bomb import Bomb
from bascenev1lib.actor.bomb import BombFactory
from bascenev1lib.gameutils import SharedObjects
from bascenev1lib.actor.onscreentimer import OnScreenTimer

if TYPE_CHECKING:
    from typing import Any, Sequence, Optional, List, Type


class Player(bs.Player['Team']):
    """Our player type for this game."""

    def __init__(self) -> None:
        super().__init__()
        self.death_time: float | None = None


class Team(bs.Team[Player]):
    """Our team type for this game."""


# ba_meta export bascenev1.GameActivity
class RunningBombsGame(bs.TeamGameActivity[Player, Team]):
    """Minigame involving dodging falling bombs."""

    name = 'Running Bombs'
    description = 'Dodge the running bombs.'
    available_settings = [bs.BoolSetting('Epic Mode', default=False),
                          bs.BoolSetting('Random bombs spawn', default=True)]
    scoreconfig = bs.ScoreConfig(label='Survived',
                                 scoretype=bs.ScoreType.MILLISECONDS,
                                 version='B')

    # Print messages when players die (since its meaningful in this game).
    announce_player_deaths = True

    # Don't allow joining after we start
    # (would enable leave/rejoin tomfoolery).
    allow_mid_activity_joins = False

    # we're currently hard-coded for one map..
    @classmethod
    def get_supported_maps(cls, sessiontype: Type[bs.Session]) -> List[str]:
        return ['Football Stadium']

    # We support teams, free-for-all, and co-op sessions.
    @classmethod
    def supports_session_type(cls, sessiontype: Type[bs.Session]) -> bool:
        return (issubclass(sessiontype, bs.DualTeamSession)
                or issubclass(sessiontype, bs.FreeForAllSession))

    def __init__(self, settings: dict):
        super().__init__(settings)

        self._epic_mode = settings.get('Epic Mode', False)
        self._random_bombs_spawn = settings.get('Random bombs spawn', False)

        self._last_player_death_time: float | None = None
        self._meteor_time = 2.0
        self._timer: Optional[OnScreenTimer] = None

        # Some base class overrides:
        self.default_music = (bs.MusicType.EPIC if self._epic_mode
                              else bs.MusicType.SURVIVAL)
        self.slow_motion = self._epic_mode

        shared = SharedObjects.get()
        self.kill_bomb_region_material = bs.Material()
        self.kill_player_region_material = bs.Material()
        self.block_player_region_material = bs.Material()

        self.kill_bomb_region_material.add_actions(
            conditions=('they_have_material', BombFactory.get().bomb_material),
            actions=(('modify_part_collision', 'collide', True),
                     ('modify_part_collision', 'physical', False),
                     ('message', 'their_node', 'at_connect', bs.DieMessage())))

        self.kill_player_region_material.add_actions(
            conditions=('they_have_material', shared.player_material),
            actions=(('modify_part_collision', 'collide', True),
                     ('modify_part_collision', 'physical', False),
                     ('message', 'their_node', 'at_connect', bs.DieMessage()),
                     ('message', 'their_node', 'at_connect',
                      bs.ShouldShatterMessage()))
        )

        self.block_player_region_material.add_actions(
            conditions=('they_have_material', shared.player_material),
            actions=(('modify_part_collision', 'collide', True),
                     ('modify_part_collision', 'physical', True))
        )
        self.force_simple_themes = False

    def on_transition_in(self) -> None:
        super().on_transition_in()
        defs = self.map.defs
        bs.NodeActor(bs.newnode(
            'region',
            attrs={'position': defs.boxes['goal1'][0:3],
                   'scale': defs.boxes['goal1'][6:9],
                   'type': 'box',
                   'materials': [self.block_player_region_material]},
        )).autoretain()
        bs.NodeActor(bs.newnode(
            'region',
            attrs={'position': defs.boxes['goal2'][0:3],
                   'scale': defs.boxes['goal2'][6:9],
                   'type': 'box',
                   'materials': [self.kill_bomb_region_material,
                                 self.kill_player_region_material]}
        )).autoretain()
        for i in range(-11, 11):
            i /= 2
            light = bs.newnode('light', attrs={
                'position': (defs.boxes['goal2'][0], 0, i),
                'color': (1, 0, 0),
                'intensity': 2,
                'radius': 0.2,
                'height_attenuated': False,
            })

    def on_begin(self) -> None:
        super().on_begin()

        # Drop a wave every few seconds.. and every so often drop the time
        # between waves ..lets have things increase faster if we have fewer
        # players.
        delay = 5.0 if len(self.players) > 2 else 2.5
        if self._epic_mode:
            delay *= 0.25
        bs.timer(delay, self._decrement_meteor_time, repeat=True)

        # Kick off the first wave in a few seconds.
        delay = 3.0
        if self._epic_mode:
            delay *= 0.25
        bs.timer(delay, self._set_meteor_timer)

        self._timer = OnScreenTimer()
        self._timer.start()

        # Check for immediate end (if we've only got 1 player, etc).
        bs.timer(5.0, self._check_end_game)

    def on_player_leave(self, player: Player) -> None:
        # Augment default behavior.
        super().on_player_leave(player)

        # A departing player may trigger game-over.
        self._check_end_game()

    # overriding the default character spawning..
    def spawn_player(self, player: Player) -> bs.Actor:
        spaz = self.spawn_player_spaz(player)

        # Let's reconnect this player's controls to this
        # spaz but *without* the ability to attack or pick stuff up.
        spaz.connect_controls_to_player(
            enable_punch=False, enable_bomb=False, enable_pickup=False
        )

        # Also lets have them make some noise when they die.
        spaz.play_big_death_sound = True
        return spaz

    # Various high-level game events come through this method.
    def handlemessage(self, msg: Any) -> Any:
        if isinstance(msg, bs.PlayerDiedMessage):

            # Augment standard behavior.
            super().handlemessage(msg)

            curtime = bs.time()

            # Record the player's moment of death.
            # assert isinstance(msg.spaz.player
            msg.getplayer(Player).death_time = curtime

            # In co-op mode, end the game the instant everyone dies
            # (more accurate looking).
            # In teams/ffa, allow a one-second fudge-factor so we can
            # get more draws if players die basically at the same time.
            if isinstance(self.session, bs.CoopSession):
                # Teams will still show up if we check now.. check in
                # the next cycle.
                bs.pushcall(self._check_end_game)

                # Also record this for a final setting of the clock.
                self._last_player_death_time = curtime
            else:
                bs.timer(1.0, self._check_end_game)

        else:
            # Default handler:
            return super().handlemessage(msg)
        return None

    def _check_end_game(self) -> None:
        living_team_count = 0
        for team in self.teams:
            for player in team.players:
                if player.is_alive():
                    living_team_count += 1
                    break

        # In co-op, we go till everyone is dead.. otherwise we go
        # until one team remains.
        if isinstance(self.session, bs.CoopSession):
            if living_team_count <= 0:
                self.end_game()
        else:
            if living_team_count <= 1:
                self.end_game()

    def _set_meteor_timer(self) -> None:
        bs.timer((1.0 + 0.2 * random.random()) * self._meteor_time,
                 self._drop_bomb_cluster)

    def _drop_bomb_cluster(self) -> None:

        # Drop several bombs in series.
        delay = 0.0
        for _i in range(random.randrange(1, 3)):
            # Drop them somewhere within our bounds with velocity pointing
            # toward the opposite side.
            vel = (-20, 2, 0)
            bs.timer(delay, bs.Call(self._drop_bomb, vel))
            delay += 0.1
        self._set_meteor_timer()

    def _drop_bomb(self, velocity: Sequence[float]) -> None:
        x = [-5, -4.5, -4, -3.5, -3, -2.5, -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5,
             2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5]
        if self._random_bombs_spawn:
            pos = (13.4, 1, random.choice(x))
            Bomb(position=pos, velocity=velocity, bomb_type='normal',
                 blast_radius=1).autoretain()
        else:
            for i in x:
                pos = (13.4, 1, i)
                Bomb(position=pos, velocity=velocity, bomb_type='normal',
                     blast_radius=1).autoretain()

    def _decrement_meteor_time(self) -> None:
        if self._random_bombs_spawn:
            self._meteor_time = max(0.01, self._meteor_time * 0.8)
        else:
            self._meteor_time = max(0.01, self._meteor_time * 0.9)

    def end_game(self) -> None:
        cur_time = bs.time()
        assert self._timer is not None
        start_time = self._timer.getstarttime()

        # Mark death-time as now for any still-living players
        # and award players points for how long they lasted.
        # (these per-player scores are only meaningful in team-games)
        for team in self.teams:
            for player in team.players:
                survived = False

                # Throw an extra fudge factor in so teams that
                # didn't die come out ahead of teams that did.
                if player.death_time is None:
                    survived = True
                    player.death_time = cur_time + 1

                # Award a per-player score depending on how many seconds
                # they lasted (per-player scores only affect teams mode;
                # everywhere else just looks at the per-team score).
                score = int(player.death_time - self._timer.getstarttime())
                if survived:
                    score += 50  # A bit extra for survivors.
                self.stats.player_scored(player, score, screenmessage=False)

        # Stop updating our time text, and set the final time to match
        # exactly when our last guy died.
        self._timer.stop(endtime=self._last_player_death_time)

        # Ok now calc game results: set a score for each team and then tell
        # the game to end.
        results = bs.GameResults()

        # Remember that 'free-for-all' mode is simply a special form
        # of 'teams' mode where each player gets their own team, so we can
        # just always deal in teams and have all cases covered.
        for team in self.teams:

            # Set the team score to the max time survived by any player on
            # that team.
            longest_life = 0.0
            for player in team.players:
                assert player.death_time is not None
                longest_life = max(longest_life,
                                   player.death_time - start_time)

            # Submit the score value in milliseconds.
            results.set_team_score(team, int(1000.0 * longest_life))

        self.end(results=results)
