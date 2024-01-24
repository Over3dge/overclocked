# Released under AGPL-3.0-or-later. See LICENSE for details.
#
"""Soccer game and support classes."""

# ba_meta require api 8
# (see https://ballistica.net/wiki/meta-tag-system)

from __future__ import annotations

from typing import TYPE_CHECKING

import bascenev1 as bs
from bascenev1lib.gameutils import SharedObjects
from bascenev1lib.actor.playerspaz import PlayerSpaz
from bascenev1lib.actor.scoreboard import Scoreboard
from bascenev1lib.game.hockey import (
    HockeyGame,
    PuckDiedMessage,
    Player,
    Team,
    Puck,
)

if TYPE_CHECKING:
    from typing import Any, Sequence


class Ball(bs.Actor):
    """Ball."""

    def __init__(self, position: Sequence[float] = (0.0, 1.0, 0.0)):
        super().__init__()
        shared = SharedObjects.get()
        activity = self.getactivity()

        # Spawn just above the provided point.
        self._spawn_pos = (position[0], position[1] + 1.0, position[2])
        self.last_players_to_touch: dict[int, Player] = {}
        self.scored = False
        assert activity is not None
        assert isinstance(activity, SoccerGame)
        pmats = [shared.object_material, activity.puck_material]
        self.node = bs.newnode(
            'prop',
            delegate=self,
            attrs={
                'mesh': activity.puck_mesh,
                'color_texture': activity.puck_tex,
                'body': 'sphere',
                'reflection': 'soft',
                'reflection_scale': [0.2],
                'shadow_size': 1.0,
                'is_area_of_interest': True,
                'position': self._spawn_pos,
                'materials': pmats,
                'gravity_scale': self.activity.gravity_mult,
            },
        )
        bs.animate(self.node, 'mesh_scale', {0: 0, 0.2: 1.3, 0.26: 1})

    def handlemessage(self, msg: Any) -> Any:
        if (
            isinstance(msg, bs.DieMessage)
            or isinstance(msg, bs.OutOfBoundsMessage)
            or isinstance(msg, bs.HitMessage)
        ):
            Puck.handlemessage(self, msg)
        else:
            super().handlemessage(msg)


