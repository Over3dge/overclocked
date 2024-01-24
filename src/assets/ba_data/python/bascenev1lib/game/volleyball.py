# ALL RIGHTS RESERVED. See COPYRIGHT_HOLDERS for details.
#
# Volleyball (final)

# Made by your friend: Freaku


# Join BCS:
# https://discord.gg/ucyaesh


# My GitHub:
# https://github.com/Freaku17/BombSquad-Mods-byFreaku


# CHANGELOG:
"""
## 2021
- Fixed Puck's mass/size/positions/texture/effects
- Fixed Goal positions
- Better center wall
- Added 1 more map
- Added more customisable options
- Map lights locators are now looped
- Merged map & minigame in one file
- Puck spawns according to scored team
- Also puck now spawns in airrr
- Server support added :)
- Fixed **LOTS** of errors/bugs

## 2022
- Code cleanup
- More accurate Goal positions
"""


# ba_meta require api 8

from __future__ import annotations

from typing import TYPE_CHECKING

import bascenev1 as bs
from bascenev1lib.actor.playerspaz import PlayerSpaz
from bascenev1lib.actor.scoreboard import Scoreboard
from bascenev1lib.actor.powerupbox import PowerupBoxFactory
from bascenev1lib.actor.bomb import BombFactory
from bascenev1lib.gameutils import SharedObjects
from bascenev1lib.game.hockey import (HockeyGame, PuckDiedMessage, Player, Team,
                                      Puck)

if TYPE_CHECKING:
    from typing import Any, Sequence


class Ball(bs.Actor):
    """Ball. but for volleyball"""

    def __init__(self, position: Sequence[float] = (0.0, 1.0, 0.0)):
        super().__init__()
        shared = SharedObjects.get()
        activity = self.getactivity()

        # Spawn just above the provided point.
        self._spawn_pos = (position[0], position[1] + 1.05, position[2])
        self.last_players_to_touch: dict[int, Player] = {}
        self.scored = False
        assert activity is not None
        assert isinstance(activity, VolleyBallGame)
        pmats = [shared.object_material, activity.puck_material]
        self.node = bs.newnode('prop',
                               delegate=self,
                               attrs={
                                   'mesh': activity.puck_mesh,
                                   'color_texture': activity.puck_tex,
                                   'body': 'sphere',
                                   'reflection': 'soft',
                                   'reflection_scale': [0.2],
                                   'shadow_size': 0.6,
                                   'mesh_scale': 0.4,
                                   'body_scale': 1.07,
                                   'is_area_of_interest': True,
                                   'position': self._spawn_pos,
                                   'materials': pmats,
                               })

        # Since it rolls on spawn, lets make gravity
        # to 0, and when another node (bomb/spaz)
        # touches it. It'll act back as our normie puck!
        bs.animate(self.node, 'gravity_scale',
                   {0: -0.1, 0.2: 1 * self.activity.gravity_mult}, False)
        # When other node touches, it realises its new gravity_scale

    def handlemessage(self, msg: Any) -> Any:
        if (isinstance(msg, bs.DieMessage)
            or isinstance(msg, bs.OutOfBoundsMessage)
                or isinstance(msg, bs.HitMessage)):
            Puck.handlemessage(self, msg)
        else:
            super().handlemessage(msg)


