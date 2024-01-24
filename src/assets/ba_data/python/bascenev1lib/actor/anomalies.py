# Released under AGPL-3.0-or-later. See LICENSE for details.
#
"""Classes for anomaly objects."""

from __future__ import annotations
from typing import TYPE_CHECKING

import math
import random

import bascenev1 as bs
from era.utils import chasattr
from bauiv1 import SpecialChar, charstr
from bascenev1lib.actor.spaz import Spaz
from bascenev1lib.actor.spazbot import SpazBot
from bascenev1lib.gameutils import SharedObjects
from bascenev1lib.actor.playerspaz import PlayerSpaz
from bascenev1lib.actor.powerupbox import PowerupBoxFactory

if TYPE_CHECKING:
    from typing import Any, Sequence


class Portal(bs.Actor):
    """A single portal, will be connected to another one to allow certain nodes
    to travel through.

    category: Gameplay Classes
    """

    def __init__(
        self,
        position: Sequence[float] = (0.0, 0.0, 0.0),
        radius: float = 1.0,
        spaz_only: bool = True,
        source_player: bs.Player | None = None,
        color: Sequence[float] = random.choice(bs.get_player_colors()),
        pair: Portal | None = None,
    ):
        super().__init__()
        self._source_player = source_player
        self._starttime = bs.time()
        shared = SharedObjects.get()
        portal_material = bs.Material()
        portal_material.add_actions(
            conditions=('they_have_material', shared.object_material),
            actions=('modify_part_collision', 'collide', True),
        )
        portal_material.add_actions(
            actions=(
                ('modify_part_collision', 'physical', False),
                ('call', 'at_connect', self.tp),
                ('call', 'at_disconnect', self.notice),
            )
        )
        self.node = bs.newnode(
            'region',
            delegate=self,
            attrs={
                'position': position,
                'scale': (0, 0, 0),
                'type': 'sphere',
                'materials': [portal_material, shared.region_material],
            },
        )
        bs.animate_array(
            self.node,
            'scale',
            3,
            {0: (0, 0, 0), radius: (radius, radius, radius)},
        )
        self.visual_node = bs.newnode(
            'shield',
            owner=self.node,
            attrs={
                'color': color,
                'radius': 0,
            },
        )
        bs.animate(self.visual_node, 'radius', {0: 1, radius: radius + 1})
        self.node.connectattr('position', self.visual_node, 'position')
        self.spaz_only = spaz_only
        self.pair = pair
        self.ignore_list = []

    def tp(self):
        node = bs.getcollision().opposingnode
        if self.pair and node not in self.ignore_list:
            self.pair.ignore_list.append(node)
            spaz = node.getdelegate(PlayerSpaz) or node.getdelegate(SpazBot)
            if bs.time() - self._starttime < 4.0 and spaz:
                spaz.last_attacked_time = bs.time()
                spaz.last_player_attacked_by = bs.existing(self._source_player)
                spaz.last_attacked_type = ('explosion', 'portal')
            if not self.spaz_only:
                try:
                    node.position = self.pair.node.position
                except RuntimeError:
                    node.handlemessage(bs.StandMessage(self.pair.node.position))
            else:
                node.handlemessage(bs.StandMessage(self.pair.node.position))

    def notice(self):
        try:
            node = bs.getcollision().opposingnode
            if node in self.ignore_list:
                self.ignore_list.remove(node)
        except bs.NodeNotFoundError:
            nodes = bs.getnodes()
            for node in self.ignore_list:
                if node not in nodes:
                    self.ignore_list.remove(node)

    def handlemessage(self, msg: Any) -> Any:
        if isinstance(msg, bs.DieMessage):
            self.pair = None
            if self.node:
                if msg.immediate:
                    self.node.delete()
                else:
                    bs.animate(
                        self.visual_node,
                        'radius',
                        {0: self.node.scale[0] + 1, 0.1: 0},
                    )
                    bs.timer(0.1, self.node.delete)
        else:
            super().handlemessage(msg)


