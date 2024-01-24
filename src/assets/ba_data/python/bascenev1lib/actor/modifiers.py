# Released under AGPL-3.0-or-later. See LICENSE for details.
#
"""Game modifiers."""

import random

import bascenev1 as bs
from era.utils import chasattr
from bascenev1lib.actor.bomb import BombFactory
from bascenev1lib.actor.spaz import Spaz, SpazFactory
from bascenev1lib.actor.spazbot import SpazBotSet, EnemyBot
from bascenev1lib.actor.powerupbox import PowerupBox, PowerupBoxFactory
from bascenev1lib.actor.spazappearance import get_appearances

from typing import Sequence, Any


class Modifier(bs.Actor):
    """A template for all other game modifiers

    Category: Gameplay Classes
    """

    name: str = 'None'
    text: str = ''
    texture: bs.Texture | str = 'achievementEmpty'
    color: Sequence[float] = (0.5, 0.5, 0.5)
    conflicts: list = []

    def __init__(self, ocm: bool | None = None) -> None:
        super().__init__()
        self.nodes: dict[str, bs.Node] | None = None
        self.bg_tex = bs.gettexture('buttonSquare')
        self.outline = bs.gettexture('achievementOutline')
        self.tex = bs.gettexture(self.texture)
        self.ocm = ocm
        self._ended: bool = False

    def make_badge(self, pos: list[int], base: bool = False) -> None:
        # reload textures in base mode
        if base:
            self.bg_tex = bs.gettexture('buttonSquare')
            self.outline = bs.gettexture('achievementOutline')
            self.tex = bs.gettexture(self.texture)

        self.nodes = {
            'bg': bs.newnode(
                'image',
                attrs={
                    'texture': self.bg_tex,
                    'absolute_scale': True,
                    'vr_depth': 5,
                    'scale': (400, 50),
                    'color': self.color,
                    'opacity': 0.6,
                    'attach': 'centerLeft',
                },
            ),
            'tex': bs.newnode(
                'image',
                attrs={
                    'texture': self.tex,
                    'absolute_scale': True,
                    'vr_depth': 5,
                    'scale': (45, 45),
                    'color': (1, 1, 1),
                    'opacity': 1,
                    'attach': 'centerLeft',
                },
            ),
            'badge_outline': bs.newnode(
                'image',
                attrs={
                    'texture': self.outline,
                    'absolute_scale': True,
                    'vr_depth': 5,
                    'scale': (50, 50),
                    'color': self.color,
                    'opacity': 1,
                    'attach': 'centerLeft',
                },
            ),
            'title': bs.newnode(
                'text',
                attrs={
                    'text': self.name,
                    'maxwidth': 240,
                    'h_attach': 'left',
                    'h_align': 'left',
                    'v_attach': 'center',
                    'v_align': 'center',
                    'vr_depth': 10,
                    'color': (1.4, 1.4, 1.4),
                    'scale': 1,
                },
            ),
            'desc': bs.newnode(
                'text',
                attrs={
                    'text': self.text,
                    'maxwidth': 280,
                    'h_attach': 'left',
                    'h_align': 'left',
                    'v_attach': 'center',
                    'v_align': 'center',
                    'vr_depth': 10,
                    'color': (1, 1, 1),
                    'scale': 0.65,
                },
            ),
        }
        mt = bs.newnode(
            'math',
            owner=self.nodes['bg'],
            attrs={'input1': (25, 0), 'operation': 'add'},
        )
        self.nodes['bg'].connectattr('position', mt, 'input2')
        mt.connectattr('output', self.nodes['tex'], 'position')
        mt.connectattr('output', self.nodes['badge_outline'], 'position')
        mt2 = bs.newnode(
            'math',
            owner=self.nodes['bg'],
            attrs={'input1': (50, 10), 'operation': 'add'},
        )
        self.nodes['bg'].connectattr('position', mt2, 'input2')
        mt2.connectattr('output', self.nodes['title'], 'position')
        md = bs.newnode(
            'math',
            owner=self.nodes['bg'],
            attrs={'input1': (45, -10), 'operation': 'add'},
        )
        self.nodes['bg'].connectattr('position', md, 'input2')
        md.connectattr('output', self.nodes['desc'], 'position')
        bs.animate_array(
            self.nodes['bg'],
            'position',
            2,
            {0: (pos[0] - 400, pos[1]), 0.2: (pos[0], pos[1])},
            session=base,
        )
        if self.ocm is not None:
            bs.timer(0.3, bs.Call(self._overcharge, self.ocm, base))

    def _overcharge(self, ultra: bool = False, base: bool = False) -> None:
        """do the visuals for overcharged and ultracharged modes"""
        if 'bg' in self.nodes.keys():
            jitter_scale = 10 if ultra else 5
            jc = bs.newnode(
                'combine', owner=self.nodes['bg'], attrs={'size': 2}
            )
            keys = {}
            time_v = 0.0

            # Gen some random keys for that stop-motion-y look
            for _i in range(10):
                keys[time_v] = (
                    self.nodes['bg'].position[0]
                    + (random.random() - 0.5) * 0.7 * jitter_scale
                )
                time_v += random.random() * 0.1
            bs.animate(jc, 'input0', keys, loop=True, session=base)
            keys = {}
            time_v = 0.0
            for _i in range(10):
                keys[time_v * 0.86] = (
                    self.nodes['bg'].position[1]
                    + (random.random() - 0.5) * 0.7 * jitter_scale
                )
                time_v += random.random() * 0.1
            jc.connectattr('output', self.nodes['bg'], 'position')
            bs.animate(jc, 'input1', keys, loop=True, session=base)

    def _end(self) -> None:
        """This will be called when the modifier is requested to stop working"""
        if self.nodes:
            for node in self.nodes.values():
                node.delete()
            self.nodes.clear()

    def handlemessage(self, msg: Any) -> Any:
        if isinstance(msg, bs.DieMessage):
            if not self._ended:
                self._ended = True
                self._end()
        else:
            return super().handlemessage(msg)


