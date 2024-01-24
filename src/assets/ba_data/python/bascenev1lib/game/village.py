# Released under AGPL-3.0-or-later. See LICENSE for details.
#
"""Won't explain."""

# ba_meta require api 8
# (see https://ballistica.net/wiki/meta-tag-system)

from __future__ import annotations

from typing import TYPE_CHECKING

import math
import random

from era import gdata
import bascenev1 as bs
from era.utils import inform
from bauiv1 import SpecialChar, charstr
from bascenev1lib.actor.spaz import Spaz
from bascenev1lib.actor.anomalies import BlackHole

if TYPE_CHECKING:
    from typing import Any, Sequence


class GuideSpaz(Spaz):
    def __init__(
        self,
        color: Sequence[float] = (1.0, 1.0, 1.0),
        highlight: Sequence[float] = (0.5, 0.5, 0.5),
        character: str = 'Spaz',
        ilist: list | None = None,
        pos: Sequence[float] = (0, 0, 0),
        ang: float = 0,
        allow_distance: bool = False,
    ):
        super().__init__(
            color=color,
            highlight=highlight,
            character=character,
            source_player=None,
            can_accept_powerups=False,
        )
        self.inform_values = ilist or []
        self.allow_distance = allow_distance
        self._cid_dict = {}
        self._text0: bs.Node | None = None
        self._text1: bs.Node | None = None
        self._text2: bs.Node | None = None
        self._pos = pos
        self._ang = ang

        self._update()
        bs.timer(0.1, self._update, True)

    def handlemessage(self, msg: Any) -> Any:
        if isinstance(msg, bs.HitMessage):
            return
        elif isinstance(msg, bs.OutOfBoundsMessage):
            self.handlemessage(bs.StandMessage(self._pos, self._ang))
        else:
            return super().handlemessage(msg)

    def punch_call(self, cid: int, lang: str):
        try:
            self._cid_dict[cid] += 1
            if self._cid_dict[cid] >= len(self.inform_values):
                self._cid_dict[cid] = 0
        except KeyError:
            self._cid_dict[cid] = 0
        self._call_inform(cid, lang)

    def pickup_call(self, cid: int, lang: str):
        try:
            self._cid_dict[cid] = self._cid_dict[cid]
        except KeyError:
            self._cid_dict[cid] = 0
        self._call_inform(cid, lang)

    def bomb_call(self, cid: int, lang: str):
        try:
            self._cid_dict[cid] -= 1
            if self._cid_dict[cid] < 0:
                self._cid_dict[cid] = len(self.inform_values) - 1
        except KeyError:
            self._cid_dict[cid] = 0
        self._call_inform(cid, lang)

    def _call_inform(self, cid: int, lang: str):
        data = self.inform_values[self._cid_dict[cid]]
        current = str(self._cid_dict[cid] + 1)
        total = str(len(self.inform_values))
        inform(data[0], data[1], cid, lang,
               ['[' + current + '/' + total + ']'] + data[2])

    def _update(self):
        if not self.allow_distance:
            sdrct = (self._pos[0] - self.node.position[0],
                     self._pos[1] - self.node.position[1],
                     self._pos[2] - self.node.position[2])
            sdstnc = math.sqrt(sdrct[0] ** 2 + sdrct[1] ** 2 + sdrct[2] ** 2)
            if sdstnc >= 1.1:
                self.handlemessage(bs.StandMessage(self._pos, self._ang))
        show = False
        for node in bs.getnodes():
            from bascenev1lib.actor.playerspaz import PlayerSpaz
            spaz = node.getdelegate(PlayerSpaz)
            if spaz:
                drct = (self.node.position[0] - node.position[0],
                        self.node.position[1] - node.position[1],
                        self.node.position[2] - node.position[2])
                dstnc = math.sqrt(drct[0] ** 2 + drct[1] ** 2 + drct[2] ** 2)
                if dstnc <= 1.5:
                    show = True
                    spaz.target_guide = self
                else:
                    spaz.target_guide = (None if spaz.target_guide == self
                                         else spaz.target_guide)
        if show and not self._text0:
            m0 = bs.newnode('math', owner=self.node,
                            attrs={'input1': (0, 1.75, 0), 'operation': 'add'})
            self.node.connectattr('torso_position', m0, 'input2')
            self._text0 = bs.newnode(
                'text',
                owner=self.node,
                attrs={'text': charstr(SpecialChar.LEFT_BUTTON) + ' Talk',
                       'in_world': True,
                       'shadow': 1.0,
                       'flatness': 1.0,
                       'color': (1, 1, 0, 1),
                       'scale': 0.01,
                       'h_align': 'center',
                       'v_align': 'center'}
            )
            m0.connectattr('output', self._text0, 'position')
            m1 = bs.newnode('math', owner=self.node,
                            attrs={'input1': (0, 1.5, 0), 'operation': 'add'})
            self.node.connectattr('torso_position', m1, 'input2')
            self._text1 = bs.newnode(
                'text',
                owner=self.node,
                attrs={'text': charstr(SpecialChar.TOP_BUTTON) + ' Repeat',
                       'in_world': True,
                       'shadow': 1.0,
                       'flatness': 1.0,
                       'color': (0, 0, 1, 1),
                       'scale': 0.01,
                       'h_align': 'center',
                       'v_align': 'center'}
            )
            m1.connectattr('output', self._text1, 'position')
            m2 = bs.newnode('math', owner=self.node,
                            attrs={'input1': (0, 1.25, 0), 'operation': 'add'})
            self.node.connectattr('torso_position', m2, 'input2')
            self._text2 = bs.newnode(
                'text',
                owner=self.node,
                attrs={
                    'text': charstr(SpecialChar.RIGHT_BUTTON) + ' Previous',
                    'in_world': True,
                    'shadow': 1.0,
                    'flatness': 1.0,
                    'color': (1, 0, 0, 1),
                    'scale': 0.01,
                    'h_align': 'center',
                    'v_align': 'center'
                }
            )
            m2.connectattr('output', self._text2, 'position')
        elif not show and self._text0:
            self._text0.delete()
            self._text0 = None
            self._text1.delete()
            self._text1 = None
            self._text2.delete()
            self._text2 = None


