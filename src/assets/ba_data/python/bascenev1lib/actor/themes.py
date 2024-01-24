# Released under AGPL-3.0-or-later. See LICENSE for details.
#
"""Activity themes."""

import random

import bascenev1 as bs
from bascenev1lib.actor.bomb import Bomb
from bascenev1lib.actor.powerupbox import PowerupBox, PowerupBoxFactory

from typing import Sequence, Any


class Theme(bs.Actor):
    """A template for all other activity themes

    Category: Gameplay Classes
    """

    name: str = 'None'
    tint: Sequence[float] | None = None
    ambient_color: Sequence[float] | None = None
    vignette_outer: Sequence[float] | None = None
    vignette_inner: Sequence[float] | None = None
    lights: bool = True
    timer_time: float | None = None

    def __init__(
        self,
        transition: bool = False,
        bounds: list[float] | None = None,
        simple: bool = False,
    ) -> None:
        super().__init__()
        self.music_type: bs.MusicType | None = None
        self.bounds = bounds
        self.simple = simple
        if transition:
            if self.tint:
                bs.animate_array(
                    self.activity.globalsnode,
                    'tint',
                    3,
                    {0: self.activity.globalsnode.tint, 1: self.tint},
                )
            if self.ambient_color:
                bs.animate_array(
                    self.activity.globalsnode,
                    'ambient_color',
                    3,
                    {
                        0: self.activity.globalsnode.ambient_color,
                        1: self.ambient_color,
                    },
                )
            if self.vignette_outer:
                bs.animate_array(
                    self.activity.globalsnode,
                    'vignette_outer',
                    3,
                    {
                        0: self.activity.globalsnode.vignette_outer,
                        1: self.vignette_outer,
                    },
                )
            if self.vignette_inner:
                bs.animate_array(
                    self.activity.globalsnode,
                    'vignette_inner',
                    3,
                    {
                        0: self.activity.globalsnode.vignette_inner,
                        1: self.vignette_inner,
                    },
                )
        else:
            self.activity.globalsnode.tint = (
                self.tint or self.activity.globalsnode.tint
            )
            self.activity.globalsnode.ambient_color = (
                self.ambient_color or self.activity.globalsnode.ambient_color
            )
            self.activity.globalsnode.vignette_outer = (
                self.vignette_outer or self.activity.globalsnode.vignette_outer
            )
            self.activity.globalsnode.vignette_inner = (
                self.vignette_inner or self.activity.globalsnode.vignette_inner
            )

        if self.activity.light:
            self.activity.light.delete()
            self.activity.light = None
        if self.activity.light2:
            self.activity.light2.delete()
            self.activity.light2 = None
        if self.bounds:
            if self.lights:
                self.activity.light = bs.newnode(
                    'light',
                    attrs={
                        'position': (
                            self.bounds[0],
                            (self.bounds[1] + self.bounds[4]) / 2,
                            (self.bounds[2] + self.bounds[5]) / 2,
                        ),
                        'color': (0.4, 0.4, 0.45),
                        'radius': 1,
                        'intensity': 6,
                        'volume_intensity_scale': 10.0,
                        'height_attenuated': False,
                    },
                )
                self.activity.light2 = bs.newnode(
                    'light',
                    attrs={
                        'position': (
                            self.bounds[3],
                            (self.bounds[1] + self.bounds[4]) / 2,
                            (self.bounds[2] + self.bounds[5]) / 2,
                        ),
                        'color': (0.4, 0.4, 0.45),
                        'radius': 1,
                        'intensity': 6,
                        'volume_intensity_scale': 10.0,
                        'height_attenuated': False,
                    },
                )
            if self.timer_time and not self.simple:
                self._timer = bs.Timer(self.timer_time, self._update, True)

    def _update(self) -> None:
        """Gets called whenever the theme is supposed to "interact" with the
        game, this usually means throwing bombs or powerups"""

    def handlemessage(self, msg: Any) -> Any:
        if isinstance(msg, bs.DieMessage):
            self._timer = None
        else:
            return super().handlemessage(msg)

    def overtime(self) -> None:
        if self.bounds and self.timer_time and not self.simple:
            self._timer = bs.Timer(self.timer_time / 2, self._update, True)