class PunchBuffedModifier(Modifier):
    name = 'Omni-Punch'
    text = 'Increases the power scale of everyone\'s punch'
    texture = 'achievementSuperPunch'
    color = (0.5, 0, 1)

    def __init__(self, ocm: bool | None = None) -> None:
        super().__init__(ocm)
        self.conflicts = [PunchNerfedModifier]
        match ocm:
            case True:
                self.amount = 1.9
            case False:
                self.amount = 1.6
            case _:
                self.amount = 1.3
        factory = SpazFactory.get()
        factory.punch_power_scale *= self.amount
        factory.punch_power_scale_gloves *= self.amount
        self.text = (
            'Punch power increased by '
            + str(round(self.amount * 100) - 100)
            + '%'
        )

    def _end(self) -> None:
        super()._end()
        factory = SpazFactory.get()
        factory.punch_power_scale /= self.amount
        factory.punch_power_scale_gloves /= self.amount


class PunchNerfedModifier(Modifier):
    name = 'Mini-Punch'
    text = 'Decreases the power scale of everyone\'s punch'
    texture = 'achievementSuperPunch'
    color = (1, 0, 0)

    def __init__(self, ocm: bool | None = None) -> None:
        super().__init__(ocm)
        self.conflicts = [PunchBuffedModifier]
        match ocm:
            case True:
                self.amount = 0.25
            case False:
                self.amount = 0.55
            case _:
                self.amount = 0.85
        factory = SpazFactory.get()
        factory.punch_power_scale *= self.amount
        factory.punch_power_scale_gloves *= self.amount
        self.text = (
            'Punch power decreased by '
            + str(100 - round(self.amount * 100))
            + '%'
        )

    def _end(self) -> None:
        super()._end()
        factory = SpazFactory.get()
        factory.punch_power_scale /= self.amount
        factory.punch_power_scale_gloves /= self.amount