# ba_meta export bascenev1.GameActivity
class SoccerGame(bs.TeamGameActivity[Player, Team]):
    """Good old soccer."""

    name = 'Soccer'
    description = 'Score some goals.'
    available_settings = [
        bs.IntSetting(
            'Score to Win',
            min_value=1,
            default=5,
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
        bs.BoolSetting('Allow Powerups', default=False),
        bs.BoolSetting('Allow Bombs', default=False),
        bs.BoolSetting('Overtime', default=True),
        bs.BoolSetting('Epic Mode', default=False),
    ]

    @classmethod
    def supports_session_type(cls, sessiontype: type[bs.Session]) -> bool:
        return issubclass(sessiontype, bs.DualTeamSession)

    @classmethod
    def get_supported_maps(cls, sessiontype: type[bs.Session]) -> list[str]:
        return bs.app.classic.getmaps('soccer')

    def __init__(self, settings: dict):
        super().__init__(settings)
        shared = SharedObjects.get()
        self._scoreboard = Scoreboard()
        self._cheer_sound = bs.getsound('cheer')
        self._chant_sound = bs.getsound('crowdChant')
        self._foghorn_sound = bs.getsound('foghorn')
        self._swipsound = bs.getsound('swip')
        self._whistle_sound = bs.getsound('refWhistle')
        self.puck_mesh = bs.getmesh('frostyPelvis')
        self.puck_tex = bs.gettexture('aliBSRemoteIOSQR')
        self.puck_material = bs.Material()
        self.puck_material.add_actions(
            conditions=(
                ('we_are_younger_than', 100),
                'and',
                ('they_have_material', shared.object_material),
            ),
            actions=('modify_node_collision', 'collide', False),
        )

        # Keep track of which player last touched the puck
        self.puck_material.add_actions(
            conditions=('they_have_material', shared.player_material),
            actions=('call', 'at_connect', self._handle_puck_player_collide),
        )

        self._score_region_material = bs.Material()
        self._score_region_material.add_actions(
            conditions=('they_have_material', self.puck_material),
            actions=(
                ('modify_part_collision', 'collide', True),
                ('modify_part_collision', 'physical', False),
                ('call', 'at_connect', self._handle_score),
            ),
        )
        self._puck_spawn_pos: Sequence[float] | None = None
        self._score_regions: list[bs.NodeActor] | None = None
        self._pucks: list[Ball] = []
        self._score_to_win = int(settings['Score to Win'])
        self._time_limit = float(settings['Time Limit'])
        self._powerups = bool(settings['Allow Powerups'])
        self._bombs = bool(settings['Allow Bombs'])
        self._allow_overtime = bool(settings['Overtime'])
        self._epic_mode = bool(settings['Epic Mode'])
        self.slow_motion = self._epic_mode
        self.default_music = (
            bs.MusicType.EPIC if self._epic_mode else bs.MusicType.HOCKEY
        )
        self.force_simple_themes = self._powerups

    def get_instance_description(self) -> str | Sequence:
        return HockeyGame.get_instance_description(self)

    def get_instance_description_short(self) -> str | Sequence:
        return HockeyGame.get_instance_description_short(self)

    def on_begin(self) -> None:
        super().on_begin()

        self.setup_standard_time_limit(self._time_limit)
        if self._powerups:
            self.setup_standard_powerup_drops()
        self._puck_spawn_pos = self.map.get_flag_position(None)
        self._spawn_puck()

        # Set up the two score regions.
        defs = self.map.defs
        self._score_regions = []
        self._score_regions.append(
            bs.NodeActor(
                bs.newnode(
                    'region',
                    attrs={
                        'position': defs.boxes['goal1'][0:3],
                        'scale': defs.boxes['goal1'][6:9],
                        'type': 'box',
                        'materials': [self._score_region_material],
                    },
                )
            )
        )
        self._score_regions.append(
            bs.NodeActor(
                bs.newnode(
                    'region',
                    attrs={
                        'position': defs.boxes['goal2'][0:3],
                        'scale': defs.boxes['goal2'][6:9],
                        'type': 'box',
                        'materials': [self._score_region_material],
                    },
                )
            )
        )
        self._update_scoreboard()
        self._chant_sound.play()

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

    def _handle_score(self) -> None:
        """A point has been scored."""

        puck = bs.getcollision().opposingnode.getdelegate(Ball, True)
        assert self._score_regions is not None

        # Our puck might stick around for a second or two
        # we don't want it to be able to score again.
        if puck.scored:
            return

        region = bs.getcollision().sourcenode
        index = 0
        for index, score_region in enumerate(self._score_regions):
            if region == score_region.node:
                break

        for team in self.teams:
            if team.id == index:
                scoring_team = team
                team.score += 1

                # Tell all players to celebrate.
                for player in team.players:
                    if player.actor:
                        player.actor.handlemessage(bs.CelebrateMessage(2.0))

                # If we've got the player from the scoring team that last
                # touched us, give them points.
                if (
                    scoring_team.id in puck.last_players_to_touch
                    and puck.last_players_to_touch[scoring_team.id]
                ):
                    self.stats.player_scored(
                        puck.last_players_to_touch[scoring_team.id],
                        100,
                        big_message=True,
                    )

                # End game if we won.
                if team.score >= self._score_to_win:
                    self.end_game()

        self._foghorn_sound.play()
        self._cheer_sound.play()

        puck.scored = True

        # Kill the puck (it'll respawn itself shortly).
        bs.timer(1.0, bs.Call(self._pucks.remove, puck))

        light = bs.newnode(
            'light',
            attrs={
                'position': bs.getcollision().position,
                'height_attenuated': False,
                'color': (1, 0, 0),
            },
        )
        bs.animate(light, 'intensity', {0: 0, 0.5: 1, 1.0: 0}, loop=True)
        bs.timer(1.0, light.delete)

        bs.cameraflash(duration=10.0)
        self._update_scoreboard()

    def end_game(self) -> None:
        return HockeyGame.end_game(self)

    def spawn_player(self, player: Player) -> bs.Actor:
        spaz = self.spawn_player_spaz(player)
        spaz.connect_controls_to_player(enable_bomb=self._bombs)
        return spaz

    def _update_scoreboard(self) -> None:
        return HockeyGame._update_scoreboard(self)

    def handlemessage(self, msg: Any) -> Any:
        # Respawn dead players if they're still in the game.
        if isinstance(msg, bs.PlayerDiedMessage):
            # Augment standard behavior...
            super().handlemessage(msg)
            self.respawn_player(msg.getplayer(Player))

        # Respawn dead pucks.
        elif isinstance(msg, PuckDiedMessage):
            if not self.has_ended():
                bs.timer(3.0, self._spawn_puck)
        else:
            super().handlemessage(msg)

    def _flash_puck_spawn(self) -> None:
        return HockeyGame._flash_puck_spawn(self)

    def _spawn_puck(self) -> None:
        self._swipsound.play()
        self._whistle_sound.play()
        self._flash_puck_spawn()
        assert self._puck_spawn_pos is not None
        psp = list(self._puck_spawn_pos)
        psp[1] += len(self._pucks) * 0.25
        self._pucks.append(Ball(position=psp))

    @property
    def _is_meeting_overtime_conditions(self) -> bool:
        if self._allow_overtime and len(self.players) != 0:
            return True
        return False

    @property
    def overtime_description(self) -> str:
        return 'An extra ball will be dropped into the game every 10 seconds'

    def overtime(self) -> None:
        return HockeyGame.overtime(self)