class BlackHole(bs.Actor):
    """A black hole that tries to consume and destroy all objects

    category: Gameplay Classes
    """

    def __init__(
        self,
        position: Sequence[float] = (0.0, 0.0, 0.0),
        source_player: bs.Player | None = None,
        radius: float = 10.0,
        xspeed: float = 1.0,
        ssize: float = 0.0,
    ):
        super().__init__()
        self._source_player = source_player
        shared = SharedObjects.get()
        dev_material = bs.Material()
        dev_material.add_actions(
            conditions=('they_have_material', shared.object_material),
            actions=('modify_part_collision', 'collide', True),
        )
        dev_material.add_actions(
            actions=(
                ('modify_part_collision', 'physical', False),
                ('call', 'at_connect', self.kill),
            )
        )
        self.node = bs.newnode(
            'region',
            delegate=self,
            attrs={
                'position': position,
                'scale': (0, 0, 0),
                'type': 'sphere',
                'materials': [dev_material],
            },
        )
        bs.animate_array(
            self.node,
            'scale',
            3,
            {
                0: (ssize, ssize, ssize),
                radius / xspeed: (radius / 10, radius / 10, radius / 10),
            },
        )
        un_material = bs.Material()
        un_material.add_actions(
            actions=('modify_part_collision', 'collide', False)
        )
        self.visual_node0 = bs.newnode(
            'prop',
            owner=self.node,
            attrs={
                'body': 'sphere',
                'mesh': bs.getmesh('shield'),
                'color_texture': bs.gettexture('black'),
                'shadow_size': 0,
                'reflection_scale': [0],
                'materials': [un_material],
                'gravity_scale': 0,
                'density': 0,
            },
        )
        self.visual_node0.is_area_of_interest = True
        mnode = bs.newnode(
            'math',
            owner=self.node,
            attrs={'input1': (0, 0.1, 0), 'operation': 'add'},
        )
        self.node.connectattr('position', mnode, 'input2')
        mnode.connectattr('output', self.visual_node0, 'position')
        bs.animate(
            self.visual_node0,
            'mesh_scale',
            {0: ssize, radius / xspeed: radius / 10},
        )
        self.visual_node1 = bs.newnode(
            'shield', owner=self.node, attrs={'color': (5, 5, 5)}
        )
        self.node.connectattr('position', self.visual_node1, 'position')
        bs.animate(
            self.visual_node1,
            'radius',
            {0: ssize * 2.1, radius / xspeed: radius / 10 * 2.1},
        )
        self._update_timer = bs.Timer(
            0.016666667, bs.WeakCall(self._update), True
        )
        self._dtimer: bs.Timer | None = None
        self._skid_sound = bs.getsound('gravelSkid')
        self.snode = bs.newnode(
            'sound', owner=self.node, attrs={'sound': self._skid_sound}
        )
        bs.animate(self.snode, 'volume', {0: 0, radius / xspeed: radius / 5})

    def _update(self):
        for node in bs.getnodes():
            if (
                chasattr(node, 'materials')
                and chasattr(node, 'position')
                and SharedObjects.get().object_material in node.materials
                and not (chasattr(node, 'invincible') and node.invincible)
            ):
                drct = (
                    self.node.position[0] - node.position[0],
                    self.node.position[1] - node.position[1],
                    self.node.position[2] - node.position[2],
                )
                dstnc = math.sqrt(drct[0] ** 2 + drct[1] ** 2 + drct[2] ** 2)
                cradius = self.node.scale[0] * 10
                if dstnc != 0 and dstnc <= cradius:
                    nv = (drct[0] / dstnc, drct[1] / dstnc, drct[2] / dstnc)
                    node.handlemessage(
                        'impulse',
                        node.position[0],
                        node.position[1],
                        node.position[2],
                        nv[0],
                        nv[1],
                        nv[2],
                        cradius * 2,
                        0,
                        0,
                        0,
                        nv[0],
                        nv[1],
                        nv[2],
                    )

    def kill(self):
        node = bs.getcollision().opposingnode
        spaz = node.getdelegate(PlayerSpaz) or node.getdelegate(SpazBot)
        if spaz and (
            spaz.last_player_attacked_by in (None, spaz)
            or bs.time() - spaz.last_attacked_time >= 4
        ):
            spaz.last_attacked_time = bs.time()
            spaz.last_player_attacked_by = bs.existing(self._source_player)
            spaz.last_attacked_type = ('explosion', 'dev')
        light = bs.newnode(
            'light',
            attrs={
                'position': node.position,
                'height_attenuated': False,
                'color': (1, 0, 0),
                'intensity': 20,
            },
        )
        bs.animate(light, 'radius', {0: 0, 0.1: 0.1, 0.2: 0.1, 0.3: 0})
        bs.timer(0.3, light.delete)
        node.handlemessage(bs.DieMessage())

    def handlemessage(self, msg: Any) -> Any:
        if isinstance(msg, bs.DieMessage):
            if self.node:
                if msg.immediate:
                    self.node.delete()
                else:
                    bs.animate(
                        self.visual_node0,
                        'mesh_scale',
                        {
                            0: self.visual_node0.mesh_scale,
                            0.1: 0,
                            0.2: 0.25,
                            0.3: 0.25,
                            0.4: 0,
                        },
                    )
                    bs.animate(
                        self.visual_node1,
                        'radius',
                        {
                            0: self.visual_node1.radius,
                            0.1: 0,
                            0.2: 0.5,
                            0.3: 0.5,
                            0.4: 0,
                        },
                    )
                    bs.animate(
                        self.snode, 'volume', {0: self.snode.volume, 0.1: 0}
                    )
                    bs.timer(0.4, self.last_breath)
                    bs.timer(0.4, self.node.delete)
                self._update_timer = None
        else:
            super().handlemessage(msg)

    def last_breath(self):
        self._dtimer = bs.Timer(
            0.016666667,
            bs.Call(
                bs.emitfx,
                self.node.position,
                count=100,
                spread=6,
                emit_type='distortion',
            ),
            True,
        )
        from bascenev1lib.actor.bomb import Blast

        Blast(self.node.position, blast_type='tnt', hit_subtype='tnt')
        bs.timer(1, bs.Call(self.__setattr__, '_dtimer', None))