class GravityScaleModifier(Modifier):
    name = 'Low-Gravity'
    text = 'Manipulates the world\'s gravity scale'
    texture = 'powerupDev'
    color = (0.2, 0, 0.5)

    def __init__(self, ocm: bool | None = None) -> None:
        super().__init__(ocm)
        match ocm:
            case True:
                self.amount = 0.3
            case False:
                self.amount = 0.5
            case _:
                self.amount = 0.7
        self.activity.gravity_mult *= self.amount
        for node in bs.getnodes():
            if chasattr(node, 'gravity_scale'):
                node.gravity_scale *= self.amount
        self.text = str(round(self.activity.gravity_mult * 100)) + '% gravity'

    def _end(self) -> None:
        super()._end()
        self.activity.gravity_mult /= self.amount
        for node in bs.getnodes():
            if chasattr(node, 'gravity_scale'):
                node.gravity_scale /= self.amount


class NoPowerupsModifier(Modifier):
    name = 'No-Powerups'
    text = 'Does not allow any powerup boxes to spawn'
    texture = 'textClearButton'

    def __init__(self, ocm: bool | None = None) -> None:
        super().__init__()
        self.conflicts = [
            RandomPowerupFrequenciesModifier,
            ReversePowerupFrequenciesModifier,
        ]
        self.activity.allow_powerups = False
        for node in bs.getnodes():
            delegate = node.getdelegate(PowerupBox)
            if delegate:
                delegate.handlemessage(bs.DieMessage())
        self.text = 'No powerup boxes will be available'

    def _end(self) -> None:
        super()._end()
        self.activity.allow_powerups = True


class RandomPowerupFrequenciesModifier(Modifier):
    name = 'Unbalanced'
    text = 'Randomizes the frequency of all powerups'
    color = (1, 0, 1)

    def __init__(self, ocm: bool | None = None) -> None:
        super().__init__()
        self.conflicts = [NoPowerupsModifier, ReversePowerupFrequenciesModifier]
        self.text = 'All powerup frequencies have been randomized'
        PowerupBoxFactory.get().randomize_distribution()

    def _end(self) -> None:
        super()._end()
        PowerupBoxFactory.get().reset_distribution()


class ReversePowerupFrequenciesModifier(Modifier):
    name = 'Untested'
    text = 'Reverses the frequency of all powerups'
    color = (1, 1, 0)

    def __init__(self, ocm: bool | None = None) -> None:
        super().__init__()
        self.conflicts = [NoPowerupsModifier, RandomPowerupFrequenciesModifier]
        self.text = 'All powerup frequencies have been reversed'
        PowerupBoxFactory.get().reverse_distribution()

    def _end(self) -> None:
        super()._end()
        PowerupBoxFactory.get().reset_distribution()


class ConstantPowerPackModifier(Modifier):
    name = 'Gamble'
    text = 'Gives everyone a Power-Pack every few seconds'
    color = (1, 1, 0.9)
    texture = 'chestIcon'

    def __init__(self, ocm: bool | None = None) -> None:
        super().__init__(ocm)
        match ocm:
            case True:
                self.sec = 5
            case False:
                self.sec = 10
            case _:
                self.sec = random.choice((15, 20))
        self.text = (
            'Everyone receives a Power-Pack every ' + str(self.sec) + ' seconds'
        )
        self._timer = bs.Timer(self.sec, self._give, True)

    def _end(self) -> None:
        super()._end()
        self._timer = None

    def _give(self) -> None:
        for player in self.activity.players:
            if player.actor:
                player.actor.handlemessage(bs.PowerupMessage('powerups'))