# ba_meta export bascenev1.GameActivity
class VolleyBallGame(bs.TeamGameActivity[Player, Team]):
    name = 'Volleyball'
    description = 'Score some goals.\nby \ue048Freaku'
    available_settings = [
        bs.IntSetting(
            'Score to Win',
            min_value=1,
            default=1,
            increment=1,
        ),
        bs.IntChoiceSetting(
            'Time Limit',
            choices=[
                ('None', 0),
                ('1 Minute', 60),
                ('2 Minutes', 120),
                ('5 Minutes', 300),
                ('10 Minutes', 600),
                ('20 Minutes', 1200),
            ],
            default=0,
        ),
        bs.FloatChoiceSetting(
            'Respawn Times',
            choices=[
                ('Shorter', 0.25),
                ('Short', 0.5),
                ('Normal', 1.0),
                ('Long', 2.0),
                ('Longer', 4.0),
            ],
            default=1.0,
        ),
        bs.BoolSetting('Epic Mode', True),
        bs.BoolSetting('Icy Floor', True),
        bs.BoolSetting('Disable Punch', False),
        bs.BoolSetting('Disable Bombs', False),
        bs.BoolSetting('Enable Bottom Credits', True),
    ]
    default_music = bs.MusicType.HOCKEY

    @classmethod
    def supports_session_type(cls, sessiontype: type[bs.Session]) -> bool:
        return issubclass(sessiontype, bs.DualTeamSession)

    @classmethod
    def get_supported_maps(cls, sessiontype: type[bs.Session]) -> list[str]:
        return bs.app.classic.getmaps('volleyball')

    def __init__(self, settings: dict):
        super().__init__(settings)
        shared = SharedObjects.get()
        self._scoreboard = Scoreboard()
        self._cheer_sound = bs.getsound('cheer')
        self._chant_sound = bs.getsound('crowdChant')
        self._foghorn_sound = bs.getsound('foghorn')
        self._swipsound = bs.getsound('swip')
        self._whistle_sound = bs.getsound('refWhistle')
        self.puck_mesh = bs.getmesh('shield')
        self.puck_tex = bs.gettexture('gameCircleIcon')
        self._puck_sound = bs.getsound('metalHit')
        self.puck_material = bs.Material()
        self.puck_material.add_actions(actions=(('modify_part_collision',
                                                 'friction', 0.5)))
        self.puck_material.add_actions(conditions=('they_have_material',
                                                   shared.pickup_material),
                                       actions=('modify_part_collision',
                                                'collide', True))
        self.puck_material.add_actions(
            conditions=(
                ('we_are_younger_than', 100),
                'and',
                ('they_have_material', shared.object_material),
            ),
            actions=('modify_node_collision', 'collide', False),
        )
        self.puck_material.add_actions(conditions=('they_have_material',
                                                   shared.footing_material),
                                       actions=('impact_sound',
                                                self._puck_sound, 0.2, 5))

        # Keep track of which player last touched the puck
        self.puck_material.add_actions(
            conditions=('they_have_material', shared.player_material),
            actions=(('call', 'at_connect',
                      self._handle_puck_player_collide), ))

        # We want the puck to kill powerups; not get stopped by them
        self.puck_material.add_actions(
            conditions=('they_have_material',
                        PowerupBoxFactory.get().powerup_material),
            actions=(('modify_part_collision', 'physical', False),
                     ('message', 'their_node', 'at_connect', bs.DieMessage())))
        self._score_region_material = bs.Material()
        self._score_region_material.add_actions(
            conditions=('they_have_material', self.puck_material),
            actions=(('modify_part_collision', 'collide',
                      True), ('modify_part_collision', 'physical', False),
                     ('call', 'at_connect', self._handle_score)))

        self._wall_material = bs.Material()
        self._fake_wall_material = bs.Material()
        self._wall_material.add_actions(

            actions=(
                ('modify_part_collision', 'friction', 100000),
            ))
        self._wall_material.add_actions(
            conditions=('they_have_material', shared.pickup_material),
            actions=(
                ('modify_part_collision', 'collide', False),
            ))

        self._wall_material.add_actions(
            conditions=(('we_are_younger_than', 100),
                        'and',
                        ('they_have_material', shared.object_material)),
            actions=(
                ('modify_part_collision', 'collide', False),
            ))
        self._wall_material.add_actions(
            conditions=('they_have_material', shared.footing_material),
            actions=(
                ('modify_part_collision', 'friction', 9999.5),
            ))
        self._wall_material.add_actions(
            conditions=('they_have_material', BombFactory.get().blast_material),
            actions=(
                ('modify_part_collision', 'collide', False),
                ('modify_part_collision', 'physical', False)

            ))
        self._fake_wall_material.add_actions(
            conditions=('they_have_material', shared.player_material),
            actions=(
                ('modify_part_collision', 'collide', True),
                ('modify_part_collision', 'physical', True)

            ))
        self.blocks = []

        self._net_wall_material = bs.Material()
        self._net_wall_material.add_actions(
            conditions=('they_have_material', shared.player_material),
            actions=(
                ('modify_part_collision', 'collide', True),
                ('modify_part_collision', 'physical', True)

            ))

        self._net_wall_material.add_actions(
            conditions=('they_have_material', shared.object_material),
            actions=(
                ('modify_part_collision', 'collide', True),
            ))
        self._net_wall_material.add_actions(
            conditions=('they_have_material', self.puck_material),
            actions=(
                ('modify_part_collision', 'collide', True),
            ))
        self._net_wall_material.add_actions(
            conditions=('we_are_older_than', 1),
            actions=(
                ('modify_part_collision', 'collide', True),
            ))
        self.net_blocc = []

        self._puck_spawn_pos: Sequence[float] | None = None
        self._score_regions: list[bs.NodeActor] | None = None
        self._puck: Ball | None = None
        self._score_to_win = int(settings['Score to Win'])
        self._punchie_ = bool(settings['Disable Punch'])
        self._bombies_ = bool(settings['Disable Bombs'])
        self._time_limit = float(settings['Time Limit'])
        self._icy_flooor = bool(settings['Icy Floor'])
        self.credit_text = bool(settings['Enable Bottom Credits'])
        self._epic_mode = bool(settings['Epic Mode'])
        # Base class overrides.
        self.slow_motion = self._epic_mode
        self.default_music = (bs.MusicType.EPIC if self._epic_mode else
                              bs.MusicType.TO_THE_DEATH)

        self.force_simple_themes = False

    def get_instance_description(self) -> str | Sequence:
        return HockeyGame.get_instance_description(self)

    def get_instance_description_short(self) -> str | Sequence:
        return HockeyGame.get_instance_description_short(self)

    def on_begin(self) -> None:
        super().on_begin()

        for zone in self.map.zonebs:
            zone.color = self.teams[0].color
        for zone in self.map.zoners:
            zone.color = self.teams[1].color

        self.setup_standard_time_limit(self._time_limit)
        self._puck_spawn_pos = self.map.get_flag_position(None)
        self._spawn_puck()

        # Set up the two score regions.
        self._score_regions = []
        self._score_regions.append(
            bs.NodeActor(
                bs.newnode('region',
                           attrs={
                               'position': (5.7, 0, -0.065),
                               'scale': (10.7, 0.001, 8),
                               'type': 'box',
                               'materials': [self._score_region_material]
                           })))
        self._score_regions.append(
            bs.NodeActor(
                bs.newnode('region',
                           attrs={
                               'position': (-5.7, 0, -0.065),
                               'scale': (10.7, 0.001, 8),
                               'type': 'box',
                               'materials': [self._score_region_material]
                           })))
        self._update_scoreboard()
        self._chant_sound.play()
        if self.credit_text:
            t = bs.newnode('text',
                           attrs={'text': "Created by Freaku\nVolleyBall",
                                  'scale': 0.7,
                                  'position': (0, 0),
                                  'shadow': 0.5,
                                  'flatness': 1.2,
                                  'color': (1, 1, 1),
                                  'h_align': 'center',
                                  'v_attach': 'bottom'})
        shared = SharedObjects.get()
        self.blocks.append(bs.NodeActor(bs.newnode('region', attrs={
            'position': (0, 2.4, 0),
            'scale': (0.8, 60, 200),
            'type': 'box',
            'materials': [self._fake_wall_material]
        })))

        self.net_blocc.append(bs.NodeActor(bs.newnode('region', attrs={
            'position': (0, 0, 0),
            'scale': (0.6, 2.4, 20),
            'materials': [self._net_wall_material]
        })))

    def on_team_join(self, team: Team) -> None:
        self._update_scoreboard()

    def _handle_puck_player_collide(self) -> None:
        collision = bs.getcollision()
        try:
            puck = collision.sourcenode.getdelegate(Ball, True)
            player = collision.opposingnode.getdelegate(
                PlayerSpaz, True
            ).getplayer(Player, True)
        except bs.NotFoundError:
            return

        puck.last_players_to_touch[player.team.id] = player

    def _kill_puck(self) -> None:
        self._puck = None

    def _handle_score(self) -> None:
        assert self._puck is not None
        assert self._score_regions is not None

        # Our puck might stick around for a second or two
        # we don't want it to be able to score again.
        if self._puck.scored:
            return

        region = bs.getcollision().sourcenode
        index = 0
        for index in range(len(self._score_regions)):
            if region == self._score_regions[index].node:
                break

        for team in self.teams:
            if team.id == index:
                scoring_team = team
                team.score += 1

                # Change puck Spawn
                if team.id == 0:  # left side scored
                    self._puck_spawn_pos = (5, 0.42, 0)
                elif team.id == 1:  # right side scored
                    self._puck_spawn_pos = (-5, 0.42, 0)
                else:  # normally shouldn't occur
                    self._puck_spawn_pos = (0, 0.42, 0)
                # Easy pizzy

                for player in team.players:
                    if player.actor:
                        player.actor.handlemessage(bs.CelebrateMessage(2.0))

                # If we've got the player from the scoring team that last
                # touched us, give them points.
                if (scoring_team.id in self._puck.last_players_to_touch
                        and self._puck.last_players_to_touch[scoring_team.id]):
                    self.stats.player_scored(
                        self._puck.last_players_to_touch[scoring_team.id],
                        100,
                        big_message=True)

                # End game if we won.
                if team.score >= self._score_to_win:
                    self.end_game()

        self._foghorn_sound.play()
        self._cheer_sound.play()

        self._puck.scored = True

        # Kill the puck (it'll respawn itself shortly).
        bs.emitfx(position=bs.getcollision().position, count=int(
            6.0 + 7.0 * 12), scale=3, spread=0.5, chunk_type='spark')
        bs.timer(0.7, self._kill_puck)

        bs.cameraflash(duration=7.0)
        self._update_scoreboard()

    def end_game(self) -> None:
        return HockeyGame.end_game(self)

    def on_transition_in(self) -> None:
        super().on_transition_in()
        activity = bs.getactivity()
        if self._icy_flooor:
            activity.map.is_hockey = True

    def _update_scoreboard(self) -> None:
        return HockeyGame._update_scoreboard(self)

    # overriding the default character spawning..
    def spawn_player(self, player: Player) -> bs.Actor:
        spaz = self.spawn_player_spaz(player)

        if self._bombies_:
            # We want the button to work, just no bombs...
            spaz.bomb_count = 0
            # Imagine not being able to swipe those colorful buttons ;(

        if self._punchie_:
            spaz.connect_controls_to_player(enable_punch=False)

        return spaz

    def handlemessage(self, msg: Any) -> Any:

        # Respawn dead players if they're still in the game.
        if isinstance(msg, bs.PlayerDiedMessage):
            # Augment standard behavior...
            super().handlemessage(msg)
            self.respawn_player(msg.getplayer(Player))

        # Respawn dead pucks.
        elif isinstance(msg, PuckDiedMessage):
            if not self.has_ended():
                bs.timer(2.2, self._spawn_puck)
        else:
            super().handlemessage(msg)

    def _flash_puck_spawn(self) -> None:
        # Effect >>>>>> Flashly
        bs.emitfx(position=self._puck_spawn_pos, count=int(
            6.0 + 7.0 * 12), scale=1.7, spread=0.4, chunk_type='spark')

    def _spawn_puck(self) -> None:
        self._swipsound.play()
        self._whistle_sound.play()
        self._flash_puck_spawn()
        assert self._puck_spawn_pos is not None
        self._puck = Ball(position=self._puck_spawn_pos)