class NoneTheme(Theme):
    lights = False

    @classmethod
    def adapt(cls) -> None:
        gnode = bs.getactivity().globalsnode
        cls.tint = gnode.tint
        cls.ambient_color = gnode.ambient_color
        cls.vignette_outer = gnode.vignette_outer
        cls.vignette_inner = gnode.vignette_inner


class AtTheEndOfTimeTheme(Theme):
    name = 'At The End of Time'
    tint = (0.3, 0.5, 0.8)
    ambient_color = (0, 0, 1)
    vignette_outer = (0.7, 0.65, 0.75)
    vignette_inner = (0.95, 0.95, 0.93)
    timer_time = 2.5

    def __init__(
        self,
        transition: bool = False,
        bounds: list[float] | None = None,
        simple: bool = False,
    ) -> None:
        super().__init__(transition, bounds, simple)
        if not bs.app.config.get('Vanillaclocked', False):
            self.music_type = bs.MusicType.TWO_O_ONE_X

    def _update(self) -> None:
        pos = (
            random.uniform(self.bounds[0], self.bounds[3]),
            self.bounds[4],
            random.uniform(self.bounds[2], self.bounds[5]),
        )
        dropdirx = -(pos[0] / abs(pos[0] / 3))
        dropdirz = -(pos[2] / abs(pos[2] / 3))
        vel = (
            random.random() * dropdirx,
            random.uniform(-0.5, -3),
            random.random() * dropdirz,
        )
        choice = random.choice(
            ['bomb', 'bomb', 'powerup', 'powerup', 'powerup']
        )
        if choice == 'bomb':
            Bomb(
                position=pos,
                velocity=vel,
                bomb_type=random.choice(
                    [
                        'normal',
                        'sticky',
                        'ice',
                        'impact',
                        'icepact',
                        'land_mine',
                        'tnt',
                        'impulse',
                    ]
                ),
                gravity_scale=0,
            ).autoretain()
        elif choice == 'powerup':
            PowerupBox(
                pos,
                PowerupBoxFactory.get().get_random_powerup_type(),
                False,
                vel,
                0,
            ).autoretain()


class CruelNightTheme(Theme):
    name = 'Cruel Night'
    tint = (0.47, 0.47, 0.47)
    ambient_color = (0, 0, 0)
    vignette_outer = (0.8, 0.8, 0.8)
    vignette_inner = (0.9, 0.9, 0.9)
    timer_time = 6.0

    def __init__(
        self,
        transition: bool = False,
        bounds: list[float] | None = None,
        simple: bool = False,
    ) -> None:
        super().__init__(transition, bounds, simple)
        if not bs.app.config.get('Vanillaclocked', False):
            self.music_type = bs.MusicType.BROKEN

    def _update(self) -> None:
        pos = (
            random.uniform(self.bounds[0], self.bounds[3]),
            self.bounds[4],
            random.uniform(self.bounds[2], self.bounds[5]),
        )
        dropdirx = -(pos[0] / abs(pos[0]))
        dropdirz = -(pos[2] / abs(pos[2]))
        forcex = (self.bounds[0] - self.bounds[3]) / abs(
            self.bounds[0] - self.bounds[3]
        )
        forcez = (self.bounds[2] - self.bounds[5]) / abs(
            self.bounds[2] - self.bounds[5]
        )
        vel = (
            (-5 + random.random() * forcex) * dropdirx,
            random.uniform(-3.066, -4.12),
            (-5 + random.random() * forcez) * dropdirz,
        )
        Bomb(position=pos, velocity=vel, bomb_type='normal').autoretain()