class FakeBlackHole(BlackHole):
    """A black hole that doesnt suck in anything"""
    def __init__(self, position: Sequence[float] = (0.0, 0.0, 0.0),
                 radius: float = 10.0):
        super().__init__(position, None, radius, radius * 10)
        self._update_timer = None


class Player(bs.Player['Team']):
    """Our player type for this game."""


class Team(bs.Team[Player]):
    """Our team type for this game."""


# ba_meta export bascenev1.GameActivity
class VillageGame(bs.TeamGameActivity[Player, Team]):
    """A game type used for guiding the players."""

    name = 'Village'
    description = 'A guide gamemode for bs9 servers.'
    default_music = bs.MusicType.GRAND_ROMP

    @classmethod
    def supports_session_type(cls, sessiontype: type[bs.Session]) -> bool:
        return issubclass(sessiontype, bs.DualTeamSession) or issubclass(
            sessiontype, bs.FreeForAllSession
        )

    @classmethod
    def get_supported_maps(cls, sessiontype: type[bs.Session]) -> list[str]:
        return ['Crag Castle']

    def __init__(self, settings: dict):
        super().__init__(settings)
        self.force_simple_themes = False

        self.tipguide: bs.Node | None = None
        self.powerupguide: bs.Node | None = None
        self.shopguide: bs.Node | None = None
        self.tagguide: bs.Node | None = None
        self.allianceguide: bs.Node | None = None
        self.wheelguide: bs.Node | None = None
        self.vipguide: bs.Node | None = None
        self.topguide: bs.Node | None = None

        self.supportguide: bs.Node | None = None
        self.supportguideknockouttimer: bs.Timer | None = None
        self.fbh: FakeBlackHole | None = None
        self.bhs = bs.app.classic.server._config.bs9vbhs * 10

    def get_instance_description(self) -> str | Sequence:
        return 'You find a peaceful and quite village, you\'re safe here.'

    def get_instance_description_short(self) -> str | Sequence:
        return 'explore the village'

    def on_transition_in(self) -> None:
        super().on_transition_in()
        tips = [['tip' + str(i), 'success', []] for i in range(1, 5)]
        tips[1][2] = ['SoulShadow']
        tips[2][2] = ['E0']
        tips[3][2] = ['PowerUser']
        random.shuffle(tips)
        tips = [['tip0', 'success', []]] + tips
        self.tipguide = GuideSpaz((0, 1, 0), (0, 0.7, 0), 'Grumbledorf', tips,
                                  (-1.5, 7.5, -3.2), 300)
        self.tipguide.node.name = 'Sageleaf'
        self.tipguide.node.name_color = (0, 1, 0)
        tips = [['powerupGuide' + str(i), (0.6, 0, 0.6), []]
                for i in range(1, 15)]
        random.shuffle(tips)
        tips = ([['powerupGuide0', (0.6, 0, 0.6), []]] + tips
                + [['powerupGuide' + str(len(tips) + 1), (0.6, 0, 0.6), []]])
        self.powerupguide = GuideSpaz((0, 0, 0), (0.8, 0, 1), 'B-9000', tips,
                                      (-3.5, 6, -1), 45)
        self.powerupguide.node.name = 'PowerUser'
        self.powerupguide.node.name_color = (0.5, 0.5, 0.5)
        tips = [['shopGuide' + str(i), (0, 1, 1), []] for i in range(10)]
        shopdatapath = gdata.getpath('gshop')
        shopdata = gdata.load(shopdatapath, update=False)
        items = []
        for i in shopdata:
            if i not in ('emote', 'other'):
                items.append(random.choice(list(shopdata[i].keys())) + '@' + i)
        itext = ''
        for _, x in enumerate(items):
            x = x.split('@')
            cat = x[1]
            item = x[0]
            itext += '\n/shop ' + cat + ' ' + item
        tips[8][2] = [itext]
        self.shopguide = GuideSpaz((0, 1, 1), (0, 1, 1), 'Bones', tips,
                                   (6.5, 6, -2.5), 270)
        self.shopguide.node.name = 'SoulShadow'
        self.shopguide.node.name_color = (0, 1, 1)
        self.shopguide.equip(items)
        self.tagguide = GuideSpaz(
            (0, 0, 0),
            (1, 0, 0.9),
            'Bernard',
            [['tagGuide' + str(i), (0.5, 0.5, 0.5), []] for i in range(8)],
            (3, 6, -2.5),
            30
        )
        self.tagguide.node.name = 'Midnight'
        self.tagguide.node.name_color = (0.5, 0.5, 0.5)
        self.tagguide.give_cstms('Look at my cool tag! >.<', (1, 0, 0.9, 1))
        self.allianceguide = GuideSpaz(
            (1, 0, 0),
            (1, 0, 0),
            'Spaz',
            [['allianceGuide' + str(i), 'error', []] for i in range(18)],
            (8, 7.5, -1),
            0
        )
        self.allianceguide.node.name = 'Jacky'
        self.allianceguide.node.name_color = (1, 0, 0)
        self.allianceguide.give_alliances(True, '<<<bs9official>>>',
                                          (1, 1, 0, 1))
        self.wheelguide = GuideSpaz(
            (0, 0, 0),
            (1, 1, 0),
            'Agent Johnson',
            [['wheelGuide' + str(i), 'warning', []] for i in range(7)],
            (7.2, 7.5, -6),
            90
        )
        self.wheelguide.node.name = 'Stingray'
        self.wheelguide.node.name_color = (1, 1, 0)
        tips = [['vipGuide' + str(i), 'warning', []] for i in range(1, 6)]
        random.shuffle(tips)
        tips = ([['vipGuide0', 'warning', []]] + tips
                + [['vipGuide' + str(len(tips) + 1), 'warning', []]]
                + [['vipGuide' + str(len(tips) + 2), 'warning', []]])
        self.vipguide = GuideSpaz((1, 1, 0), (1, 1, 0), 'Pascal', tips,
                                  (3.5, 7.5, -4.5), 340)
        self.vipguide.node.name = 'Flipper'
        self.vipguide.node.name_color = (1, 1, 0)
        self.vipguide.give_ranks(True, 'VIP', (1, 0.15, 0.15, 1), True)
        pos = (-6, 7.5, -5.5)
        ang = 50
        tips = [['supportGuide-1', 'warning', []]]
        knockout = True
        if self.bhs > 0:
            pos = (-2, 9, -6)
            ang = 160
            tips = [['supportGuide' + str(i), (0.5, 0.25, 1.0), []]
                    for i in range(5)]
            knockout = False
            self.fbh = FakeBlackHole((0.5, 10, -20), self.bhs)
        self.supportguide = GuideSpaz((0.5, 0.25, 1), (0.5, 0.25, 1), 'Bones',
                                      tips, pos, ang)
        self.supportguide.node.name = 'E0'
        self.supportguide.node.name_color = (0.5, 0.25, 1)
        if knockout:
            self.supportguide.allow_distance = True
            self.supportguide.node.handlemessage('knockout', 2000)
            self.supportguideknockouttimer = bs.Timer(
                1,
                bs.Call(self.supportguide.node.handlemessage, 'knockout', 2000),
                True)
        self.topguide = GuideSpaz(
            (0.5, 0.5, 0.5),
            (0, 0, 0),
            'Pixel',
            [['topGuide' + str(i), (1, 1, 1), []] for i in range(7)],
            (-6.5, 7.5, 0),
            120
        )
        self.topguide.node.name = 'Dust'
        self.topguide.node.name_color = (0.5, 0.5, 0.5)
        match random.randint(0, 5):
            case 0:
                trophy = charstr(SpecialChar.TROPHY4)
                lcolor = (0.9, 0, 1, 1)
            case 1:
                trophy = charstr(SpecialChar.TROPHY3)
                lcolor = (1, 0, 0, 1)
            case 2:
                trophy = charstr(SpecialChar.TROPHY2)
                lcolor = (1, 1, 0, 1)
            case 3:
                trophy = charstr(SpecialChar.TROPHY1)
                lcolor = (0, 0, 1, 0.9)
            case 4:
                trophy = charstr(SpecialChar.TROPHY0B)
                lcolor = (0, 1, 0, 0.8)
            case 5:
                trophy = ''
                lcolor = (1, 1, 1, 0.75)
        self.topguide.give_leagues(
            True, trophy + '#' + str(random.randint(1, 999)), lcolor
        )
        self.topguide.give_tops(True, '#' + str(random.randint(1, 999)),
                                (1, 1, 1, 1))

    def handlemessage(self, msg: Any) -> Any:
        super().handlemessage(msg)
        if isinstance(msg, bs.PlayerDiedMessage):
            self.respawn_player(msg.getplayer(Player))