class GravityBox(bs.Actor):
    """A box that changes its gravity_scale based on how many people hold it

    category: Gameplay Classes
    """

    def __init__(
        self,
        position: Sequence[float] = (0.0, 0.0, 0.0),
        velocity: Sequence[float] = (0.0, 0.0, 0.0),
        xg: float = -1.0,
    ):
        super().__init__()
        self._xg = xg
        self._held_count: int = 0
        shared = SharedObjects.get()
        factory = PowerupBoxFactory.get()
        self.node = bs.newnode(
            'prop',
            delegate=self,
            attrs={
                'body': 'box',
                'position': position,
                'velocity': velocity,
                'mesh': factory.mesh,
                'light_mesh': factory.mesh_simple,
                'color_texture': bs.gettexture('upButton'),
                'materials': [shared.object_material],
                'gravity_scale': self.activity.gravity_mult,
            },
        )
        bs.animate(self.node, 'mesh_scale', {0: 0, 0.2: 1.3, 0.26: 1})

    def handle_gravity(self):
        if self._held_count <= 0:
            self._held_count = 0
            self.node.gravity_scale = self.activity.gravity_mult
        else:
            self.node.gravity_scale = (
                self._held_count * self._xg * self.activity.gravity_mult
            )

    def handlemessage(self, msg: Any) -> Any:
        if isinstance(msg, bs.PickedUpMessage):
            self._held_count += 1
            self.handle_gravity()
        elif isinstance(msg, bs.DroppedMessage):
            self._held_count -= 1
            self.handle_gravity()
        elif isinstance(msg, bs.DieMessage):
            if self.node:
                if msg.immediate:
                    self.node.delete()
                else:
                    bs.animate(self.node, 'mesh_scale', {0: 1, 0.1: 0})
                    bs.timer(0.1, self.node.delete)
        else:
            return super().handlemessage(msg)
        return None