class EnemyRobotModifier(Modifier):
    name = 'Third-Party'
    text = 'Spawns enemy robots every few seconds'
    color = (1, 0, 0)
    texture = 'cyborgIcon'

    def __init__(self, ocm: bool | None = None) -> None:
        super().__init__(ocm)
        match ocm:
            case True:
                self.sec = 5
            case False:
                self.sec = 15
            case _:
                self.sec = 30
        self.text = (
            'Enemy robots will spawn every ' + str(self.sec) + ' seconds'
        )
        self.activity.customdata[self.__hash__()] = SpazBotSet()
        self._timer = bs.Timer(self.sec, self._spawn, True)

    def _end(self) -> None:
        super()._end()
        self._timer = None

    def _spawn(self) -> None:
        c_raw = bs.get_player_colors()

        class TempEnemyBot(EnemyBot):
            color = random.choice(c_raw)
            highlight = random.choice(c_raw)

        self.activity.customdata[self.__hash__()].spawn_bot(
            TempEnemyBot, random.choice(self.activity.map.ffa_spawn_points)[:3]
        )


class BombBuffedModifier(Modifier):
    name = 'Super-Bombs'
    text = 'Increases the size and explosion of all bombs'
    texture = 'buttonBomb'
    color = (1, 0, 0)

    def __init__(self, ocm: bool | None = None) -> None:
        super().__init__(ocm)
        self.conflicts = [BombNerfedModifier]
        match ocm:
            case True:
                self.amount = 1.75
            case False:
                self.amount = 1.5
            case _:
                self.amount = 1.25
        factory = BombFactory.get()
        factory.bomb_scale_mult *= self.amount
        factory.blast_radius_mult *= self.amount
        factory.density_mult /= self.amount * 2
        self.text = (
            'Bomb size increased by '
            + str(round(self.amount * 100) - 100)
            + '%'
        )

    def _end(self) -> None:
        super()._end()
        factory = BombFactory.get()
        factory.bomb_scale_mult /= self.amount
        factory.blast_radius_mult /= self.amount
        factory.density_mult *= self.amount * 2


class BombNerfedModifier(Modifier):
    name = 'Mini-Bombs'
    text = 'Decreases the size and explosion of all bombs'
    texture = 'buttonBomb'
    color = (0, 0, 1)

    def __init__(self, ocm: bool | None = None) -> None:
        super().__init__()
        self.conflicts = [BombBuffedModifier]
        self.amount = 0.7
        factory = BombFactory.get()
        factory.bomb_scale_mult *= self.amount
        factory.blast_radius_mult *= self.amount
        factory.density_mult /= self.amount / 2
        self.text = (
            'Bomb size decreased by '
            + str(round((1 - self.amount) * 100))
            + '%'
        )

    def _end(self) -> None:
        super()._end()
        factory = BombFactory.get()
        factory.bomb_scale_mult /= self.amount
        factory.blast_radius_mult /= self.amount
        factory.density_mult *= self.amount / 2


class SpazRainModifier(Modifier):
    name = 'Spaz-Rain'
    text = 'Watch out for the falling Spazes!'
    texture = 'cuteSpaz'
    color = (1, 0, 0)

    def __init__(self, ocm: bool | None = None) -> None:
        super().__init__(ocm)
        match ocm:
            case True:
                self.sec = 0.1
            case False:
                self.sec = 0.5
            case _:
                self.sec = 1
        self._timer = bs.Timer(self.sec, self._spawn, True)
        self.text = 'A Spaz will fall every ' + str(self.sec) + ' seconds'

    def _end(self) -> None:
        super()._end()
        self._timer = None

    def _spawn(self) -> None:
        bounds = self.activity.map.get_def_bound_box('map_bounds')
        c_raw = bs.get_player_colors()

        pos = (
            random.uniform(bounds[0], bounds[3]) * 0.9,
            bounds[4] - 2,
            random.uniform(bounds[2], bounds[5]) * 0.9,
        )
        vel = (
            random.random() * 10 * -(pos[0] / abs(pos[0] / 3)),
            random.uniform(-3, -0.5),
            random.random() * 10 * -(pos[2] / abs(pos[2] / 3)),
        )
        spaz = Spaz(
            random.choice(c_raw),
            random.choice(c_raw),
            random.choice(get_appearances(True)),
            start_invincible=False,
            can_accept_powerups=False,
        ).autoretain()
        spaz.node.attack_sounds = []
        spaz.node.jump_sounds = []
        spaz.node.impact_sounds = []
        spaz.node.pickup_sounds = []
        spaz.node.death_sounds = []
        spaz.node.fall_sounds = []
        spaz.node.is_area_of_interest = False
        spaz.mode = bs.ProjectileActorMode
        spaz.handlemessage(bs.StandMessage(pos))
        spaz.node.handlemessage(
            'impulse', vel[0], vel[1], vel[2], 1, 1, 1, 45, 45, 0, 0, 1, 1, 1
        )


