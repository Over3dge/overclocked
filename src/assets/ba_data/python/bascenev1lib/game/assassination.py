# Released under AGPL-3.0-or-later. See LICENSE for details.
#
"""Assassination game where a person will be marked for termination."""

# ba_meta require api 8
# (see https://ballistica.net/wiki/meta-tag-system)

from __future__ import annotations

from typing import TYPE_CHECKING

import random

import bascenev1 as bs
from bascenev1lib.game.elimination import Icon
from bascenev1lib.actor.playerspaz import PlayerSpaz
from bascenev1lib.actor.scoreboard import Scoreboard

if TYPE_CHECKING:
    from typing import Any, Sequence


class Player(bs.Player['Team']):
    """Our player type for this game."""

    def __init__(self) -> None:
        self.icon: Icon | None = None
        self.lives = 0  # this is so that we don't have to edit the "Icon"
        # class in order for it to not throw an error, just a cheeky
        # workaround


class Team(bs.Team[Player]):
    """Our team type for this game."""

    def __init__(self) -> None:
        self.score = 0


# ba_meta export bascenev1.GameActivity
class AssassinationGame(bs.TeamGameActivity[Player, Team]):
    """A game type based on acquiring kills."""

    name = 'Assassination'
    description = 'Kill the marked player to gain points.'

    # Print messages when players die since it matters here.
    announce_player_deaths = True

    @classmethod
    def get_available_settings(
        cls, sessiontype: type[bs.Session]
    ) -> list[bs.Setting]:
        settings = [
            bs.IntSetting(
                'Points to Win',
                min_value=1,
                default=10,
                increment=1,
            ),
            bs.IntSetting(
                'Points for Killing The Target',
                min_value=1,
                default=2,
                increment=1,
            ),
            bs.IntSetting(
                'Points for Surviving an Assassination',
                min_value=1,
                default=3,
                increment=1,
            ),
            bs.IntSetting(
                'Negative Points for Killing Others',
                min_value=0,
                default=0,
                increment=1,
            ),
            bs.IntSetting(
                'Seconds for Assassination',
                min_value=5,
                default=20,
                increment=5,
            ),
            bs.IntSetting(
                'Extra Seconds for Assassination per Target Suicide/Betrayal',
                min_value=0,
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
                default=0.5,
            ),
            bs.BoolSetting('Epic Mode', default=False),
        ]

        if issubclass(sessiontype, bs.FreeForAllSession):
            settings.append(
                bs.BoolSetting('Allow Negative Scores', default=False)
            )

        return settings

    @classmethod
    def supports_session_type(cls, sessiontype: type[bs.Session]) -> bool:
        return issubclass(sessiontype, bs.MultiTeamSession)

    @classmethod
    def get_supported_maps(cls, sessiontype: type[bs.Session]) -> list[str]:
        return bs.app.classic.getmaps('melee')

    def __init__(self, settings: dict):
        super().__init__(settings)
        self._scoreboard = Scoreboard()
        self._score_to_win = int(settings['Points to Win'])
        self._itime = int(settings['Seconds for Assassination'])
        self._assassination_score = int(settings['Points for Killing The '
                                                 'Target'])
        self._penalty_score = int(settings['Negative Points for Killing '
                                           'Others'])
        self._suicide_penalty_time = int(settings['Extra Seconds for '
                                                  'Assassination per Target '
                                                  'Suicide/Betrayal'])
        self._survival_points = int(settings['Points for Surviving an '
                                             'Assassination'])
        self._dingsound = bs.getsound('dingSmall')
        self._epic_mode = bool(settings['Epic Mode'])
        self._time_limit = float(settings['Time Limit'])
        self._allow_negative_scores = bool(
            settings.get('Allow Negative Scores', False)
        )
        self._target: Player | None = None
        self._survival_timer: bs.Timer | None = None

        # Base class overrides.
        self.slow_motion = self._epic_mode
        self.default_music = (
            bs.MusicType.EPIC if self._epic_mode else bs.MusicType.TO_THE_DEATH
        )

    def get_instance_description(self) -> str | Sequence:
        return ('Earn ${ARG1} points by successful assassinations or surviving'
                ' assassinations.', self._score_to_win)

    def get_instance_description_short(self) -> str | Sequence:
        return 'earn ${ARG1} points', self._score_to_win

    def on_team_join(self, team: Team) -> None:
        if self.has_begun():
            self._update_scoreboard()

    def on_begin(self) -> None:
        super().on_begin()
        self.setup_standard_time_limit(self._time_limit)
        self.setup_standard_powerup_drops()

        self._update_scoreboard()
        bs.timer(3, self.setup)

    def setup(self) -> None:
        if (all(len(team.players) > 0 for team in self.teams)
                and len(self.teams) > 1):
            for player in self.players:
                if player.icon:
                    player.icon.node.delete()
                    player.icon = None
                    break
            self._target = random.choice(self.players)
            self._target.icon = Icon(self._target, position=(0, 50), scale=1)
            self._target.icon._lives_text.text = str(self._itime)
            self._survival_timer = bs.Timer(1, self.countdown)
        else:
            self.end_game()

    def countdown(self) -> None:
        if int(self._target.icon._lives_text.text) > 0:
            self._target.icon._lives_text.text = str(
                int(self._target.icon._lives_text.text) - 1
            )
            if self._target.icon._lives_text.text != '0':
                self._survival_timer = bs.Timer(1, self.countdown)
        if self._target.icon._lives_text.text == '0':
            self._target.icon._lives_text.text = 'Survived'
            self._target.team.score += self._survival_points
            if isinstance(self._target.actor, PlayerSpaz):
                self._target.actor.set_score_text(
                    '+' + str(self._survival_points),
                    color=self._target.team.color,
                    flash=True,
                )
            self._target = None
            self._dingsound.play()
            if not self._check_end():
                bs.timer(3, self.setup)

    def on_player_leave(self, player: Player) -> None:
        super().on_player_leave(player)
        if self._target is player:
            if player.icon:
                player.icon.node.delete()
                player.icon = None
            self._survival_timer = None
            self._target = None
            bs.timer(1, self.setup)

    def handlemessage(self, msg: Any) -> Any:

        if isinstance(msg, bs.PlayerDiedMessage):

            # Augment standard behavior.
            super().handlemessage(msg)

            player = msg.getplayer(Player)
            self.respawn_player(player)

            killer = msg.getkillerplayer(Player)
            if killer is None:
                return None

            if (self._target and player is self._target
                    and killer.team is not self._target.team):
                player.icon.handle_player_died()
                bs.timer(3, self.setup)
                self._survival_timer = None
                self._target.icon._lives_text.text = ('Assassinated by '
                                                      + killer.getname(True))
                self._target = None
                killer.team.score += self._assassination_score
                self._dingsound.play()
                if isinstance(killer.actor, PlayerSpaz) and killer.actor:
                    killer.actor.set_score_text(
                        '+' + str(self._assassination_score),
                        color=killer.team.color,
                        flash=True,
                    )
            elif self._target and player is self._target:
                self._target.icon._lives_text.text = str(
                    int(self._target.icon._lives_text.text)
                    + int(player.customdata['respawn_icon']._text.node.text)
                    + self._suicide_penalty_time)
            elif not self._target or killer.team is not self._target.team:
                new_score = killer.team.score - self._penalty_score
                if not self._allow_negative_scores:
                    new_score = max(0, new_score)
                if (isinstance(killer.actor, PlayerSpaz) and killer.actor
                        and new_score - killer.team.score < 0):
                    killer.actor.set_score_text(
                        str(new_score - killer.team.score),
                        color=killer.team.color,
                        flash=True,
                    )
                killer.team.score = new_score

            self._check_end()

        else:
            return super().handlemessage(msg)
        return None

    def _update_scoreboard(self) -> None:
        for team in self.teams:
            self._scoreboard.set_team_value(
                team, team.score, self._score_to_win
            )

    def _check_end(self) -> bool:
        self._update_scoreboard()
        assert self._score_to_win is not None
        if any(team.score >= self._score_to_win for team in self.teams):
            bs.timer(0.5, self.end_game)
            return True
        return False

    def end_game(self) -> None:
        results = bs.GameResults()
        for team in self.teams:
            results.set_team_score(team, team.score)
        self.end(results=results)