class AutumnTheme(Theme):
    name = 'Autumn'
    tint = (1, 0.7, 0.5)
    ambient_color = (1, 0.7, 0)
    vignette_outer = (0.7, 0.65, 0.75)
    vignette_inner = (0.95, 0.95, 0.93)
    timer_time = 5.0

    def __init__(
        self,
        transition: bool = False,
        bounds: list[float] | None = None,
        simple: bool = False,
    ) -> None:
        super().__init__(transition, bounds, simple)
        if not bs.app.config.get('Vanillaclocked', False):
            self.music_type = bs.MusicType.DONT_SMOKE_MY_WEED

    def _update(self) -> None:
        pos = (
            random.uniform(self.bounds[0], self.bounds[3]),
            self.bounds[4],
            random.uniform(self.bounds[2], self.bounds[5]),
        )
        dropdirx = -(pos[0] / abs(pos[0]))
        dropdirz = -(pos[2] / abs(pos[2]))
        vel = (
            random.random() * dropdirx,
            random.uniform(-0.5, -1),
            random.random() * dropdirz,
        )
        PowerupBox(
            pos,
            PowerupBoxFactory.get().get_random_powerup_type(),
            False,
            vel,
            0,
        ).autoretain()


class AtTheEndOfSpaceTheme(Theme):
    name = 'At The End of Space'
    tint = (0.8, 0.2, 0.032)
    ambient_color = (1, 0, 0)
    vignette_outer = (0.8, 0.7, 0.7)
    vignette_inner = (1, 0.9, 0.9)
    timer_time = 1.0

    def __init__(
        self,
        transition: bool = False,
        bounds: list[float] | None = None,
        simple: bool = False,
    ) -> None:
        super().__init__(transition, bounds, simple)
        if not bs.app.config.get('Vanillaclocked', False):
            self.music_type = bs.MusicType.EVENING_BUMP

    def _update(self) -> None:
        ranchoice = random.choice(['x', 'y'])
        pos = (
            (
                random.choice([self.bounds[0], self.bounds[3]]),
                random.uniform(self.bounds[1], self.bounds[4]),
                random.uniform(self.bounds[2], self.bounds[5]),
            )
            if ranchoice == 'x'
            else (
                random.uniform(self.bounds[0], self.bounds[3]),
                random.uniform(self.bounds[1], self.bounds[4]),
                random.choice([self.bounds[2], self.bounds[5]]),
            )
        )
        dropdirx = -(pos[0] / abs(pos[0] / 5))
        dropdirz = -(pos[2] / abs(pos[2] / 5))
        vel = (dropdirx, 0, 0) if ranchoice == 'x' else (0, 0, dropdirz)
        choice = random.randint(0, 1)
        mat = bs.Material()
        mat.add_actions(actions=('modify_part_collision', 'collide', False))
        objtype = 'powerup'
        mesh = bs.getmesh('powerup')
        btype = None
        if choice == 1:
            objtype = 'bomb'
            btype = random.choice(
                [
                    'normal',
                    'sticky',
                    'ice',
                    'impact',
                    'icepact',
                    'land_mine',
                    'tnt',
                    'impulse',
                ],
            )
            if btype == 'sticky':
                mesh = bs.getmesh('bombSticky')
            elif btype in ('impact', 'icepact'):
                mesh = bs.getmesh('impactBomb')
            elif btype == 'land_mine':
                mesh = bs.getmesh('landMine')
            elif btype == 'tnt':
                mesh = bs.getmesh('tnt')
            elif btype == 'impulse':
                mesh = bs.getmesh('powerup')
            else:
                if btype not in ('normal', 'ice'):
                    print('invalid btype, using fallback')
                mesh = bs.getmesh('bomb')
        if choice == 1 or (choice == 0 and self.activity.allow_powerups):
            prop = bs.newnode(
                'prop',
                attrs={
                    'body': 'box',
                    'position': pos,
                    'mesh': mesh,
                    'color_texture': bs.gettexture('white'),
                    'materials': [mat],
                    'gravity_scale': 0,
                },
            )
            bs.animate(prop, 'mesh_scale', {0: 0, 1: 1})
            bs.timer(1, prop.delete)
            bs.timer(
                1, bs.Call(self.delayed_obj_spawn, objtype, pos, vel, btype)
            )

    def delayed_obj_spawn(
        self,
        objtype: str,
        pos: tuple,
        vel: tuple,
        btype: str | None = None,
    ) -> None:
        if objtype == 'bomb':
            Bomb(pos, vel, btype, gravity_scale=0, anim=False).autoretain()
        elif objtype == 'powerup':
            PowerupBox(
                pos,
                PowerupBoxFactory.get().get_random_powerup_type(),
                False,
                vel,
                0,
                False,
            ).autoretain()