class RandomModifier(Modifier):
    name = 'Chaos'
    text = 'Random overcharged modifiers will be picked every few seconds.'
    color = (1, 0, 1)

    def __init__(self, ocm: bool | None = None) -> None:
        super().__init__(ocm)
        self.sec = 15.001  # Extra .001 to allow certain modifiers to operate
        self._timer = bs.Timer(self.sec, self._update, True)
        self.text = (
            '3 new modifiers will be selected every '
            + str(round(self.sec))
            + ' seconds'
        )

    def _end(self) -> None:
        super()._end()
        self._timer = None

    def _update(self) -> None:
        preset = list(MOD_DICT.values())
        preset.remove(self.__class__)
        random.shuffle(preset)
        preset.insert(0, self.__class__)
        if self.ocm is False:
            ocm = True
        else:
            ocm = False
        self.activity.apply_modifiers(4, preset, ocm)


class HitpointsBuffedModifier(Modifier):
    name = 'Impenetrable'
    text = 'Increases everyone\'s max hitpoints'
    texture = 'achievementStayinAlive'
    color = (0, 1, 0)

    def __init__(self, ocm: bool | None = None) -> None:
        super().__init__(ocm)
        self.conflicts = [HitpointsNerfedModifier]
        match ocm:
            case True:
                self.amount = 2
            case False:
                self.amount = 1.5
            case _:
                self.amount = 1.2
        SpazFactory.get().max_hitpoints *= self.amount
        self.text = (
            'Max hitpoints increased by '
            + str(round(self.amount * 100) - 100)
            + '%'
        )

    def _end(self) -> None:
        super()._end()
        SpazFactory.get().max_hitpoints /= self.amount


class HitpointsNerfedModifier(Modifier):
    name = 'Vulnerable'
    text = 'Decreases everyone\'s max hitpoints'
    texture = 'achievementStayinAlive'
    color = (1, 0, 0)

    def __init__(self, ocm: bool | None = None) -> None:
        super().__init__(ocm)
        self.conflicts = [HitpointsBuffedModifier]
        match ocm:
            case True:
                self.amount = 0.2
            case False:
                self.amount = 0.5
            case _:
                self.amount = 0.8
        SpazFactory.get().max_hitpoints *= self.amount
        self.text = (
            'Max hitpoints decreased by '
            + str(100 - round(self.amount * 100))
            + '%'
        )

    def _end(self) -> None:
        super()._end()
        SpazFactory.get().max_hitpoints /= self.amount


MOD_DICT = {
    'Chaos Modifier': RandomModifier,
    'Gamble Modifier': ConstantPowerPackModifier,
    'Impenetrable Modifier': HitpointsBuffedModifier,
    'Low-Gravity Modifier': GravityScaleModifier,
    'Mini-Bombs Modifier': BombNerfedModifier,
    'Mini-Punch Modifier': PunchNerfedModifier,
    'No-Powerups Modifier': NoPowerupsModifier,
    'Omni-Punch Modifier': PunchBuffedModifier,
    'Spaz-Rain Modifier': SpazRainModifier,
    'Super-Bombs Modifier': BombBuffedModifier,
    'Third-Party Modifier': EnemyRobotModifier,
    'Unbalanced Modifier': RandomPowerupFrequenciesModifier,
    'Untested Modifier': ReversePowerupFrequenciesModifier,
    'Vulnerable Modifier': HitpointsNerfedModifier,
}