class Coin(bs.Actor):
    """A coin inspired by the coin flip mechanic in ULTRAKILL

    category: Gameplay Classes
    """

    def __init__(
        self,
        position: Sequence[float] = (0.0, 0.0, 0.0),
        velocity: Sequence[float] = (0.0, 0.0, 0.0),
        vmag: int = 20,
    ):
        super().__init__()
        shared = SharedObjects.get()
        self.coin_mat = bs.Material()
        self.coin_mat.add_actions(
            conditions=('they_dont_have_material', shared.region_material),
            actions=('call', 'at_connect', self.handlecollision),
        )
        self.node = bs.newnode(
            'prop',
            delegate=self,
            attrs={
                'body': 'sphere',
                'position': position,
                'velocity': velocity,
                'mesh': bs.getmesh('puck'),
                'color_texture': bs.gettexture('white'),
                'materials': [shared.object_material, self.coin_mat],
                'gravity_scale': self.activity.gravity_mult,
            },
        )
        bs.animate(self.node, 'mesh_scale', {0: 0, 0.2: 0.6, 0.26: 0.5})
        self.light = bs.newnode(
            'light',
            owner=self.node,
            attrs={
                'radius': 0.1,
                'height_attenuated': False,
                'color': (1, 1, 0),
                'intensity': 2,
            },
        )
        self.node.connectattr('position', self.light, 'position')
        self.text: bs.Node | None = None
        self.vmag = vmag
        self._plr: bs.Player | None = None
        self._src_node: bs.Node | None = None
        self._lt: bs.Timer | None = None

    def handlemessage(self, msg: Any) -> Any:
        if isinstance(msg, bs.HitMessage):
            if msg.hit_type == 'punch':
                if not self._lt:
                    if self.text:
                        self.text.delete()
                        self.text = None
                    self._plr = None
                    self._src_node = None
                    self.node.gravity_scale = 0
                    self.node.velocity = (0, 0, 0)
                    bs.animate(
                        self.light,
                        'radius',
                        {0: 0.1, 0.2: 0.2, 0.4: 0.2, 0.6: 0.1},
                    )
                    self._lt = bs.Timer(0.6, bs.WeakCall(self._launch, msg))
            else:
                self._plr = None
                self._src_node = None
                self.node.gravity_scale = self.activity.gravity_mult
                self.node.handlemessage(
                    'impulse',
                    msg.pos[0],
                    msg.pos[1],
                    msg.pos[2],
                    msg.velocity[0],
                    msg.velocity[1],
                    msg.velocity[2],
                    msg.magnitude,
                    msg.velocity_magnitude,
                    msg.radius,
                    0,
                    msg.velocity[0],
                    msg.velocity[1],
                    msg.velocity[2],
                )
        elif isinstance(msg, bs.PickedUpMessage):
            bs.animate_array(
                self.light,
                'color',
                3,
                {0: (1, 1, 0), 0.2: (0, 0, 1), 0.4: (0, 0, 1), 0.6: (1, 1, 0)},
            )
            self._plr = None
            self._src_node = None
            self.node.gravity_scale = self.activity.gravity_mult
            m = bs.newnode(
                'math',
                owner=self.node,
                attrs={'input1': (0, 0.5, 0), 'operation': 'add'},
            )
            self.node.connectattr('position', m, 'input2')
            if self.text:
                self.text.delete()
                self.text = None
            self.text = bs.newnode(
                'text',
                owner=self.node,
                attrs={
                    'text': charstr(SpecialChar.TOP_BUTTON),
                    'in_world': True,
                    'shadow': 1.0,
                    'flatness': 1.0,
                    'scale': 0.015,
                    'h_align': 'center',
                    'v_align': 'center',
                },
            )
            bs.animate_array(
                self.text,
                'color',
                4,
                {0: (0, 0, 1, 1), 1: (0, 0, 1, 0), 2: (0, 0, 1, 1)},
                True,
            )
            m.connectattr('output', self.text, 'position')
        elif isinstance(msg, bs.DroppedMessage):
            # Eww, seems like we need to use a timer here
            bs.timer(0.001, bs.WeakCall(self._dropped))
        elif isinstance(msg, bs.DieMessage):
            if self.node:
                if msg.immediate:
                    self.node.delete()
                else:
                    bs.animate(self.node, 'mesh_scale', {0: 1, 0.3: 0})
                    bs.timer(0.3, self.node.delete)
        else:
            return super().handlemessage(msg)
        return None

    def _launch(self, msg: bs.HitMessage):
        if not self.node:
            return
        snode = None
        srcspaz = msg.srcnode.getdelegate(Spaz) if msg.srcnode else None
        srcteam = srcspaz.team if srcspaz else None
        for node in bs.getnodes():
            spaz = node.getdelegate(Spaz)
            if (
                spaz
                and spaz.is_alive()
                and spaz.team is not srcteam
                and not (
                    snode
                    and math.sqrt(
                        (snode.position[0] - self.node.position[0]) ** 2
                        + (snode.position[1] - self.node.position[1]) ** 2
                        + (snode.position[2] - self.node.position[2]) ** 2
                    )
                    < math.sqrt(
                        (node.position[0] - self.node.position[0]) ** 2
                        + (node.position[1] - self.node.position[1]) ** 2
                        + (node.position[2] - self.node.position[2]) ** 2
                    )
                )
            ):
                snode = node
        if snode:
            drct = [
                snode.position_center[0] - self.node.position[0],
                snode.position_center[1] - self.node.position[1],
                snode.position_center[2] - self.node.position[2],
            ]
            mag = math.sqrt(drct[0] ** 2 + drct[1] ** 2 + drct[2] ** 2)
            if mag != 0:
                drct = [drct[0] / mag, drct[1] / mag, drct[2] / mag]
            self.node.velocity = [
                drct[0] * self.vmag,
                drct[1] * self.vmag,
                drct[2] * self.vmag,
            ]
            self._plr = msg.get_source_player(bs.Player)
            self._src_node = msg.srcnode

    def _dropped(self) -> None:
        if not self.node:
            return
        m = bs.newnode(
            'math',
            owner=self.node,
            attrs={'input1': (0, 0.5, 0), 'operation': 'add'},
        )
        self.node.connectattr('position', m, 'input2')
        if self.text:
            self.text.delete()
            self.text = None
        self.text = bs.newnode(
            'text',
            owner=self.node,
            attrs={
                'text': charstr(SpecialChar.LEFT_BUTTON),
                'in_world': True,
                'shadow': 1.0,
                'flatness': 1.0,
                'scale': 0.015,
                'h_align': 'center',
                'v_align': 'center',
            },
        )
        bs.animate_array(
            self.text,
            'color',
            4,
            {0: (1, 1, 0, 1), 1: (1, 1, 0, 0), 2: (1, 1, 0, 1)},
            True,
        )
        m.connectattr('output', self.text, 'position')

    def handlecollision(self) -> None:
        if self._plr or self._src_node:
            bs.getcollision().opposingnode.handlemessage(
                bs.HitMessage(
                    self._src_node,
                    self.node.position,
                    self.node.velocity,
                    velocity_magnitude=15,
                    radius=0.0,
                    source_player=self._plr
                )
            )
            bs.animate_array(
                self.light, 'color', 3, {0: (1, 1, 0), 0.2: (1, 0, 0)}
            )
            self._plr = None
            self._src_node = None
            self.handlemessage(bs.DieMessage())
