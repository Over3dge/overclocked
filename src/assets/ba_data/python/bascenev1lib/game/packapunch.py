# Released under AGPL-3.0-or-later. See LICENSE for details.
#
"""Pack-A-Punch is back better than ever."""

# ba_meta require api 8
# (see https://ballistica.net/wiki/meta-tag-system)

from __future__ import annotations

from typing import TYPE_CHECKING

import logging

import bascenev1 as bs
from bascenev1lib.actor.playerspaz import PlayerSpaz
from bascenev1lib.actor.scoreboard import Scoreboard
from bascenev1lib.actor.spazfactory import SpazFactory
from bascenev1lib.game.deathmatch import DeathMatchGame
from bascenev1lib.game.elimination import EliminationGame, Icon

if TYPE_CHECKING:
    from typing import Any, Sequence


class Player(bs.Player['Team']):
    """Our player type for this game."""

    def __init__(self) -> None:
        self.lives = 0
        self.icons: list[Icon] = []


class Team(bs.Team[Player]):
    """Our team type for this game."""

    def __init__(self) -> None:
        self.score = 0
        self.survival_seconds: int | None = None
        self.spawn_order: list[Player] = []


# ba_meta export bascenev1.GameActivity
class PackAPunchGame(bs.TeamGameActivity[Player, Team]):
    """A game type where we pack the best punches of our lives."""

    name = 'Pack-A-Punch'
    description = 'Blow up your opponents, by punching them!'
    announce_player_deaths = True

    @classmethod
    def get_available_settings(
        cls, sessiontype: type[bs.Session]
    ) -> list[bs.Setting]:
        settings = [
            bs.IntSetting(
                'Player Health',
                default=500,
                min_value=100,
                increment=50,
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
            bs.BoolSetting('Boxing Gloves', default=True),
            bs.BoolSetting('Allow Grabbing', default=True),
            bs.BoolSetting('Random Chance of Saviors on Impact', default=True),
            bs.IntChoiceSetting(
                'Game mode',
                choices=[('Elimination', 1), ('Deathmatch', 2)],
                default=1,
            ),
            bs.IntSetting(
                'Lives or Kills to Win Per Player',
                default=5,
                min_value=1,
                increment=1,
            ),
            bs.BoolSetting('Overtime', default=True),
            bs.BoolSetting('Epic Mode', default=False),
        ]
        if issubclass(sessiontype, bs.DualTeamSession):
            settings.append(
                bs.BoolSetting(
                    'Solo Mode (Elimination Exclusive)', default=False
                )
            )
            settings.append(
                bs.BoolSetting(
                    'Balance Total Lives (Elimination Exclusive)', default=False
                )
            )
        elif issubclass(sessiontype, bs.FreeForAllSession):
            settings.append(
                bs.BoolSetting(
                    'Allow Negative Scores (Deathmatch Exclusive)',
                    default=False,
                )
            )
        return settings

    @classmethod
    def supports_session_type(cls, sessiontype: type[bs.Session]) -> bool:
        return issubclass(sessiontype, bs.DualTeamSession) or issubclass(
            sessiontype, bs.FreeForAllSession
        )

    @classmethod
    def get_supported_maps(cls, sessiontype: type[bs.Session]) -> list[str]:
        return bs.app.classic.getmaps('melee')

    def __init__(self, settings: dict):
        super().__init__(settings)
        self._scoreboard = Scoreboard()
        self._score_to_win: int | None = None
        self._start_time: float | None = None
        self._vs_text: bs.Actor | None = None
        self._round_end_timer: bs.Timer | None = None
        self._dingsound = bs.getsound('dingSmall')
        self._allow_overtime = bool(settings['Overtime'])
        self._epic_mode = bool(settings['Epic Mode'])
        self._lives_per_player = int(
            settings['Lives or Kills to Win Per Player']
        )
        self._kills_to_win_per_player = int(
            settings['Lives or Kills to Win Per Player']
        )
        self._time_limit = float(settings['Time Limit'])
        self._balance_total_lives = bool(
            settings.get('Balance Total Lives (Elimination Exclusive)', False)
        )
        self._solo_mode = bool(
            settings.get('Solo Mode (Elimination Exclusive)', False)
        )
        self._healthpoints = int(settings['Player Health'])
        self._glovesbool = bool(settings['Boxing Gloves'])
        self._grabbool = bool(settings['Allow Grabbing'])
        self._shieldbool = bool(settings['Random Chance of Saviors on Impact'])
        self._gamemode = int(settings['Game mode'])
        self._allow_negative_scores = bool(
            settings.get('Allow Negative Scores (Deathmatch Exclusive)', False)
        )
        self.force_simple_themes = False

        # Base class overrides:
        self.slow_motion = self._epic_mode
        self.default_music = (
            bs.MusicType.EPIC if self._epic_mode else bs.MusicType.GRAND_ROMP
        )

    def get_instance_description(self) -> str | Sequence:
        return (
            EliminationGame.get_instance_description(self)
            if self._gamemode == 1
            else DeathMatchGame.get_instance_description(self)
        )

    def get_instance_description_short(self) -> str | Sequence:
        return (
            EliminationGame.get_instance_description_short(self)
            if self._gamemode == 1
            else DeathMatchGame.get_instance_description_short(self)
        )

    def on_transition_in(self) -> None:
        SpazFactory.get().max_hitpoints = self._healthpoints * 10
        super().on_transition_in()
        # Ok an explanation: we need to set the scoreconfig for our cls as
        # it doesn't work if we do it for self, this *should* be done in
        # init, however if our next game is from the same type it will
        # overwrite our scoreconfig as the next game gets initialized right
        # when we start playing this one
        self.__class__.scoreconfig = (
            EliminationGame.scoreconfig
            if self._gamemode == 1
            else DeathMatchGame.scoreconfig
        )

    def on_player_join(self, player: Player) -> None:
        (
            EliminationGame.on_player_join(self, player)
            if self._gamemode == 1
            else super().on_player_join(player)
        )

    def on_team_join(self, team: Team) -> None:
        (
            super().on_team_join(team)
            if self._gamemode == 1
            else DeathMatchGame.on_team_join(self, team)
        )

    def on_begin(self) -> None:
        super().on_begin()
        self.setup_standard_time_limit(self._time_limit)
        if self._gamemode == 1:
            self._start_time = bs.time()
            self.allow_mid_activity_joins = False
            if self._solo_mode:
                self._vs_text = bs.NodeActor(
                    bs.newnode(
                        'text',
                        attrs={
                            'position': (0, 105),
                            'h_attach': 'center',
                            'h_align': 'center',
                            'maxwidth': 200,
                            'shadow': 0.5,
                            'vr_depth': 390,
                            'scale': 0.6,
                            'v_attach': 'bottom',
                            'color': (0.8, 0.8, 0.3, 1.0),
                            'text': bs.Lstr(resource='vsText'),
                        },
                    )
                )

            # If balance-team-lives is on, add lives to the smaller team until
            # total lives match.
            if (
                isinstance(self.session, bs.DualTeamSession)
                and self._balance_total_lives
                and self.teams[0].players
                and self.teams[1].players
            ):
                if self._get_total_team_lives(
                    self.teams[0]
                ) < self._get_total_team_lives(self.teams[1]):
                    lesser_team = self.teams[0]
                    greater_team = self.teams[1]
                else:
                    lesser_team = self.teams[1]
                    greater_team = self.teams[0]
                add_index = 0
                while self._get_total_team_lives(
                    lesser_team
                ) < self._get_total_team_lives(greater_team):
                    lesser_team.players[add_index].lives += 1
                    add_index = (add_index + 1) % len(lesser_team.players)

            self._update_icons()

            # We could check game-over conditions at explicit trigger points,
            # but lets just do the simple thing and poll it.
            bs.timer(1.0, self._update, repeat=True)
        else:
            # Base kills needed to win on the size of the largest team.
            self._score_to_win = self._kills_to_win_per_player * max(
                1, max(len(t.players) for t in self.teams)
            )
            self._update_scoreboard()

    def _update_solo_mode(self) -> None:
        EliminationGame._update_solo_mode(self)

    def _update_icons(self) -> None:
        EliminationGame._update_icons(self)

    def _get_spawn_point(self, player: Player) -> bs.Vec3 | None:
        EliminationGame._get_spawn_point(self, player)

    def spawn_player(self, player: Player) -> bs.Actor:
        spaz = (
            EliminationGame.spawn_player(self, player)
            if self._gamemode == 1
            else super().spawn_player(player)
        )
        spaz.connect_controls_to_player(
            enable_bomb=False, enable_pickup=self._grabbool
        )
        if self._glovesbool:
            spaz.equip_boxing_gloves()
        spaz.pap_defence = self._shieldbool
        spaz.pap = True

        return spaz

    def _print_lives(self, player: Player) -> None:
        EliminationGame._print_lives(self, player)

    def on_player_leave(self, player: Player) -> None:
        super().on_player_leave(player)
        if self._gamemode == 1:
            player.icons = []

            # Remove us from spawn-order.
            if self._solo_mode:
                if player in player.team.spawn_order:
                    player.team.spawn_order.remove(player)

            # Update icons in a moment since our team will be gone from the
            # list then.
            bs.timer(0, self._update_icons)

            # If the player to leave was the last in spawn order and had
            # their final turn currently in-progress, mark the survival time
            # for their team.
            if self._get_total_team_lives(player.team) == 0:
                assert self._start_time is not None
                player.team.survival_seconds = int(bs.time() - self._start_time)

    def _get_total_team_lives(self, team: Team) -> int:
        return sum(player.lives for player in team.players)

    def handlemessage(self, msg: Any) -> Any:
        if isinstance(msg, bs.PlayerDiedMessage):
            # Augment standard behavior.
            super().handlemessage(msg)
            player: Player = msg.getplayer(Player)

            if self._gamemode == 1:
                player.lives -= 1
                if player.lives < 0:
                    logging.exception(
                        "Got lives < 0 in Elim; this shouldn't happen. solo:"
                        + str(self._solo_mode)
                    )
                    player.lives = 0

                # If we have any icons, update their state.
                for icon in player.icons:
                    icon.handle_player_died()

                # Play big death sound on our last death
                # or for every one in Solo Mode (Elimination Exclusive).
                if self._solo_mode or player.lives == 0:
                    SpazFactory.get().single_player_death_sound.play()

                # If we hit zero lives, we're dead (and our team might be too).
                if player.lives == 0:
                    # If the whole team is now dead, mark their survival time.
                    if self._get_total_team_lives(player.team) == 0:
                        assert self._start_time is not None
                        player.team.survival_seconds = int(
                            bs.time() - self._start_time
                        )
                else:
                    # Otherwise, in regular mode, respawn.
                    if not self._solo_mode:
                        self.respawn_player(player)

                # In solo, put ourself at the back of the spawn order.
                if self._solo_mode:
                    player.team.spawn_order.remove(player)
                    player.team.spawn_order.append(player)
            else:
                self.respawn_player(player)

                killer = msg.getkillerplayer(Player)
                if killer is None:
                    return None

                # Handle team-kills.
                if killer.team is player.team:
                    # In free-for-all, killing yourself loses you a point.
                    if isinstance(self.session, bs.FreeForAllSession):
                        new_score = player.team.score - 1
                        if not self._allow_negative_scores:
                            new_score = max(0, new_score)
                        player.team.score = new_score

                    # In teams-mode it gives a point to the other team.
                    else:
                        self._dingsound.play()
                        for team in self.teams:
                            if team is not killer.team:
                                team.score += 1

                # Killing someone on another team nets a kill.
                else:
                    killer.team.score += 1
                    self._dingsound.play()

                    # In FFA show scores since its hard to find on the
                    # scoreboard.
                    if isinstance(killer.actor, PlayerSpaz) and killer.actor:
                        killer.actor.set_score_text(
                            str(killer.team.score)
                            + '/'
                            + str(self._score_to_win),
                            color=killer.team.color,
                            flash=True,
                        )

                self._update_scoreboard()

                # If someone has won, set a timer to end shortly.
                # (allows the dust to clear and draws to occur if deaths are
                # close enough)
                assert self._score_to_win is not None
                if any(team.score >= self._score_to_win for team in self.teams):
                    bs.timer(0.5, self.end_game)
        else:
            return super().handlemessage(msg)
        return None

    def _update_scoreboard(self) -> None:
        DeathMatchGame._update_scoreboard(self)

    def _update(self) -> None:
        EliminationGame._update(self)

    def _get_living_teams(self) -> list[Team]:
        return EliminationGame._get_living_teams(self)

    def end_game(self) -> None:
        (
            EliminationGame.end_game(self)
            if self._gamemode == 1
            else DeathMatchGame.end_game(self)
        )

    @property
    def _is_meeting_overtime_conditions(self) -> bool:
        return (
            True
            if self._allow_overtime
            and (self._gamemode == 1 or len(self.players) != 0)
            else False
        )

    @property
    def overtime_description(self) -> str:
        return (
            'Everyone including eliminated folks gets a final life'
            if self._gamemode == 1
            else (
                'Everyone gets a score of '
                if isinstance(self.session, bs.FreeForAllSession)
                else 'All teams get a score of '
            )
            + str(self._score_to_win - 1)
        )

    def overtime(self) -> None:
        return (
            EliminationGame.overtime(self)
            if self._gamemode == 1
            else DeathMatchGame.overtime(self)
        )