class UnderTheSakuraTheme(Theme):
    name = 'Under The Sakura'
    tint = (0.9, 0.5, 0.7)
    ambient_color = (1, 0, 1)
    vignette_outer = (0.7, 0.65, 0.75)
    vignette_inner = (0.95, 0.95, 0.93)
    timer_time = 5.0

    def __init__(
        self,
        transition: bool = False,
        bounds: list[float] | None = None,
        simple: bool = False,
    ) -> None:
        super().__init__(transition, bounds, simple)
        if False:
            self.music_type = bs.MusicType.NIGHT_TIME_CHILL

    def _update(self) -> None:
        pos = (
            random.uniform(self.bounds[0], self.bounds[3]),
            self.bounds[4],
            random.uniform(self.bounds[2], self.bounds[5]),
        )
        dropdirx = -(pos[0] / abs(pos[0]))
        dropdirz = -(pos[2] / abs(pos[2]))
        vel = (
            random.random() * dropdirx,
            random.uniform(-0.5, -1),
            random.random() * dropdirz,
        )
        PowerupBox(
            pos,
            PowerupBoxFactory.get().get_random_powerup_type(),
            False,
            vel,
            0,
        ).autoretain()


class MintyToxicityTheme(Theme):
    name = 'Minty Toxicity'
    tint = (0.5, 1, 0.7)
    ambient_color = (0, 1, 0)
    vignette_outer = (0.7, 0.65, 0.75)
    vignette_inner = (0.95, 0.95, 0.93)
    timer_time = 2.0

    def _update(self) -> None:
        ranchoice = random.choice(['x', 'y'])
        pos = (
            (
                random.choice([self.bounds[0], self.bounds[3]]),
                self.bounds[1] + 1,
                random.uniform(self.bounds[2], self.bounds[5]),
            )
            if ranchoice == 'x'
            else (
                random.uniform(self.bounds[0], self.bounds[3]),
                self.bounds[1] + 1,
                random.choice([self.bounds[2], self.bounds[5]]),
            )
        )
        lpos = (pos[0] / abs(pos[0]), -1, pos[2] / abs(pos[2]))
        sbomb = Bomb(
            position=pos, velocity=(0, 0, 0), bomb_type='sticky'
        ).autoretain()
        avgabs3 = (
            abs(self.bounds[0] - self.bounds[3])
            + abs(self.bounds[1] - self.bounds[4])
            + abs(self.bounds[2] - self.bounds[5])
        )
        sbomb.node.handlemessage(
            'impulse',
            pos[0] + lpos[0],
            pos[1] + lpos[1],
            pos[2] + lpos[2],
            0,
            0,
            0,
            min(100 * avgabs3, 5000),
            0,
            3,
            0,
            0,
            0,
            0,
        )


class DarkestHourTheme(Theme):
    name = 'Darkest Hour'
    tint = (0.1, 0.1, 0.1)
    ambient_color = (0, 0, 0)
    vignette_outer = (0, 0, 0)
    vignette_inner = (0, 0, 0)
    lights = False


THEME_DICT = {
    'At-The-End-of-Space Theme': AtTheEndOfSpaceTheme,
    'At-The-End-of-Time Theme': AtTheEndOfTimeTheme,
    'Autumn Theme': AutumnTheme,
    'Cruel-Night Theme': CruelNightTheme,
    'Minty-Toxicity Theme': MintyToxicityTheme,
    'Under-The-Sakura Theme': UnderTheSakuraTheme,
}
