# Released under AGPL-3.0-or-later. See LICENSE for details.
#
# This file incorporates work covered by the following permission notice:
#   Released under the MIT License. See LICENSE for details.
#
"""Defines the spaz actor."""
# pylint: disable=too-many-lines

from __future__ import annotations

import random
import logging
from typing import TYPE_CHECKING

from era import gdata
import bascenev1 as bs
from bascenev1lib.actor.bomb import Bomb, Blast
from bascenev1lib.gameutils import SharedObjects
from bascenev1lib.actor.popuptext import PopupText
from bascenev1lib.actor.themes import DarkestHourTheme
from bascenev1lib.actor.spazfactory import SpazFactory
from bascenev1lib.actor.powerupbox import PowerupBoxFactory, POWERUP_COLORS

if TYPE_CHECKING:
    from typing import Any, Sequence, Callable

POWERUP_WEAR_OFF_TIME = 20000

# Obsolete - just used for demo guy now.
BASE_PUNCH_POWER_SCALE = 1.2
BASE_PUNCH_COOLDOWN = 400


class PickupMessage:
    """We wanna pick something up."""


class PunchHitMessage:
    """Message saying an object was hit."""


class CurseExplodeMessage:
    """We are cursed and should blow up now."""


class BombDiedMessage:
    """A bomb has died and thus can be recycled."""


class Ammunition:
    """
    Used for our ammo system, allows storing landmines, portals, etc.
    This class should only be used for type checking
    """

    bomb_type: str

    @classmethod
    def get_texture(cls) -> bs.Texture:
        """return the ammo's texture"""


class LandmineAmmo(Ammunition):
    """Ammo for landmines"""

    bomb_type = 'land_mine'

    @classmethod
    def get_texture(cls) -> bs.Texture:
        return PowerupBoxFactory.get().tex_land_mines


class PortalAmmo(Ammunition):
    """Ammo for portals"""

    bomb_type = 'portal'

    @classmethod
    def get_texture(cls) -> bs.Texture:
        return PowerupBoxFactory.get().tex_portal


class GBoxAmmo(Ammunition):
    """Ammo for gravity boxes"""

    bomb_type = 'gravity_box'

    @classmethod
    def get_texture(cls) -> bs.Texture:
        return PowerupBoxFactory.get().tex_0g


class DevAmmo(Ammunition):
    """Ammo for black holes"""

    bomb_type = 'dev'

    @classmethod
    def get_texture(cls) -> bs.Texture:
        return PowerupBoxFactory.get().tex_dev


class CoinAmmo(Ammunition):
    """Ammo for coins"""

    bomb_type = 'coin'

    @classmethod
    def get_texture(cls) -> bs.Texture:
        return PowerupBoxFactory.get().tex_coins


class IcepactAmmo(Ammunition):
    """Ammo for ice trigger bombs"""

    bomb_type = 'icepact'

    @classmethod
    def get_texture(cls) -> bs.Texture:
        return PowerupBoxFactory.get().tex_icepact_bombs


class WonderAmmo(Ammunition):
    """Ammo for wonder bomb"""

    bomb_type = 'wonder'

    @classmethod
    def get_texture(cls) -> bs.Texture:
        return PowerupBoxFactory.get().tex_wonder


class Spaz(bs.Actor):
    """
    Base class for various Spazzes.

    Category: **Gameplay Classes**

    A Spaz is the standard little humanoid character in the game.
    It can be controlled by a player or by AI, and can have
    various different appearances.  The name 'Spaz' is not to be
    confused with the 'Spaz' character in the game, which is just
    one of the skins available for instances of this class.
    """

    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-locals

    node: bs.Node
    """The 'spaz' bs.Node."""

    points_mult = 1
    curse_time: float | None = 5.0
    default_bomb_count = 1
    default_bomb_type = 'normal'
    default_boxing_gloves = False
    default_shields = False

    def __init__(
        self,
        color: Sequence[float] = (1.0, 1.0, 1.0),
        highlight: Sequence[float] = (0.5, 0.5, 0.5),
        character: str = 'Spaz',
        source_player: bs.Player | None = None,
        start_invincible: bool = True,
        can_accept_powerups: bool = True,
        powerups_expire: bool = False,
        demo_mode: bool = False,
    ):
        """Create a spaz with the requested color, character, etc."""
        # pylint: disable=too-many-statements

        super().__init__()
        shared = SharedObjects.get()
        activity = self.activity

        factory = SpazFactory.get()

        # We need to behave slightly different in the tutorial.
        self._demo_mode = demo_mode

        self.play_big_death_sound = False

        # Scales how much impacts affect us (most damage calcs).
        self.impact_scale = 1.0

        self.source_player = source_player
        self._dead = False
        if self._demo_mode:  # Preserve old behavior.
            self._punch_power_scale = BASE_PUNCH_POWER_SCALE
        else:
            self._punch_power_scale = factory.punch_power_scale
        self.fly = bs.getactivity().globalsnode.happy_thoughts_mode
        if isinstance(activity, bs.GameActivity):
            self._hockey = activity.map.is_hockey
        else:
            self._hockey = False
        self._punched_nodes: set[bs.Node] = set()
        self._cursed = False
        self._connected_to_player: bs.Player | None = None
        self._pmat = bs.Material()
        self._pmat.add_actions(
            conditions=(
                ('they_have_material', shared.footing_material),
                'or',
                ('they_have_material', shared.object_material),
            ),
            actions=('call', 'at_connect', self._touched),
        )
        materials = [
            factory.spaz_material,
            shared.object_material,
            shared.player_material,
            self._pmat,
        ]
        roller_materials = [factory.roller_material, shared.player_material]
        extras_material = []

        if can_accept_powerups:
            pam = PowerupBoxFactory.get().powerup_accept_material
            materials.append(pam)
            roller_materials.append(pam)
            extras_material.append(pam)

        media = factory.get_media(character)
        punchmats = (factory.punch_material, shared.attack_material)
        pickupmats = (factory.pickup_material, shared.pickup_material)
        self.node: bs.Node = bs.newnode(
            type='spaz',
            delegate=self,
            attrs={
                'color': color,
                'behavior_version': 0 if demo_mode else 1,
                'demo_mode': demo_mode,
                'highlight': highlight,
                'jump_sounds': media['jump_sounds'],
                'attack_sounds': media['attack_sounds'],
                'impact_sounds': media['impact_sounds'],
                'death_sounds': media['death_sounds'],
                'pickup_sounds': media['pickup_sounds'],
                'fall_sounds': media['fall_sounds'],
                'color_texture': media['color_texture'],
                'color_mask_texture': media['color_mask_texture'],
                'head_mesh': media['head_mesh'],
                'torso_mesh': media['torso_mesh'],
                'pelvis_mesh': media['pelvis_mesh'],
                'upper_arm_mesh': media['upper_arm_mesh'],
                'forearm_mesh': media['forearm_mesh'],
                'hand_mesh': media['hand_mesh'],
                'upper_leg_mesh': media['upper_leg_mesh'],
                'lower_leg_mesh': media['lower_leg_mesh'],
                'toes_mesh': media['toes_mesh'],
                'style': factory.get_style(character),
                'fly': self.fly,
                'hockey': self._hockey,
                'materials': materials,
                'roller_materials': roller_materials,
                'extras_material': extras_material,
                'punch_materials': punchmats,
                'pickup_materials': pickupmats,
                'invincible': start_invincible,
                'source_player': source_player,
            },
        )
        self.light = bs.newnode(
            'light',
            owner=self.node,
            attrs={
                'position': (0, 0, 0),
                'color': bs.safecolor(color),
                'radius': 0.12,
                'intensity': 1,
                'volume_intensity_scale': 10.0,
                'height_attenuated': False,
            },
        )
        self.node.connectattr('position', self.light, 'position')
        self.shield: bs.Node | None = None

        if start_invincible:

            def _safesetattr(node: bs.Node | None, attr: str, val: Any) -> None:
                if node:
                    setattr(node, attr, val)

            bs.timer(1.0, self._invout)
        self.hitpoints = factory.max_hitpoints
        self.hitpoints_max = factory.max_hitpoints
        self.shield_hitpoints: int | None = None
        self.shield_hitpoints_max = 650
        self.shield_decay_rate = 0
        self.shield_decay_timer: bs.Timer | None = None
        self._boxing_gloves_wear_off_timer: bs.Timer | None = None
        self._boxing_gloves_wear_off_flash_timer: bs.Timer | None = None
        self._bomb_wear_off_timer: bs.Timer | None = None
        self._bomb_wear_off_flash_timer: bs.Timer | None = None
        self._multi_bomb_wear_off_timer: bs.Timer | None = None
        self._multi_bomb_wear_off_flash_timer: bs.Timer | None = None
        self._curse_timer: bs.Timer | None = None
        self.bomb_count = self.default_bomb_count
        self._max_bomb_count = self.default_bomb_count
        self.bomb_type_default = self.default_bomb_type
        self.bomb_type = self.bomb_type_default
        self.ammo: list[Ammunition] = []
        self.bomb_scale = 1.0
        self.bomb_density = 1.0
        self.blast_radius = 2.0
        self.powerups_expire = powerups_expire
        if self._demo_mode:  # Preserve old behavior.
            self._punch_cooldown = BASE_PUNCH_COOLDOWN
        else:
            self._punch_cooldown = factory.punch_cooldown
        self._jump_cooldown = 250
        self._pickup_cooldown = 0
        self._bomb_cooldown = 0
        self._has_boxing_gloves = False
        if self.default_boxing_gloves:
            self.equip_boxing_gloves()
        self.last_punch_time_ms = -9999
        self.last_pickup_time_ms = -9999
        self.last_jump_time_ms = -9999
        self.last_run_time_ms = -9999
        self._last_run_value = 0.0
        self.last_bomb_time_ms = -9999
        self._turbo_filter_times: dict[str, int] = {}
        self._turbo_filter_time_bucket = 0
        self._turbo_filter_counts: dict[str, int] = {}
        self.frozen = False
        self.shattered = False
        self._last_hit_time: int | None = None
        self._num_times_hit = 0
        self._bomb_held = False
        if self.default_shields:
            self.equip_shields()
        self._dropped_bomb_callbacks: list[Callable[[Spaz, bs.Actor], Any]] = []

        self._score_text: bs.Node | None = None
        self._score_text_hide_timer: bs.Timer | None = None
        self._last_stand_pos: Sequence[float] | None = None

        # Deprecated stuff.. should make these into lists.
        self.punch_callback: Callable[[Spaz], Any] | None = None
        self.pick_up_powerup_callback: Callable[[Spaz], Any] | None = None

        self.pap: bool = False
        self.pap_defence: bool = False
        self.invd: int | None = None
        self.speed: bool = False
        self._inv_wear_off_timer: bs.Timer | None = None
        self._inv_wear_off_flash_timer: bs.Timer | None = None
        self.reflect: bs.Node | None = None
        self.reflect_hitpoints: int | None = None
        self.reflect_hitpoints_max = POWERUP_WEAR_OFF_TIME / 4000
        self.reflect_decay_timer: bs.Timer | None = None
        self.deflect: bs.Node | None = None
        self.deflect_hitpoints: int | None = None
        self.deflect_hitpoints_max = POWERUP_WEAR_OFF_TIME / 1000
        self.deflect_decay_timer: bs.Timer | None = None
        self.hitpercent: float = 0
        self._btext: bs.Node | None = None
        self._play_trail_timer: bs.Timer | None = None
        self._trail_actions: dict | None = None
        self._glow_node: bs.Node | None = None

        self._rank_text: bs.Node | None = None
        self._alliance_text: bs.Node | None = None
        self._cstm_text: bs.Node | None = None
        self._league_text: bs.Node | None = None
        self._top_text: bs.Node | None = None

        self.team: bs.Team | None = None
        self.botset = None

        self._update_timer = bs.Timer(
            0.016666667, bs.WeakCall(self._update), True
        )

    def exists(self) -> bool:
        return bool(self.node)

    def on_expire(self) -> None:
        super().on_expire()

        # Release callbacks/refs so we don't wind up with dependency loops.
        self._dropped_bomb_callbacks = []
        self.punch_callback = None
        self.pick_up_powerup_callback = None

    def add_dropped_bomb_callback(
        self, call: Callable[[Spaz, bs.Actor], Any]
    ) -> None:
        """
        Add a call to be run whenever this Spaz drops a bomb.
        The spaz and the newly-dropped bomb are passed as arguments.
        """
        assert not self.expired
        self._dropped_bomb_callbacks.append(call)

    def is_alive(self) -> bool:
        """
        Method override; returns whether ol' spaz is still kickin'.
        """
        return not self._dead

    def _hide_score_text(self) -> None:
        if self._score_text:
            assert isinstance(self._score_text.scale, float)
            bs.animate(
                self._score_text,
                'scale',
                {0.0: self._score_text.scale, 0.2: 0.0},
            )

    def _turbo_filter_add_press(self, source: str) -> None:
        """
        Can pass all button presses through here; if we see an obscene number
        of them in a short time let's shame/pushish this guy for using turbo.
        """
        t_ms = int(bs.basetime() * 1000.0)
        assert isinstance(t_ms, int)
        t_bucket = int(t_ms / 1000)
        if t_bucket == self._turbo_filter_time_bucket:
            # Add only once per timestep (filter out buttons triggering
            # multiple actions).
            if t_ms != self._turbo_filter_times.get(source, 0):
                self._turbo_filter_counts[source] = (
                    self._turbo_filter_counts.get(source, 0) + 1
                )
                self._turbo_filter_times[source] = t_ms
                # (uncomment to debug; prints what this count is at)
                # bs.broadcastmessage( str(source) + " "
                #                   + str(self._turbo_filter_counts[source]))
                if self._turbo_filter_counts[source] == 15:
                    # Knock 'em out.  That'll learn 'em.
                    assert self.node
                    self.node.handlemessage('knockout', 500.0)

                    # Also issue periodic notices about who is turbo-ing.
                    now = bs.apptime()
                    assert bs.app.classic is not None
                    if now > bs.app.classic.last_spaz_turbo_warn_time + 30.0:
                        bs.app.classic.last_spaz_turbo_warn_time = now
                        bs.broadcastmessage(
                            bs.Lstr(
                                translate=(
                                    'statements',
                                    (
                                        'Warning to ${NAME}:  '
                                        'turbo / button-spamming knocks'
                                        ' you out.'
                                    ),
                                ),
                                subs=[('${NAME}', self.node.name)],
                            ),
                            color=(1, 0.5, 0),
                        )
                        bs.getsound('error').play()
        else:
            self._turbo_filter_times = {}
            self._turbo_filter_time_bucket = t_bucket
            self._turbo_filter_counts = {source: 1}

    def set_score_text(
        self,
        text: str | bs.Lstr,
        color: Sequence[float] = (1.0, 1.0, 0.4),
        flash: bool = False,
    ) -> None:
        """
        Utility func to show a message momentarily over our spaz that follows
        him around; Handy for score updates and things.
        """
        color_fin = bs.safecolor(color)[:3]
        if not self.node:
            return
        if not self._score_text:
            start_scale = 0.0
            mnode = bs.newnode(
                'math',
                owner=self.node,
                attrs={'input1': (0, 1.4, 0), 'operation': 'add'},
            )
            self.node.connectattr('torso_position', mnode, 'input2')
            self._score_text = bs.newnode(
                'text',
                owner=self.node,
                attrs={
                    'text': text,
                    'in_world': True,
                    'shadow': 1.0,
                    'flatness': 1.0,
                    'color': color_fin,
                    'scale': 0.02,
                    'h_align': 'center',
                },
            )
            mnode.connectattr('output', self._score_text, 'position')
        else:
            self._score_text.color = color_fin
            assert isinstance(self._score_text.scale, float)
            start_scale = self._score_text.scale
            self._score_text.text = text
        if flash:
            combine = bs.newnode(
                'combine', owner=self._score_text, attrs={'size': 3}
            )
            scl = 1.8
            offs = 0.5
            tval = 0.300
            for i in range(3):
                cl1 = offs + scl * color_fin[i]
                cl2 = color_fin[i]
                bs.animate(
                    combine,
                    'input' + str(i),
                    {0.5 * tval: cl2, 0.75 * tval: cl1, 1.0 * tval: cl2},
                )
            combine.connectattr('output', self._score_text, 'color')

        bs.animate(self._score_text, 'scale', {0.0: start_scale, 0.2: 0.02})
        self._score_text_hide_timer = bs.Timer(
            1.0, bs.WeakCall(self._hide_score_text)
        )

    def on_jump_press(self) -> None:
        """
        Called to 'press jump' on this spaz;
        used by player or AI connections.
        """
        if not self.node:
            return
        t_ms = int(bs.time() * 1000.0)
        assert isinstance(t_ms, int)
        if t_ms - self.last_jump_time_ms >= self._jump_cooldown:
            self.node.jump_pressed = True
            self.last_jump_time_ms = t_ms
        self._turbo_filter_add_press('jump')

    def on_jump_release(self) -> None:
        """
        Called to 'release jump' on this spaz;
        used by player or AI connections.
        """
        if not self.node:
            return
        self.node.jump_pressed = False

    def on_pickup_press(self) -> None:
        """
        Called to 'press pick-up' on this spaz;
        used by player or AI connections.
        """
        if not self.node:
            return
        t_ms = int(bs.time() * 1000.0)
        assert isinstance(t_ms, int)
        if t_ms - self.last_pickup_time_ms >= self._pickup_cooldown:
            self.node.pickup_pressed = True
            self.last_pickup_time_ms = t_ms
        self._turbo_filter_add_press('pickup')

    def on_pickup_release(self) -> None:
        """
        Called to 'release pick-up' on this spaz;
        used by player or AI connections.
        """
        if not self.node:
            return
        self.node.pickup_pressed = False

    def on_hold_position_press(self) -> None:
        """
        Called to 'press hold-position' on this spaz;
        used for player or AI connections.
        """
        if not self.node:
            return
        self.node.hold_position_pressed = True
        self._turbo_filter_add_press('holdposition')

    def on_hold_position_release(self) -> None:
        """
        Called to 'release hold-position' on this spaz;
        used for player or AI connections.
        """
        if not self.node:
            return
        self.node.hold_position_pressed = False

    def on_punch_press(self) -> None:
        """
        Called to 'press punch' on this spaz;
        used for player or AI connections.
        """
        if not self.node or self.frozen or self.node.knockout > 0.0:
            return
        t_ms = int(bs.time() * 1000.0)
        assert isinstance(t_ms, int)
        if t_ms - self.last_punch_time_ms >= self._punch_cooldown:
            if self.punch_callback is not None:
                self.punch_callback(self)
            self._punched_nodes = set()  # Reset this.
            self.last_punch_time_ms = t_ms
            self.node.punch_pressed = True
            if not self.node.hold_node:
                bs.timer(
                    0.1,
                    bs.WeakCall(
                        self._safe_play_sound,
                        SpazFactory.get().swish_sound,
                        0.8,
                    ),
                )
        self._turbo_filter_add_press('punch')

    def _safe_play_sound(self, sound: bs.Sound, volume: float) -> None:
        """Plays a sound at our position if we exist."""
        if self.node:
            sound.play(volume, self.node.position)

    def on_punch_release(self) -> None:
        """
        Called to 'release punch' on this spaz;
        used for player or AI connections.
        """
        if not self.node:
            return
        self.node.punch_pressed = False

    def on_bomb_press(self) -> None:
        """
        Called to 'press bomb' on this spaz;
        used for player or AI connections.
        """
        if (
            not self.node
            or self._dead
            or self.frozen
            or self.node.knockout > 0.0
        ):
            return
        t_ms = int(bs.time() * 1000.0)
        assert isinstance(t_ms, int)
        if t_ms - self.last_bomb_time_ms >= self._bomb_cooldown:
            self.last_bomb_time_ms = t_ms
            self.node.bomb_pressed = True
            if not self.node.hold_node:
                self.drop_bomb()
        self._turbo_filter_add_press('bomb')

    def on_bomb_release(self) -> None:
        """
        Called to 'release bomb' on this spaz;
        used for player or AI connections.
        """
        if not self.node:
            return
        self.node.bomb_pressed = False

    def on_run(self, value: float) -> None:
        """
        Called to 'press run' on this spaz;
        used for player or AI connections.
        """
        if not self.node:
            return
        t_ms = int(bs.time() * 1000.0)
        assert isinstance(t_ms, int)
        self.last_run_time_ms = t_ms
        self.node.run = value

        # Filtering these events would be tough since its an analog
        # value, but lets still pass full 0-to-1 presses along to
        # the turbo filter to punish players if it looks like they're turbo-ing.
        if self._last_run_value < 0.01 and value > 0.99:
            self._turbo_filter_add_press('run')

        self._last_run_value = value

    def on_fly_press(self) -> None:
        """
        Called to 'press fly' on this spaz;
        used for player or AI connections.
        """
        if not self.node:
            return
        # Not adding a cooldown time here for now; slightly worried
        # input events get clustered up during net-games and we'd wind up
        # killing a lot and making it hard to fly.. should look into this.
        self.node.fly_pressed = True
        self._turbo_filter_add_press('fly')

    def on_fly_release(self) -> None:
        """
        Called to 'release fly' on this spaz;
        used for player or AI connections.
        """
        if not self.node:
            return
        self.node.fly_pressed = False

    def on_move(self, x: float, y: float) -> None:
        """
        Called to set the joystick amount for this spaz;
        used for player or AI connections.
        """
        if not self.node:
            return
        self.node.handlemessage('move', x, y)

    def on_move_up_down(self, value: float) -> None:
        """
        Called to set the up/down joystick amount on this spaz;
        used for player or AI connections.
        value will be between -32768 to 32767
        WARNING: deprecated; use on_move instead.
        """
        if not self.node:
            return
        self.node.move_up_down = value

    def on_move_left_right(self, value: float) -> None:
        """
        Called to set the left/right joystick amount on this spaz;
        used for player or AI connections.
        value will be between -32768 to 32767
        WARNING: deprecated; use on_move instead.
        """
        if not self.node:
            return
        self.node.move_left_right = value

    def on_punched(self, damage: int) -> None:
        """Called when this spaz gets punched."""

    def get_death_points(self, how: bs.DeathType) -> tuple[int, int]:
        """Get the points awarded for killing this spaz."""
        del how  # Unused.
        num_hits = float(max(1, self._num_times_hit))

        # Base points is simply 10 for 1-hit-kills and 5 otherwise.
        importance = 2 if num_hits < 2 else 1
        return (10 if num_hits < 2 else 5) * self.points_mult, importance

    def curse(self) -> None:
        """
        Give this poor spaz a curse;
        he will explode in 5 seconds.
        """
        if not self._cursed:
            factory = SpazFactory.get()
            self._cursed = True

            # Add the curse material.
            for attr in ['materials', 'roller_materials']:
                materials = getattr(self.node, attr)
                if factory.curse_material not in materials:
                    setattr(
                        self.node, attr, materials + (factory.curse_material,)
                    )

            # None specifies no time limit.
            assert self.node
            if self.curse_time is None:
                self.node.curse_death_time = -1
            else:
                # Note: curse-death-time takes milliseconds.
                tval = bs.time()
                assert isinstance(tval, (float, int))
                self.node.curse_death_time = int(
                    1000.0 * (tval + self.curse_time)
                )
                self._curse_timer = bs.Timer(
                    5.0, bs.WeakCall(self.handlemessage, CurseExplodeMessage())
                )

    def equip_boxing_gloves(self) -> None:
        """
        Give this spaz some boxing gloves.
        """
        assert self.node
        self.node.boxing_gloves = True
        self._has_boxing_gloves = True
        if self._demo_mode:  # Preserve old behavior.
            self._punch_power_scale = 1.7
            self._punch_cooldown = 300
        else:
            factory = SpazFactory.get()
            self._punch_power_scale = factory.punch_power_scale_gloves
            self._punch_cooldown = factory.punch_cooldown_gloves

    def equip_shields(self, decay: bool = False) -> None:
        """
        Give this spaz a nice energy shield.
        """

        if not self.node:
            logging.exception('Can\'t equip shields; no node.')
            return

        factory = SpazFactory.get()
        if self.shield is None:
            self.shield = bs.newnode(
                'shield',
                owner=self.node,
                attrs={'color': (0.3, 0.2, 2.0), 'radius': 1.3},
            )
            self.node.connectattr('position_center', self.shield, 'position')
        self.shield_hitpoints = self.shield_hitpoints_max = 650
        self.shield_decay_rate = factory.shield_decay_rate if decay else 0
        self.shield.hurt = 0
        factory.shield_up_sound.play(1.0, position=self.node.position)

        if self.shield_decay_rate > 0:
            self.shield_decay_timer = bs.Timer(
                0.5, bs.WeakCall(self.shield_decay), repeat=True
            )
            # So user can see the decay.
            self.shield.always_show_health_bar = True

    def shield_decay(self) -> None:
        """Called repeatedly to decay shield HP over time."""
        if self.shield:
            assert self.shield_hitpoints is not None
            self.shield_hitpoints = max(
                0, self.shield_hitpoints - self.shield_decay_rate
            )
            assert self.shield_hitpoints is not None
            self.shield.hurt = (
                1.0 - float(self.shield_hitpoints) / self.shield_hitpoints_max
            )
            if self.shield_hitpoints <= 0:
                self.shield.delete()
                self.shield = None
                self.shield_decay_timer = None
                assert self.node
                SpazFactory.get().shield_down_sound.play(
                    1.0,
                    position=self.node.position,
                )
        else:
            self.shield_decay_timer = None

    def equip_reflects(self, uptime: float = 0) -> None:
        if not self.node:
            logging.exception('Can\'t equip reflects; no node.')
            return

        factory = SpazFactory.get()
        if self.reflect is None:
            self.reflect = bs.newnode(
                'shield',
                owner=self.node,
                attrs={'color': (2.0, 0.2, 0.3), 'radius': 1.3},
            )
            self.node.connectattr('position_center', self.reflect, 'position')
        self.reflect_hitpoints = self.reflect_hitpoints_max = uptime * 50
        self.reflect.hurt = 0
        factory.shield_up_sound.play(1.0, position=self.node.position)

        if uptime > 0:
            self.reflect_decay_timer = bs.Timer(
                0.5, bs.WeakCall(self.reflect_decay), repeat=True
            )
            # So user can see the decay.
            self.reflect.always_show_health_bar = True

    def reflect_decay(self) -> None:
        if self.reflect:
            assert self.reflect_hitpoints is not None
            self.reflect_hitpoints = max(0, self.reflect_hitpoints - 25)
            assert self.reflect_hitpoints is not None
            self.reflect.hurt = (
                1.0 - float(self.reflect_hitpoints) / self.reflect_hitpoints_max
            )
            if self.reflect_hitpoints <= 0:
                self.reflect.delete()
                self.reflect = None
                self.reflect_decay_timer = None
                assert self.node
                SpazFactory.get().shield_down_sound.play(
                    1.0,
                    position=self.node.position,
                )
        else:
            self.reflect_decay_timer = None

    def equip_deflects(self, uptime: float = 0) -> None:
        if not self.node:
            logging.exception('Can\'t equip deflects; no node.')
            return

        factory = SpazFactory.get()
        if self.deflect is None:
            self.deflect = bs.newnode(
                'shield',
                owner=self.node,
                attrs={'color': (2.0, 2.0, 0.2), 'radius': 1.3},
            )
            self.node.connectattr('position_center', self.deflect, 'position')
        self.deflect_hitpoints = self.deflect_hitpoints_max = uptime * 50
        self.deflect.hurt = 0
        factory.shield_up_sound.play(1.0, position=self.node.position)

        if uptime > 0:
            self.deflect_decay_timer = bs.Timer(
                0.5, bs.WeakCall(self.deflect_decay), repeat=True
            )
            # So user can see the decay.
            self.deflect.always_show_health_bar = True

    def deflect_decay(self) -> None:
        if self.deflect:
            assert self.deflect_hitpoints is not None
            self.deflect_hitpoints = max(0, self.deflect_hitpoints - 25)
            assert self.deflect_hitpoints is not None
            self.deflect.hurt = (
                1.0 - float(self.deflect_hitpoints) / self.deflect_hitpoints_max
            )
            if self.deflect_hitpoints <= 0:
                self.deflect.delete()
                self.deflect = None
                self.deflect_decay_timer = None
                assert self.node
                SpazFactory.get().shield_down_sound.play(
                    1.0,
                    position=self.node.position,
                )
        else:
            self.deflect_decay_timer = None

    def handlemessage(self, msg: Any) -> Any:
        # pylint: disable=too-many-return-statements
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-branches
        assert not self.expired

        if isinstance(msg, bs.PickedUpMessage):
            if self.node:
                self.node.handlemessage('hurt_sound')
                self.node.handlemessage('picked_up')

            # This counts as a hit.
            self._num_times_hit += 1

        elif isinstance(msg, bs.ShouldShatterMessage):
            # Eww; seems we have to do this in a timer or it wont work right.
            # (since we're getting called from within update() perhaps?..)
            # NOTE: should test to see if that's still the case.
            bs.timer(0.001, bs.WeakCall(self.shatter))

        elif isinstance(msg, bs.ImpactDamageMessage):
            # Eww; seems we have to do this in a timer or it wont work right.
            # (since we're getting called from within update() perhaps?..)
            bs.timer(0.001, bs.WeakCall(self._hit_self, msg.intensity))

        elif isinstance(msg, bs.PowerupMessage):
            if self._dead or not self.node:
                return True
            if self.pick_up_powerup_callback is not None:
                self.pick_up_powerup_callback(self)
            name = None
            if msg.poweruptype == 'triple_bombs':
                name = 'Triple-Bombs'
                tex = PowerupBoxFactory.get().tex_bomb
                self._flash_billboard(tex)
                self.bomb_scale = 1.0
                self.bomb_density = 1.0
                self.blast_radius = 2.0
                self.set_bomb_count(3)
                if self.powerups_expire:
                    self.node.mini_billboard_1_texture = tex
                    t_ms = int(bs.time() * 1000.0)
                    assert isinstance(t_ms, int)
                    self.node.mini_billboard_1_start_time = t_ms
                    self.node.mini_billboard_1_end_time = (
                        t_ms + POWERUP_WEAR_OFF_TIME
                    )
                    self._multi_bomb_wear_off_flash_timer = bs.Timer(
                        (POWERUP_WEAR_OFF_TIME - 2000) / 1000.0,
                        bs.WeakCall(self._multi_bomb_wear_off_flash),
                    )
                    self._multi_bomb_wear_off_timer = bs.Timer(
                        POWERUP_WEAR_OFF_TIME / 1000.0,
                        bs.WeakCall(self._multi_bomb_wear_off),
                    )
            elif msg.poweruptype == 'big_bombs':
                name = 'Bigger-Bombs'
                tex = PowerupBoxFactory.get().tex_big_bombs
                self._flash_billboard(tex)
                self.set_bomb_count(self.default_bomb_count)
                self.bomb_scale = 1.25
                self.bomb_density = 0.5
                self.blast_radius = 3.0
                if self.powerups_expire:
                    self.node.mini_billboard_1_texture = tex
                    t_ms = int(bs.time() * 1000.0)
                    assert isinstance(t_ms, int)
                    self.node.mini_billboard_1_start_time = t_ms
                    self.node.mini_billboard_1_end_time = (
                        t_ms + POWERUP_WEAR_OFF_TIME
                    )
                    self._multi_bomb_wear_off_flash_timer = bs.Timer(
                        (POWERUP_WEAR_OFF_TIME - 2000) / 1000.0,
                        bs.WeakCall(self._big_bomb_wear_off_flash),
                    )
                    self._multi_bomb_wear_off_timer = bs.Timer(
                        POWERUP_WEAR_OFF_TIME / 1000.0,
                        bs.WeakCall(self._bomb_modifier_wear_off),
                    )
            elif msg.poweruptype == 'light_bombs':
                name = 'Lightweight-Bombs'
                tex = PowerupBoxFactory.get().tex_light_bombs
                self._flash_billboard(tex)
                self.set_bomb_count(self.default_bomb_count)
                self.bomb_scale = 1.0
                self.blast_radius = 2.0
                self.bomb_density = 0.75
                if self.powerups_expire:
                    self.node.mini_billboard_1_texture = tex
                    t_ms = int(bs.time() * 1000.0)
                    assert isinstance(t_ms, int)
                    self.node.mini_billboard_1_start_time = t_ms
                    self.node.mini_billboard_1_end_time = (
                        t_ms + POWERUP_WEAR_OFF_TIME
                    )
                    self._multi_bomb_wear_off_flash_timer = bs.Timer(
                        (POWERUP_WEAR_OFF_TIME - 2000) / 1000.0,
                        bs.WeakCall(self._light_bomb_wear_off_flash),
                    )
                    self._multi_bomb_wear_off_timer = bs.Timer(
                        POWERUP_WEAR_OFF_TIME / 1000.0,
                        bs.WeakCall(self._bomb_modifier_wear_off),
                    )
            elif msg.poweruptype == 'land_mines':
                name = 'Land-Mines'
                self.add_ammo(LandmineAmmo, 3)
            elif msg.poweruptype == 'impact_bombs':
                name = 'Trigger-Bombs'
                self.bomb_type = 'impact'
                tex = self._get_bomb_type_tex()
                self._flash_billboard(tex)
                if self.powerups_expire:
                    self.node.mini_billboard_2_texture = tex
                    t_ms = int(bs.time() * 1000.0)
                    assert isinstance(t_ms, int)
                    self.node.mini_billboard_2_start_time = t_ms
                    self.node.mini_billboard_2_end_time = (
                        t_ms + POWERUP_WEAR_OFF_TIME
                    )
                    self._bomb_wear_off_flash_timer = bs.Timer(
                        (POWERUP_WEAR_OFF_TIME - 2000) / 1000.0,
                        bs.WeakCall(self._bomb_wear_off_flash),
                    )
                    self._bomb_wear_off_timer = bs.Timer(
                        POWERUP_WEAR_OFF_TIME / 1000.0,
                        bs.WeakCall(self._bomb_wear_off),
                    )
            elif msg.poweruptype == 'sticky_bombs':
                name = 'Sticky-Bombs'
                self.bomb_type = 'sticky'
                tex = self._get_bomb_type_tex()
                self._flash_billboard(tex)
                if self.powerups_expire:
                    self.node.mini_billboard_2_texture = tex
                    t_ms = int(bs.time() * 1000.0)
                    assert isinstance(t_ms, int)
                    self.node.mini_billboard_2_start_time = t_ms
                    self.node.mini_billboard_2_end_time = (
                        t_ms + POWERUP_WEAR_OFF_TIME
                    )
                    self._bomb_wear_off_flash_timer = bs.Timer(
                        (POWERUP_WEAR_OFF_TIME - 2000) / 1000.0,
                        bs.WeakCall(self._bomb_wear_off_flash),
                    )
                    self._bomb_wear_off_timer = bs.Timer(
                        POWERUP_WEAR_OFF_TIME / 1000.0,
                        bs.WeakCall(self._bomb_wear_off),
                    )
            elif msg.poweruptype == 'punch':
                name = 'Boxing-Gloves'
                self._pap_wear_off()
                self._speed_wear_off()
                tex = PowerupBoxFactory.get().tex_punch
                self._flash_billboard(tex)
                self.equip_boxing_gloves()
                if self.powerups_expire and not self.default_boxing_gloves:
                    self.node.boxing_gloves_flashing = False
                    self.node.mini_billboard_3_texture = tex
                    t_ms = int(bs.time() * 1000.0)
                    assert isinstance(t_ms, int)
                    self.node.mini_billboard_3_start_time = t_ms
                    self.node.mini_billboard_3_end_time = (
                        t_ms + POWERUP_WEAR_OFF_TIME
                    )
                    self._boxing_gloves_wear_off_flash_timer = bs.Timer(
                        (POWERUP_WEAR_OFF_TIME - 2000) / 1000.0,
                        bs.WeakCall(self._gloves_wear_off_flash),
                    )
                    self._boxing_gloves_wear_off_timer = bs.Timer(
                        POWERUP_WEAR_OFF_TIME / 1000.0,
                        bs.WeakCall(self._gloves_wear_off),
                    )
            elif msg.poweruptype == 'shield':
                name = 'Energy-Shield'
                if self.reflect:
                    self.reflect.delete()
                    self.reflect = None
                    self.reflect_hitpoints = 0
                    self.reflect_decay_timer = None
                    self.equip_deflects(POWERUP_WEAR_OFF_TIME / 1000)
                elif self.deflect:
                    self.equip_deflects(POWERUP_WEAR_OFF_TIME / 1000)
                else:
                    factory = SpazFactory.get()

                    # Let's allow powerup-equipped shields to lose hp over time.
                    self.equip_shields(decay=factory.shield_decay_rate > 0)
            elif msg.poweruptype == 'curse':
                name = 'Curse'
                self.curse()
            elif msg.poweruptype == 'ice_bombs':
                name = 'Ice-Bombs'
                self.bomb_type = 'ice'
                tex = self._get_bomb_type_tex()
                self._flash_billboard(tex)
                if self.powerups_expire:
                    self.node.mini_billboard_2_texture = tex
                    t_ms = int(bs.time() * 1000.0)
                    assert isinstance(t_ms, int)
                    self.node.mini_billboard_2_start_time = t_ms
                    self.node.mini_billboard_2_end_time = (
                        t_ms + POWERUP_WEAR_OFF_TIME
                    )
                    self._bomb_wear_off_flash_timer = bs.Timer(
                        (POWERUP_WEAR_OFF_TIME - 2000) / 1000.0,
                        bs.WeakCall(self._bomb_wear_off_flash),
                    )
                    self._bomb_wear_off_timer = bs.Timer(
                        POWERUP_WEAR_OFF_TIME / 1000.0,
                        bs.WeakCall(self._bomb_wear_off),
                    )
            elif msg.poweruptype == 'health':
                name = 'Med-Pack'
                if self._cursed:
                    self._cursed = False

                    # Remove cursed material.
                    factory = SpazFactory.get()
                    for attr in ['materials', 'roller_materials']:
                        materials = getattr(self.node, attr)
                        if factory.curse_material in materials:
                            setattr(
                                self.node,
                                attr,
                                tuple(
                                    m
                                    for m in materials
                                    if m != factory.curse_material
                                ),
                            )
                    self.node.curse_death_time = 0
                self.hitpercent = max(self.hitpercent - 100, 0)
                if self.mode is bs.SmashActorMode:
                    self.set_score_text(
                        str(round(self.hitpercent)) + '%', (1, 1, 1)
                    )
                self.hitpoints = self.hitpoints_max
                self._flash_billboard(PowerupBoxFactory.get().tex_health)
                self.node.hurt = 0
                self._last_hit_time = None
                self._num_times_hit = 0
            elif msg.poweruptype == 'icepact_bombs':
                name = 'Ice-Trigger-Bombs'
                self.add_ammo(IcepactAmmo, 3)
            elif msg.poweruptype == 'impulse_bombs':
                name = 'Impulse-Bombs'
                self.bomb_type = 'impulse'
                tex = self._get_bomb_type_tex()
                self._flash_billboard(tex)
                if self.powerups_expire:
                    self.node.mini_billboard_2_texture = tex
                    t_ms = int(bs.time() * 1000.0)
                    assert isinstance(t_ms, int)
                    self.node.mini_billboard_2_start_time = t_ms
                    self.node.mini_billboard_2_end_time = (
                        t_ms + POWERUP_WEAR_OFF_TIME
                    )
                    self._bomb_wear_off_flash_timer = bs.Timer(
                        (POWERUP_WEAR_OFF_TIME - 2000) / 1000.0,
                        bs.WeakCall(self._bomb_wear_off_flash),
                    )
                    self._bomb_wear_off_timer = bs.Timer(
                        POWERUP_WEAR_OFF_TIME / 1000.0,
                        bs.WeakCall(self._bomb_wear_off),
                    )
            elif msg.poweruptype == 'pap':
                name = 'Pack-A-Punch'
                self._gloves_wear_off()
                self._speed_wear_off()
                tex = PowerupBoxFactory.get().tex_pap
                self._flash_billboard(tex)
                self.pap = True
                if self.powerups_expire:
                    self.node.mini_billboard_3_texture = tex
                    t_ms = int(bs.time() * 1000.0)
                    assert isinstance(t_ms, int)
                    self.node.mini_billboard_3_start_time = t_ms
                    self.node.mini_billboard_3_end_time = (
                        t_ms + POWERUP_WEAR_OFF_TIME
                    )
                    self._boxing_gloves_wear_off_flash_timer = bs.Timer(
                        (POWERUP_WEAR_OFF_TIME - 2000) / 1000.0,
                        bs.WeakCall(self._pap_wear_off_flash),
                    )
                    self._boxing_gloves_wear_off_timer = bs.Timer(
                        POWERUP_WEAR_OFF_TIME / 1000.0,
                        bs.WeakCall(self._pap_wear_off),
                    )
            elif msg.poweruptype == 'speed':
                name = 'Running-Shoes'
                self._gloves_wear_off()
                self._pap_wear_off()
                tex = PowerupBoxFactory.get().tex_speed
                self._flash_billboard(tex)
                self.speed = True
                if self.powerups_expire:
                    self.node.mini_billboard_3_texture = tex
                    t_ms = int(bs.time() * 1000.0)
                    assert isinstance(t_ms, int)
                    self.node.mini_billboard_3_start_time = t_ms
                    self.node.mini_billboard_3_end_time = (
                        t_ms + POWERUP_WEAR_OFF_TIME
                    )
                    self._boxing_gloves_wear_off_flash_timer = bs.Timer(
                        (POWERUP_WEAR_OFF_TIME - 2000) / 1000.0,
                        bs.WeakCall(self._speed_wear_off_flash),
                    )
                    self._boxing_gloves_wear_off_timer = bs.Timer(
                        POWERUP_WEAR_OFF_TIME / 1000.0,
                        bs.WeakCall(self._speed_wear_off),
                    )
            elif msg.poweruptype == 'inv':
                name = 'Invincibility'
                tex = PowerupBoxFactory.get().tex_inv
                self._flash_billboard(tex)
                self.invd = 1
                self.node.invincible = True
                self._inv_wear_off_flash_timer = bs.Timer(
                    (POWERUP_WEAR_OFF_TIME - 2000) / 1000.0,
                    bs.WeakCall(self._inv_wear_off_flash),
                )
                self._inv_wear_off_timer = bs.Timer(
                    POWERUP_WEAR_OFF_TIME / 1000.0,
                    bs.WeakCall(self._inv_wear_off),
                )
            elif msg.poweruptype == 'uno':
                name = 'Damage-Reflector'
                if self.shield:
                    self.shield.delete()
                    self.shield = None
                    self.shield_hitpoints = 0
                    self.shield_decay_timer = None
                    self.equip_deflects(POWERUP_WEAR_OFF_TIME / 1000)
                elif self.deflect:
                    self.equip_deflects(POWERUP_WEAR_OFF_TIME / 1000)
                else:
                    self.equip_reflects(POWERUP_WEAR_OFF_TIME / 1000)
            elif msg.poweruptype == 'portal':
                name = 'Specialized-Spaz-Teleportation-Module'
                self.add_ammo(PortalAmmo, 1)
            elif msg.poweruptype == 'dev':
                name = 'Black-Hole-Module'
                self.add_ammo(DevAmmo, 1)
            elif msg.poweruptype == '0g':
                name = 'Zero-Gravity-Box-Module'
                self.add_ammo(GBoxAmmo, 1)
            elif msg.poweruptype == 'coins':
                name = 'Coin-Modules'
                self.add_ammo(CoinAmmo, 4)
            elif msg.poweruptype == 'wonder':
                name = 'Wonder-Bombs'
                self.add_ammo(WonderAmmo, 2)
            elif msg.poweruptype == 'powerups':
                name = 'Power-Pack'
                tex = PowerupBoxFactory.get().tex_powerups
                self._flash_billboard(tex)
                self.node.mini_billboard_1_texture = tex
                t_ms = int(bs.time() * 1000.0)
                assert isinstance(t_ms, int)
                self.node.mini_billboard_1_start_time = t_ms
                self.node.mini_billboard_1_end_time = t_ms + 500
                self._multi_bomb_wear_off_flash_timer = None
                self._multi_bomb_wear_off_timer = bs.Timer(
                    0.5,
                    bs.WeakCall(self._give_random_bomb_modifier),
                )
            elif msg.poweruptype == 'bot':
                name = 'BUDDY-9000'
                if not self.botset:
                    return True
                tex = PowerupBoxFactory.get().tex_bot
                self._flash_billboard(tex)
                from bascenev1lib.actor.spazbot import EnemyBot

                class BuddyBot(EnemyBot):
                    color = self.node.color
                    highlight = self.node.highlight
                    # FIXME: shouldn't be 0
                    points_mult = 0

                def finalize(bspaz: BuddyBot):
                    if self.node.name and self.node.name_color:
                        bspaz.node.name = self.node.name.upper() + '-9000'
                        bspaz.node.name_color = self.node.name_color

                self.botset.spawn_bot(BuddyBot, self.node.position, 1, finalize)

            self.node.handlemessage('flash')
            if name and not bs.app.config.get('Disable Powerup Pop-ups', False):
                pos = self.node.position
                pt = bs.newnode(
                    'text',
                    attrs={
                        'text': name,
                        'in_world': True,
                        'shadow': 1.0,
                        'flatness': 1.0,
                        'h_align': 'center',
                        'v_align': 'center',
                    },
                )
                bs.animate(
                    pt,
                    'scale',
                    {
                        0: 0.0,
                        0.1: 0.017,
                        0.15: 0.015,
                    },
                )
                combine0 = bs.newnode(
                    'combine',
                    owner=pt,
                    attrs={'input0': pos[0], 'input2': pos[2], 'size': 3},
                )
                bs.animate(
                    combine0,
                    'input1',
                    {0: pos[1] + 1.5, 1.5: pos[1] + 2.0},
                )
                combine0.connectattr('output', pt, 'position')
                color = list(
                    bs.safecolor(POWERUP_COLORS.get(msg.poweruptype, (1, 1, 1)))
                )
                combine1 = bs.newnode(
                    'combine',
                    owner=pt,
                    attrs={
                        'input0': color[0],
                        'input1': color[1],
                        'input2': color[2],
                        'size': 4,
                    },
                )
                for i in range(3):
                    bs.animate(
                        combine1,
                        'input' + str(i),
                        {0.1: color[i], 0.2: 4.0 * color[i], 0.3: color[i]},
                    )
                bs.animate(
                    combine1,
                    'input3',
                    {0: 0, 0.2: 1, 1: 1, 1.5: 0},
                )
                combine1.connectattr('output', pt, 'color')
                bs.timer(1.5, pt.delete)

            if msg.sourcenode:
                msg.sourcenode.handlemessage(bs.PowerupAcceptMessage())
            return True

        elif isinstance(msg, bs.FreezeMessage):
            if not self.node:
                return None
            if self.node.invincible:
                SpazFactory.get().block_sound.play(
                    1.0,
                    position=self.node.position,
                )
                return None
            if self.shield:
                return None
            if not self.frozen:
                self.frozen = True
                self.node.frozen = True
                bs.timer(5.0, bs.WeakCall(self.handlemessage, bs.ThawMessage()))
                # Instantly shatter if we're already dead.
                # (otherwise its hard to tell we're dead).
                if self.hitpoints <= 0:
                    self.shatter()

        elif isinstance(msg, bs.ThawMessage):
            if self.frozen and not self.shattered and self.node:
                self.frozen = False
                self.node.frozen = False

        elif isinstance(msg, bs.HitMessage):
            if not self.node:
                return None

            if self.node.invincible:
                SpazFactory.get().block_sound.play(
                    1.0,
                    position=self.node.position,
                )
                if self.invd:
                    self.invd -= 1
                    if self.invd == 0:
                        self.invd = None
                        self._inv_wear_off_flash_timer = None
                        self._inv_wear_off_timer = None
                        self.node.invincible = False
                return True

            # If we were recently hit, don't count this as another.
            # (so punch flurries and bomb pileups essentially count as 1 hit).
            local_time = int(bs.time() * 1000.0)
            assert isinstance(local_time, int)
            if (
                self._last_hit_time is None
                or local_time - self._last_hit_time > 1000
            ):
                self._num_times_hit += 1
                self._last_hit_time = local_time

            mag = msg.magnitude * self.impact_scale
            velocity_mag = msg.velocity_magnitude * self.impact_scale
            damage_scale = 0.22

            srcp = None
            pos = msg.pos
            vel = msg.velocity
            rmag = msg.magnitude
            rvmag = msg.velocity_magnitude
            fdir = msg.force_direction
            if self.deflect:
                ls = []
                for spaz in bs.getnodes():
                    delegate = spaz.getdelegate(Spaz)
                    if (
                        delegate
                        and delegate.team != self.team
                        and not (delegate.deflect or delegate.reflect)
                    ):
                        ls.append(delegate)
                if len(ls) == 0:
                    srcp = self
                else:
                    srcp = random.choice(ls)
                    pos = (
                        (
                            srcp.node.position[0]
                            + pos[0]
                            - self.node.position[0]
                        ),
                        (
                            srcp.node.position[1]
                            + pos[1]
                            - self.node.position[1]
                        ),
                        (
                            srcp.node.position[2]
                            + pos[2]
                            - self.node.position[2]
                        ),
                    )
            elif self.reflect:
                vel = (-vel[0], -vel[1], -vel[2])
                fdir = (-fdir[0], -fdir[1], -fdir[2])
                rmag = (
                    rmag * self.reflect_hitpoints / self.reflect_hitpoints_max
                )
                rvmag = (
                    rvmag * self.reflect_hitpoints / self.reflect_hitpoints_max
                )
                if msg.srcnode:
                    srcpt = msg.srcnode.getdelegate(Spaz)
                    if srcpt and srcpt is not self:
                        srcp = srcpt
                        pos = (
                            (
                                msg.srcnode.position[0]
                                + self.node.position[0]
                                - pos[0]
                            ),
                            (
                                msg.srcnode.position[1]
                                + self.node.position[1]
                                - pos[1]
                            ),
                            (
                                msg.srcnode.position[2]
                                + self.node.position[2]
                                - pos[2]
                            ),
                        )
            if srcp:
                if srcp is self:
                    from bascenev1lib.actor.anomalies import BlackHole

                    bh = BlackHole(
                        self.node.position, msg.get_source_player(bs.Player)
                    ).autoretain()
                    bs.timer(20, bs.WeakCall(bh.handlemessage, bs.DieMessage()))

                    self.deflect.delete()
                    self.deflect = None
                    self.deflect_hitpoints = 0
                    self.deflect_decay_timer = None
                    return
                elif srcp.reflect and self.reflect:
                    self.reflect.delete()
                    self.reflect = None
                    self.reflect_hitpoints = 0
                    self.reflect_decay_timer = None
                    srcp.reflect.delete()
                    srcp.reflect = None
                    srcp.reflect_hitpoints = 0
                    srcp.reflect_decay_timer = None
                    self.handlemessage(msg)
                srcp.handlemessage(
                    bs.HitMessage(
                        pos=pos,
                        velocity=vel,
                        magnitude=rmag,
                        velocity_magnitude=rvmag,
                        radius=msg.radius,
                        srcnode=self.node,
                        source_player=self.source_player,
                        force_direction=fdir,
                        hit_type=msg.hit_type,
                        hit_subtype=msg.hit_subtype,
                    )
                )
                if self.deflect:
                    if msg.flat_damage:
                        damage = msg.flat_damage * self.impact_scale
                    else:
                        # Hit our spaz with an impulse but tell it to only
                        # return theoretical damage; not apply the impulse.
                        assert msg.force_direction is not None
                        self.node.handlemessage(
                            'impulse',
                            msg.pos[0],
                            msg.pos[1],
                            msg.pos[2],
                            msg.velocity[0],
                            msg.velocity[1],
                            msg.velocity[2],
                            mag,
                            velocity_mag,
                            msg.radius,
                            1,
                            msg.force_direction[0],
                            msg.force_direction[1],
                            msg.force_direction[2],
                        )
                        damage = damage_scale * self.node.damage

                    assert self.deflect_hitpoints is not None
                    self.deflect_hitpoints -= int(damage)
                    self.deflect.hurt = 1.0 - (
                        float(self.deflect_hitpoints)
                        / self.deflect_hitpoints_max
                    )

                    # Its a cleaner event if a hit just kills the shield
                    # without damaging the player.
                    # However, massive damage events should still be able to
                    # damage the player. This hopefully gives us a happy medium.
                    sf = SpazFactory.get()
                    max_spillover = sf.max_shield_spillover_damage
                    if self.deflect_hitpoints <= 0:
                        # FIXME: Transition out perhaps?
                        self.deflect.delete()
                        self.deflect = None
                        SpazFactory.get().shield_down_sound.play(
                            1.0,
                            position=self.node.position,
                        )

                        # Emit some cool looking sparks when the shield dies.
                        npos = self.node.position
                        bs.emitfx(
                            position=(npos[0], npos[1] + 0.9, npos[2]),
                            velocity=self.node.velocity,
                            count=random.randrange(20, 30),
                            scale=1.0,
                            spread=0.6,
                            chunk_type='spark',
                        )

                    else:
                        SpazFactory.get().shield_hit_sound.play(
                            0.5,
                            position=self.node.position,
                        )

                    # Emit some cool looking sparks on shield hit.
                    assert msg.force_direction is not None
                    bs.emitfx(
                        position=msg.pos,
                        velocity=(
                            msg.force_direction[0] * 1.0,
                            msg.force_direction[1] * 1.0,
                            msg.force_direction[2] * 1.0,
                        ),
                        count=min(30, 5 + int(damage * 0.005)),
                        scale=0.5,
                        spread=0.3,
                        chunk_type='spark',
                    )

                    # If they passed our spillover threshold,
                    # pass damage along to spaz.
                    if self.deflect_hitpoints <= -max_spillover:
                        leftover_damage = (
                            -max_spillover - self.deflect_hitpoints
                        )
                        shield_leftover_ratio = leftover_damage / damage

                        # Scale down the magnitudes applied to spaz accordingly.
                        mag *= shield_leftover_ratio
                        velocity_mag *= shield_leftover_ratio
                    else:
                        return True  # Good job shield!
                msg.magnitude -= rmag

            # If they've got a shield, deliver it to that instead.
            if self.shield:
                if msg.flat_damage:
                    damage = msg.flat_damage * self.impact_scale
                else:
                    # Hit our spaz with an impulse but tell it to only return
                    # theoretical damage; not apply the impulse.
                    assert msg.force_direction is not None
                    self.node.handlemessage(
                        'impulse',
                        msg.pos[0],
                        msg.pos[1],
                        msg.pos[2],
                        msg.velocity[0],
                        msg.velocity[1],
                        msg.velocity[2],
                        mag,
                        velocity_mag,
                        msg.radius,
                        1,
                        msg.force_direction[0],
                        msg.force_direction[1],
                        msg.force_direction[2],
                    )
                    damage = damage_scale * self.node.damage

                assert self.shield_hitpoints is not None
                self.shield_hitpoints -= int(damage)
                self.shield.hurt = (
                    1.0
                    - float(self.shield_hitpoints) / self.shield_hitpoints_max
                )

                # Its a cleaner event if a hit just kills the shield
                # without damaging the player.
                # However, massive damage events should still be able to
                # damage the player. This hopefully gives us a happy medium.
                max_spillover = SpazFactory.get().max_shield_spillover_damage
                if self.shield_hitpoints <= 0:
                    # FIXME: Transition out perhaps?
                    self.shield.delete()
                    self.shield = None
                    SpazFactory.get().shield_down_sound.play(
                        1.0,
                        position=self.node.position,
                    )

                    # Emit some cool looking sparks when the shield dies.
                    npos = self.node.position
                    bs.emitfx(
                        position=(npos[0], npos[1] + 0.9, npos[2]),
                        velocity=self.node.velocity,
                        count=random.randrange(20, 30),
                        scale=1.0,
                        spread=0.6,
                        chunk_type='spark',
                    )

                else:
                    SpazFactory.get().shield_hit_sound.play(
                        0.5,
                        position=self.node.position,
                    )

                # Emit some cool looking sparks on shield hit.
                assert msg.force_direction is not None
                bs.emitfx(
                    position=msg.pos,
                    velocity=(
                        msg.force_direction[0] * 1.0,
                        msg.force_direction[1] * 1.0,
                        msg.force_direction[2] * 1.0,
                    ),
                    count=min(30, 5 + int(damage * 0.005)),
                    scale=0.5,
                    spread=0.3,
                    chunk_type='spark',
                )

                # If they passed our spillover threshold,
                # pass damage along to spaz.
                if self.shield_hitpoints <= -max_spillover:
                    leftover_damage = -max_spillover - self.shield_hitpoints
                    shield_leftover_ratio = leftover_damage / damage

                    # Scale down the magnitudes applied to spaz accordingly.
                    mag *= shield_leftover_ratio
                    velocity_mag *= shield_leftover_ratio
                else:
                    return True  # Good job shield!
            else:
                shield_leftover_ratio = 1.0

            if self.mode is bs.SmashActorMode:
                if msg.flat_damage:
                    damage = int(
                        msg.flat_damage
                        * self.impact_scale
                        * shield_leftover_ratio
                    )
                    self.hitpercent = min(self.hitpercent + damage / 10, 999)
                else:
                    assert msg.force_direction is not None
                    self.node.handlemessage(
                        'impulse',
                        msg.pos[0],
                        msg.pos[1],
                        msg.pos[2],
                        msg.velocity[0],
                        msg.velocity[1],
                        msg.velocity[2],
                        mag,
                        velocity_mag,
                        msg.radius,
                        1,
                        msg.force_direction[0],
                        msg.force_direction[1],
                        msg.force_direction[2],
                    )
                    damage = damage_scale * self.node.damage
                    self.hitpercent = min(
                        self.hitpercent + min(damage / 20, 15), 999
                    )
                    self.node.handlemessage(
                        'impulse',
                        msg.pos[0],
                        msg.pos[1],
                        msg.pos[2],
                        msg.velocity[0] * self.hitpercent / 100,
                        msg.velocity[1] * self.hitpercent / 100,
                        msg.velocity[2] * self.hitpercent / 100,
                        mag,
                        velocity_mag,
                        msg.radius,
                        0,
                        msg.force_direction[0],
                        msg.force_direction[1],
                        msg.force_direction[2],
                    )
            elif msg.flat_damage:
                damage = int(
                    msg.flat_damage * self.impact_scale * shield_leftover_ratio
                )
            else:
                # Hit it with an impulse and get the resulting damage.
                assert msg.force_direction is not None
                self.node.handlemessage(
                    'impulse',
                    msg.pos[0],
                    msg.pos[1],
                    msg.pos[2],
                    msg.velocity[0],
                    msg.velocity[1],
                    msg.velocity[2],
                    mag,
                    velocity_mag,
                    msg.radius,
                    0,
                    msg.force_direction[0],
                    msg.force_direction[1],
                    msg.force_direction[2],
                )

                damage = int(damage_scale * self.node.damage)
            self.node.handlemessage('hurt_sound')

            # Play punch impact sound based on damage if it was a punch.
            if msg.hit_type == 'punch':
                self.on_punched(damage)

                # If damage was significant, lets show it.
                if damage >= 350:
                    assert msg.force_direction is not None
                    bs.show_damage_count(
                        '-' + str(int(damage / 10)) + '%',
                        msg.pos,
                        msg.force_direction,
                    )

                # Let's always add in a super-punch sound with boxing
                # gloves just to differentiate them.
                if msg.hit_subtype in ('super_punch', 'super_pap'):
                    SpazFactory.get().punch_sound_stronger.play(
                        1.0,
                        position=self.node.position,
                    )
                if damage >= 500:
                    sounds = SpazFactory.get().punch_sound_strong
                    sound = sounds[random.randrange(len(sounds))]
                elif damage >= 100:
                    sound = SpazFactory.get().punch_sound
                else:
                    sound = SpazFactory.get().punch_sound_weak
                sound.play(1.0, position=self.node.position)

                if (
                    msg.hit_subtype in ('super_pap', 'pap')
                    and self.hitpoints > 0
                ):
                    radius = None
                    dtype = None
                    chance_min = None
                    aps = None
                    if 250 < damage <= 500:
                        radius = damage / 10000
                        dtype = 'normal'
                        chance_min = 6
                        aps = ['heal', 'shield']
                    elif 500 < damage <= 750:
                        radius = damage / 10000
                        dtype = 'sticky'
                        chance_min = 5
                        aps = ['heal', 'shield', 'block']
                    elif 750 < damage <= 900:
                        radius = damage / 10000
                        dtype = 'impact'
                        chance_min = 5
                        aps = ['heal', 'shield']
                    elif 900 < damage < 1000:
                        radius = damage / 1000
                        dtype = 'tnt'
                        chance_min = 4
                        aps = ['shield', 'block']
                    elif 1000 <= damage:
                        radius = damage / 5000
                        dtype = 'ice'
                        chance_min = 3
                        aps = ['block']
                    if radius and dtype and chance_min and aps and self.node:
                        Blast(
                            position=self.node.position,
                            blast_radius=radius,
                            blast_type=dtype,
                            source_player=msg.get_source_player(bs.Player),
                            hit_subtype=dtype,
                        ).autoretain()
                        chance = random.randrange(1, 7)
                        if self.pap_defence and chance >= chance_min:
                            bs.emitfx(
                                position=self.node.position,
                                scale=2.0,
                                count=8,
                                spread=1.2,
                                chunk_type='spark',
                            )
                            power = random.choice(aps)
                            srcname = 'Bot'
                            if self.node.name:
                                srcname = self.node.name
                            if power == 'heal':
                                PopupText(
                                    text=srcname + ' rolled a 6 and HEALED!',
                                    color=(0.7, 0.7, 1.0, 1),
                                    scale=1.6,
                                    position=self.node.position,
                                ).autoretain()
                                self.hitpoints += self.hitpoints_max / 10
                                PopupText(
                                    text='+'
                                    + str(int(self.hitpoints_max / 100))
                                    + 'hp',
                                    color=(0, 1, 0, 1),
                                    scale=1,
                                    position=self.node.position,
                                ).autoretain()
                            elif power == 'shield':
                                PopupText(
                                    text=srcname + ' rolled a 6 and SHIELDED!',
                                    color=(0.7, 0.7, 1.0, 1),
                                    scale=1.6,
                                    position=self.node.position,
                                ).autoretain()
                                self.handlemessage(bs.PowerupMessage('shield'))
                            elif power == 'block':
                                PopupText(
                                    text=srcname + ' rolled a 6 and BLOCKED!',
                                    color=(0.7, 0.7, 1.0, 1),
                                    scale=1.6,
                                    position=self.node.position,
                                ).autoretain()
                                self.handlemessage(bs.PowerupMessage('inv'))

                # Throw up some chunks.
                assert msg.force_direction is not None
                bs.emitfx(
                    position=msg.pos,
                    velocity=(
                        msg.force_direction[0] * 0.5,
                        msg.force_direction[1] * 0.5,
                        msg.force_direction[2] * 0.5,
                    ),
                    count=min(10, 1 + int(damage * 0.0025)),
                    scale=0.3,
                    spread=0.03,
                )

                bs.emitfx(
                    position=msg.pos,
                    chunk_type='sweat',
                    velocity=(
                        msg.force_direction[0] * 1.3,
                        msg.force_direction[1] * 1.3 + 5.0,
                        msg.force_direction[2] * 1.3,
                    ),
                    count=min(30, 1 + int(damage * 0.04)),
                    scale=0.9,
                    spread=0.28,
                )

                # Momentary flash.
                hurtiness = damage * 0.003
                punchpos = (
                    msg.pos[0] + msg.force_direction[0] * 0.02,
                    msg.pos[1] + msg.force_direction[1] * 0.02,
                    msg.pos[2] + msg.force_direction[2] * 0.02,
                )
                flash_color = (1.0, 0.8, 0.4)
                light = bs.newnode(
                    'light',
                    attrs={
                        'position': punchpos,
                        'radius': 0.12 + hurtiness * 0.12,
                        'intensity': 0.3 * (1.0 + 1.0 * hurtiness),
                        'height_attenuated': False,
                        'color': flash_color,
                    },
                )
                bs.timer(0.06, light.delete)

                flash = bs.newnode(
                    'flash',
                    attrs={
                        'position': punchpos,
                        'size': 0.17 + 0.17 * hurtiness,
                        'color': flash_color,
                    },
                )
                bs.timer(0.06, flash.delete)

                sh = (
                    self.shield_hitpoints
                    if self.shield_hitpoints and self.shield
                    else 0
                )
                if damage >= self.hitpoints_max + sh and damage >= 1000:
                    activity = self._activity()
                    if activity:
                        preset = activity.active_theme.__class__
                        activity.decorate(DarkestHourTheme)
                        bs.getsound('explosion05').play()
                        bs.timer(0.2, bs.Call(activity.decorate, preset, True))

            if msg.hit_type == 'impact':
                assert msg.force_direction is not None
                bs.emitfx(
                    position=msg.pos,
                    velocity=(
                        msg.force_direction[0] * 2.0,
                        msg.force_direction[1] * 2.0,
                        msg.force_direction[2] * 2.0,
                    ),
                    count=min(10, 1 + int(damage * 0.01)),
                    scale=0.4,
                    spread=0.1,
                )
            if self.hitpoints > 0:
                # It's kinda crappy to die from impacts, so lets reduce
                # impact damage by a reasonable amount *if* it'll keep us alive.
                if msg.hit_type == 'impact' and damage >= self.hitpoints:
                    # Drop damage to whatever puts us at 10 hit points,
                    # or 200 less than it used to be whichever is greater
                    # (so it *can* still kill us if its high enough).
                    newdamage = max(damage - 200, self.hitpoints - 10)
                    damage = newdamage
                self.node.handlemessage('flash')

                # If we're holding something, drop it.
                if damage > 0.0 and self.node.hold_node:
                    self.node.hold_node = None
                if self.mode is bs.SmashActorMode:
                    self.set_score_text(
                        str(round(self.hitpercent)) + '%', (1, 1, 1)
                    )
                else:
                    self.hitpoints -= damage
                    self.node.hurt = (
                        1.0 - float(self.hitpoints) / self.hitpoints_max
                    )

                # If we're cursed, *any* damage blows us up.
                if self._cursed and damage > 0:
                    bs.timer(
                        0.05,
                        bs.WeakCall(
                            self.curse_explode, msg.get_source_player(bs.Player)
                        ),
                    )

                # If we're frozen, shatter.. otherwise die if we hit zero
                if self.frozen and (damage > 200 or self.hitpoints <= 0):
                    self.shatter()
                elif self.hitpoints <= 0:
                    self.node.handlemessage(
                        bs.DieMessage(how=bs.DeathType.IMPACT)
                    )

            # If we're dead, take a look at the smoothed damage value
            # (which gives us a smoothed average of recent damage) and shatter
            # us if its grown high enough.
            if self.hitpoints <= 0:
                damage_avg = self.node.damage_smoothed * damage_scale
                if damage_avg >= 1000:
                    self.shatter()

        elif isinstance(msg, BombDiedMessage):
            self.bomb_count += 1

        elif isinstance(msg, bs.DieMessage):
            wasdead = self._dead
            self._dead = True
            self.hitpoints = 0
            if msg.immediate:
                if self.node:
                    self.node.delete()
            elif self.node:
                self.node.hurt = 1.0
                if not wasdead:
                    if self.play_big_death_sound:
                        SpazFactory.get().single_player_death_sound.play()
                    if self.mode is bs.SmashActorMode:
                        if self.hitpercent > 25:
                            blast_type = 'tnt'
                            radius = min(self.hitpercent / 5, 20)
                        else:
                            blast_type = 'ice'
                            radius = 7.5
                        Blast(
                            self.node.position,
                            blast_radius=radius,
                            blast_type=blast_type,
                        ).autoretain()
                self.node.dead = True
                bs.timer(2.0, self.node.delete)

        elif isinstance(msg, bs.OutOfBoundsMessage):
            # By default we just die here.
            self.handlemessage(bs.DieMessage(how=bs.DeathType.FALL))

        elif isinstance(msg, bs.StandMessage):
            self._last_stand_pos = (
                msg.position[0],
                msg.position[1],
                msg.position[2],
            )
            if self.node:
                self.node.handlemessage(
                    'stand',
                    msg.position[0],
                    msg.position[1],
                    msg.position[2],
                    msg.angle,
                )

        elif isinstance(msg, CurseExplodeMessage):
            self.curse_explode()

        elif isinstance(msg, PunchHitMessage):
            if not self.node:
                return None
            node = bs.getcollision().opposingnode

            # Only allow one hit per node per punch.
            if node and (node not in self._punched_nodes):
                punch_momentum_angular = (
                    self.node.punch_momentum_angular * self._punch_power_scale
                )
                punch_power = self.node.punch_power * self._punch_power_scale

                # Ok here's the deal:  we pass along our base velocity for use
                # in the impulse damage calculations since that is a more
                # predictable value than our fist velocity, which is rather
                # erratic. However, we want to actually apply force in the
                # direction our fist is moving so it looks better. So we still
                # pass that along as a direction. Perhaps a time-averaged
                # fist-velocity would work too?.. perhaps should try that.

                # If its something besides another spaz, just do a muffled
                # punch sound.
                if node.getnodetype() != 'spaz':
                    sounds = SpazFactory.get().impact_sounds_medium
                    sound = sounds[random.randrange(len(sounds))]
                    sound.play(1.0, position=self.node.position)

                ppos = self.node.punch_position
                punchdir = self.node.punch_velocity
                vel = self.node.punch_momentum_linear

                self._punched_nodes.add(node)
                subtype = 'default'
                if self._has_boxing_gloves and self.pap:
                    subtype = 'super_pap'
                elif self._has_boxing_gloves:
                    subtype = 'super_punch'
                elif self.pap:
                    subtype = 'pap'
                node.handlemessage(
                    bs.HitMessage(
                        pos=ppos,
                        velocity=vel,
                        magnitude=punch_power * punch_momentum_angular * 110.0,
                        velocity_magnitude=punch_power * 40,
                        radius=0,
                        srcnode=self.node,
                        source_player=self.source_player,
                        force_direction=punchdir,
                        hit_type='punch',
                        hit_subtype=subtype,
                    )
                )

                # Also apply opposite to ourself for the first punch only.
                # This is given as a constant force so that it is more
                # noticeable for slower punches where it matters. For fast
                # awesome looking punches its ok if we punch 'through'
                # the target.
                mag = -400.0
                if self._hockey:
                    mag *= 0.5
                if len(self._punched_nodes) == 1:
                    self.node.handlemessage(
                        'kick_back',
                        ppos[0],
                        ppos[1],
                        ppos[2],
                        punchdir[0],
                        punchdir[1],
                        punchdir[2],
                        mag,
                    )
        elif isinstance(msg, PickupMessage):
            if not self.node:
                return None

            try:
                collision = bs.getcollision()
                opposingnode = collision.opposingnode
                opposingbody = collision.opposingbody
            except bs.NotFoundError:
                return True

            # Don't allow picking up of invincible dudes.
            try:
                if opposingnode.invincible:
                    return True
            except Exception:
                pass

            # If we're grabbing the pelvis of a non-shattered spaz, we wanna
            # grab the torso instead.
            if (
                opposingnode.getnodetype() == 'spaz'
                and not opposingnode.shattered
                and opposingbody == 4
            ):
                opposingbody = 1

            # Special case - if we're holding a flag, don't replace it
            # (hmm - should make this customizable or more low level).
            held = self.node.hold_node
            if held and held.getnodetype() == 'flag':
                return True

            # Note: hold_body needs to be set before hold_node.
            self.node.hold_body = opposingbody
            self.node.hold_node = opposingnode
        elif isinstance(msg, bs.CelebrateMessage):
            if self.node:
                self.node.handlemessage('celebrate', int(msg.duration * 1000))

        else:
            return super().handlemessage(msg)
        return None

    def drop_bomb(self) -> Bomb | None:
        """
        Tell the spaz to drop one of his bombs, and returns
        the resulting bomb object.
        If the spaz has no bombs or is otherwise unable to
        drop a bomb, returns None.
        """

        if len(self.ammo) + self.bomb_count <= 0 or self.frozen:
            return None
        assert self.node
        pos = self.node.position_forward
        vel = self.node.velocity

        if len(self.ammo) > 0:
            dropping_bomb = False
            ammo = self.ammo[-1]
            bomb_type = ammo.bomb_type
            self.ammo.remove(ammo)
            self.show_ammo_count()
        else:
            dropping_bomb = True
            bomb_type = self.bomb_type

        if bomb_type == 'gravity_box':
            from bascenev1lib.actor.anomalies import GravityBox

            bomb = GravityBox((pos[0], pos[1] + 0.5, pos[2]), vel).autoretain()
        elif bomb_type == 'coin':
            from bascenev1lib.actor.anomalies import Coin

            bomb = Coin((pos[0], pos[1] - 0.0, pos[2]), vel).autoretain()
        else:
            bomb = Bomb(
                position=(pos[0], pos[1] - 0.0, pos[2]),
                velocity=(vel[0], vel[1], vel[2]),
                bomb_type=bomb_type,
                bomb_scale=self.bomb_scale,
                density=self.bomb_density,
                blast_radius=self.blast_radius,
                source_player=self.source_player,
                owner=self.node,
            ).autoretain()

        assert bomb.node
        if dropping_bomb:
            self.bomb_count -= 1
            bomb.node.add_death_action(
                bs.WeakCall(self.handlemessage, BombDiedMessage())
            )
        self._pick_up(bomb.node)

        for clb in self._dropped_bomb_callbacks:
            clb(self, bomb)

        return bomb

    def _pick_up(self, node: bs.Node) -> None:
        if self.node:
            # Note: hold_body needs to be set before hold_node.
            self.node.hold_body = 0
            self.node.hold_node = node

    def add_ammo(self, ammo: Ammunition, count: int) -> None:
        """Add <count> ammunition of type <ammo> to our big fat pocket"""
        old_count = self.ammo.count(ammo)
        for _ in range(old_count):
            self.ammo.remove(ammo)
            self.ammo.append(ammo)
        for _ in range(count):
            self.ammo.append(ammo)
        self.show_ammo_count()

    def show_ammo_count(self) -> None:
        if self.node:
            try:
                ammo = self.ammo[-1]
                self.node.counter_text = 'x' + str(self.ammo.count(ammo))
                self.node.counter_texture = ammo.get_texture()
            except IndexError:
                self.node.counter_text = ''

    def curse_explode(self, source_player: bs.Player | None = None) -> None:
        """Explode the poor spaz spectacularly."""
        if self._cursed and self.node:
            self.shatter(extreme=True)
            self.handlemessage(bs.DieMessage())
            activity = self._activity()
            if activity:
                Blast(
                    position=self.node.position,
                    velocity=self.node.velocity,
                    blast_radius=3.0,
                    blast_type='normal',
                    source_player=(
                        source_player if source_player else self.source_player
                    ),
                ).autoretain()
            self._cursed = False

    def shatter(self, extreme: bool = False) -> None:
        """Break the poor spaz into little bits."""
        if self.shattered:
            return
        self.shattered = True
        assert self.node
        if self.frozen:
            # Momentary flash of light.
            light = bs.newnode(
                'light',
                attrs={
                    'position': self.node.position,
                    'radius': 0.5,
                    'height_attenuated': False,
                    'color': (0.8, 0.8, 1.0),
                },
            )

            bs.animate(
                light, 'intensity', {0.0: 3.0, 0.04: 0.5, 0.08: 0.07, 0.3: 0}
            )
            bs.timer(0.3, light.delete)

            # Emit ice chunks.
            bs.emitfx(
                position=self.node.position,
                velocity=self.node.velocity,
                count=int(random.random() * 10.0 + 10.0),
                scale=0.6,
                spread=0.2,
                chunk_type='ice',
            )
            bs.emitfx(
                position=self.node.position,
                velocity=self.node.velocity,
                count=int(random.random() * 10.0 + 10.0),
                scale=0.3,
                spread=0.2,
                chunk_type='ice',
            )
            SpazFactory.get().shatter_sound.play(
                1.0,
                position=self.node.position,
            )
        else:
            SpazFactory.get().splatter_sound.play(
                1.0,
                position=self.node.position,
            )
        self.handlemessage(bs.DieMessage())
        self.node.shattered = 2 if extreme else 1

    def _hit_self(self, intensity: float) -> None:
        if not self.node:
            return
        pos = self.node.position
        self.handlemessage(
            bs.HitMessage(
                flat_damage=50.0 * intensity,
                pos=pos,
                force_direction=self.node.velocity,
                hit_type='impact',
            )
        )
        self.node.handlemessage('knockout', max(0.0, 50.0 * intensity))
        sounds: Sequence[bs.Sound]
        if intensity >= 5.0:
            sounds = SpazFactory.get().impact_sounds_harder
        elif intensity >= 3.0:
            sounds = SpazFactory.get().impact_sounds_hard
        else:
            sounds = SpazFactory.get().impact_sounds_medium
        sound = sounds[random.randrange(len(sounds))]
        sound.play(position=pos, volume=5.0)

    def _get_bomb_type_tex(self) -> bs.Texture:
        factory = PowerupBoxFactory.get()
        if self.bomb_type == 'sticky':
            return factory.tex_sticky_bombs
        if self.bomb_type == 'ice':
            return factory.tex_ice_bombs
        if self.bomb_type == 'impact':
            return factory.tex_impact_bombs
        if self.bomb_type == 'impulse':
            return factory.tex_impulse_bombs
        raise ValueError('invalid bomb type')

    def _flash_billboard(self, tex: bs.Texture) -> None:
        assert self.node
        self.node.billboard_texture = tex
        self.node.billboard_cross_out = False
        bs.animate(
            self.node,
            'billboard_opacity',
            {0.0: 0.0, 0.1: 1.0, 0.4: 1.0, 0.5: 0.0},
        )

    def set_bomb_count(self, count: int) -> None:
        """Sets the number of bombs this Spaz has."""
        # We can't just set bomb_count because some bombs may be laid currently
        # so we have to do a relative diff based on max.
        diff = count - self._max_bomb_count
        self._max_bomb_count += diff
        self.bomb_count += diff

    def _gloves_wear_off_flash(self) -> None:
        if self.node:
            self.node.boxing_gloves_flashing = True
            self.node.billboard_texture = PowerupBoxFactory.get().tex_punch
            self.node.billboard_opacity = 1.0
            self.node.billboard_cross_out = True

    def _gloves_wear_off(self) -> None:
        if self._demo_mode:  # Preserve old behavior.
            self._punch_power_scale = 1.2
            self._punch_cooldown = BASE_PUNCH_COOLDOWN
        else:
            factory = SpazFactory.get()
            self._punch_power_scale = factory.punch_power_scale
            self._punch_cooldown = factory.punch_cooldown
        self._has_boxing_gloves = False
        if self.node:
            PowerupBoxFactory.get().powerdown_sound.play(
                position=self.node.position,
            )
            self.node.boxing_gloves = False
            self.node.billboard_opacity = 0.0

    def _multi_bomb_wear_off_flash(self) -> None:
        if self.node:
            self.node.billboard_texture = PowerupBoxFactory.get().tex_bomb
            self.node.billboard_opacity = 1.0
            self.node.billboard_cross_out = True

    def _multi_bomb_wear_off(self) -> None:
        self.set_bomb_count(self.default_bomb_count)
        if self.node:
            PowerupBoxFactory.get().powerdown_sound.play(
                position=self.node.position,
            )
            self.node.billboard_opacity = 0.0

    def _big_bomb_wear_off_flash(self) -> None:
        if self.node:
            self.node.billboard_texture = PowerupBoxFactory.get().tex_big_bombs
            self.node.billboard_opacity = 1.0
            self.node.billboard_cross_out = True

    def _light_bomb_wear_off_flash(self) -> None:
        if self.node:
            self.node.billboard_texture = (
                PowerupBoxFactory.get().tex_light_bombs
            )
            self.node.billboard_opacity = 1.0
            self.node.billboard_cross_out = True

    def _bomb_modifier_wear_off(self) -> None:
        self.bomb_scale = 1.0
        self.bomb_density = 1.0
        self.blast_radius = 2.0
        if self.node:
            PowerupBoxFactory.get().powerdown_sound.play(
                position=self.node.position,
            )
            self.node.billboard_opacity = 0.0

    def _bomb_wear_off_flash(self) -> None:
        if self.node:
            self.node.billboard_texture = self._get_bomb_type_tex()
            self.node.billboard_opacity = 1.0
            self.node.billboard_cross_out = True

    def _bomb_wear_off(self) -> None:
        self.bomb_type = self.bomb_type_default
        if self.node:
            PowerupBoxFactory.get().powerdown_sound.play(
                position=self.node.position,
            )
            self.node.billboard_opacity = 0.0

    def _pap_wear_off_flash(self) -> None:
        if self.node:
            self.node.billboard_texture = PowerupBoxFactory.get().tex_pap
            self.node.billboard_opacity = 1.0
            self.node.billboard_cross_out = True

    def _pap_wear_off(self) -> None:
        self.pap = False
        if self.node:
            PowerupBoxFactory.get().powerdown_sound.play(
                position=self.node.position,
            )
            self.node.billboard_opacity = 0.0

    def _inv_wear_off_flash(self) -> None:
        if self.node:
            self.node.billboard_texture = PowerupBoxFactory.get().tex_inv
            self.node.billboard_opacity = 1.0
            self.node.billboard_cross_out = True

    def _inv_wear_off(self) -> None:
        self.invd = None
        if self.node:
            self.node.invincible = False
            PowerupBoxFactory.get().powerdown_sound.play(
                position=self.node.position,
            )
            self.node.billboard_opacity = 0.0

    def _speed_wear_off_flash(self) -> None:
        if self.node:
            self.node.billboard_texture = PowerupBoxFactory.get().tex_speed
            self.node.billboard_opacity = 1.0
            self.node.billboard_cross_out = True

    def _speed_wear_off(self) -> None:
        self.speed = False
        if self.node:
            PowerupBoxFactory.get().powerdown_sound.play(
                position=self.node.position,
            )
            self.node.billboard_opacity = 0.0

    def give_ranks(
        self, show: bool, text: str, color: tuple, rainbow: bool
    ) -> None:
        if self._rank_text:
            self._rank_text.delete()
            self._rank_text = None
        if not show:
            return
        m = bs.newnode(
            'math',
            owner=self.node,
            attrs={'input1': (0, 1, 0), 'operation': 'add'},
        )
        self.node.connectattr('torso_position', m, 'input2')
        self._rank_text = bs.newnode(
            'text',
            owner=self.node,
            attrs={
                'text': text,
                'in_world': True,
                'shadow': 1.0,
                'flatness': 1.0,
                'color': color,
                'scale': 0.01,
                'h_align': 'center',
                'v_align': 'top',
            },
        )
        m.connectattr('output', self._rank_text, 'position')
        if rainbow:
            orange = (1, 0.5, 0, 1)
            yellow = (1, 1, 0, 1)
            green = (0.2, 1, 0.2, 1)
            blue = (0.1, 0.1, 1, 1)
            purple = (0.5, 0.25, 1, 1)
            bs.animate_array(
                self._rank_text,
                'color',
                4,
                {
                    0: color,
                    1: orange,
                    2: yellow,
                    3: green,
                    4: blue,
                    5: purple,
                    6: blue,
                    7: green,
                    8: yellow,
                    9: orange,
                    10: color,
                },
                True,
            )

    def give_alliances(self, show: bool, text: str, color: tuple) -> None:
        if self._alliance_text:
            self._alliance_text.delete()
            self._alliance_text = None
        if not show:
            return
        m = bs.newnode(
            'math',
            owner=self.node,
            attrs={'input1': (0, 1.7, 0), 'operation': 'add'},
        )
        self.node.connectattr('torso_position', m, 'input2')
        self._alliance_text = bs.newnode(
            'text',
            owner=self.node,
            attrs={
                'text': text,
                'in_world': True,
                'shadow': 1.0,
                'flatness': 1.0,
                'color': color,
                'scale': 0.008,
                'h_align': 'center',
                'v_align': 'bottom',
            },
        )
        m.connectattr('output', self._alliance_text, 'position')

    def give_cstms(self, text: str, color: tuple) -> None:
        if self._cstm_text:
            self._cstm_text.delete()
            self._cstm_text = None
        m = bs.newnode(
            'math',
            owner=self.node,
            attrs={'input1': (0, 1.9, 0), 'operation': 'add'},
        )
        self.node.connectattr('torso_position', m, 'input2')
        self._cstm_text = bs.newnode(
            'text',
            owner=self.node,
            attrs={
                'text': text,
                'in_world': True,
                'shadow': 1.0,
                'flatness': 1.0,
                'color': color,
                'scale': 0.008,
                'h_align': 'center',
                'v_align': 'bottom',
            },
        )
        m.connectattr('output', self._cstm_text, 'position')

    def give_leagues(self, show: bool, text: str, color: tuple) -> None:
        if self._league_text:
            self._league_text.delete()
            self._league_text = None
        if not show:
            return
        m = bs.newnode(
            'math',
            owner=self.node,
            attrs={'input1': (0, -1.2, 0), 'operation': 'add'},
        )
        self.node.connectattr('torso_position', m, 'input2')
        self._league_text = bs.newnode(
            'text',
            owner=self.node,
            attrs={
                'text': text,
                'in_world': True,
                'shadow': 1.0,
                'flatness': 1.0,
                'color': color,
                'scale': 0.0085,
                'h_align': 'center',
                'v_align': 'bottom',
            },
        )
        m.connectattr('output', self._league_text, 'position')

    def give_tops(self, show: bool, text: str, color: tuple) -> None:
        if self._top_text:
            self._top_text.delete()
            self._top_text = None
        if not show:
            return
        m = bs.newnode(
            'math',
            owner=self.node,
            attrs={'input1': (0, -1.4, 0), 'operation': 'add'},
        )
        self.node.connectattr('torso_position', m, 'input2')
        self._top_text = bs.newnode(
            'text',
            owner=self.node,
            attrs={
                'text': text,
                'in_world': True,
                'shadow': 1.0,
                'flatness': 1.0,
                'color': color,
                'scale': 0.0075,
                'h_align': 'center',
                'v_align': 'bottom',
            },
        )
        m.connectattr('output', self._top_text, 'position')

    def equip(self, equipment: list) -> None:
        gshop = gdata.getpath('gshop')
        # FIXME: this system doesnt support unequipping items
        for base in equipment:
            base = base.split('@')
            scat = base[1]
            ea = gdata.load(gshop, scat, base[0], 'eactions', update=False)
            if scat == 'trail':
                self._play_trail_timer = bs.Timer(
                    ea[len(ea) - 1],
                    bs.WeakCall(self._play, 'trail'),
                    True,
                )
                ea.pop(-1)
                self._trail_actions = ea
            if scat == 'glow':
                # FIXME: this should all be moved to _play
                rainbow = False
                if ea['color'] == 'rainbow':
                    ea['color'] = (1, 0.15, 0.15)
                    rainbow = True
                else:
                    ea['color'] = ea['color'].split()
                    for i, x in enumerate(ea['color']):
                        ea['color'][i] = float(x)
                    ea['color'] = tuple(ea['color'])
                if self._glow_node:
                    self._glow_node.delete()
                self._glow_node = bs.newnode('light', self.node, attrs=ea)
                self.node.connectattr(
                    'torso_position', self._glow_node, 'position'
                )
                if rainbow:
                    red = (1, 0.15, 0.15)
                    orange = (1, 0.5, 0)
                    yellow = (1, 1, 0)
                    green = (0.2, 1, 0.2)
                    blue = (0.1, 0.1, 1)
                    purple = (0.65, 0, 1)
                    bs.animate_array(
                        self._glow_node,
                        'color',
                        3,
                        {
                            0: red,
                            1: orange,
                            2: yellow,
                            3: green,
                            4: blue,
                            5: purple,
                            6: red,
                        },
                        True,
                    )

    def _play(self, t: str) -> None:
        ea = None
        if t == 'trail':
            ea = self._trail_actions
        try:
            for x in ea:
                if x[0] == 'emitfx':
                    x[1]['position'] = self.node.position
                    x[1]['velocity'] = (0, 0, 0)
                    bs.emitfx(**x[1])
        except AttributeError:
            self._play_trail_timer = None

    def emote(self, emote) -> None:
        if emote == 'wave':
            self.node.handlemessage(
                ('celebrate_r' if random.randint(0, 1) == 0 else 'celebrate_l'),
                random.randint(1000, 2000),
            )
        elif emote == 'celebrate':
            self.node.handlemessage('celebrate', random.randint(1000, 3000))

    def _invout(self) -> None:
        if self.node:
            self.node.invincible = False

    def _update(self) -> None:
        factory = SpazFactory.get()
        self.hitpoints_max = factory.max_hitpoints
        self.hitpoints = min(self.hitpoints, self.hitpoints_max)
        if self._demo_mode:  # Preserve old behavior.
            self._punch_power_scale = 1.7 if self._has_boxing_gloves else 1.2
            self._punch_cooldown = (
                300 if self._has_boxing_gloves else BASE_PUNCH_COOLDOWN
            )
        else:
            self._punch_power_scale = (
                factory.punch_power_scale_gloves
                if self._has_boxing_gloves
                else factory.punch_power_scale
            )
            self._punch_cooldown = (
                factory.punch_cooldown_gloves
                if self._has_boxing_gloves
                else factory.punch_cooldown
            )
        if self.node:
            self.node.hockey = self._hockey or (
                self.speed and not self.node.hold_node and self.node.run == 1.0
            )
            f = 1 - self.activity.gravity_mult
            if f != 0:
                self.node.handlemessage(
                    'impulse',
                    self.node.position_center[0],
                    self.node.position_center[1],
                    self.node.position_center[2],
                    0,
                    f,
                    0,
                    0,
                    6,
                    0,
                    0,
                    0,
                    f,
                    0,
                )

    def _give_random_bomb_modifier(self) -> None:
        if self.node:
            self.handlemessage(
                bs.PowerupMessage(
                    random.choice(
                        [
                            'triple_bombs',
                            'big_bombs',
                            'light_bombs',
                        ]
                    )
                )
            )
            self.node.mini_billboard_2_texture = (
                PowerupBoxFactory.get().tex_powerups
            )
            t_ms = int(bs.time() * 1000.0)
            assert isinstance(t_ms, int)
            self.node.mini_billboard_2_start_time = t_ms
            self.node.mini_billboard_2_end_time = t_ms + 500
            self._bomb_wear_off_flash_timer = None
            self._bomb_wear_off_timer = bs.Timer(
                0.5,
                bs.WeakCall(self._give_random_bomb),
            )

    def _give_random_bomb(self) -> None:
        if self.node:
            self.handlemessage(
                bs.PowerupMessage(
                    random.choice(
                        [
                            'ice_bombs',
                            'impact_bombs',
                            'sticky_bombs',
                            'impulse_bombs',
                        ]
                    )
                )
            )
            self.node.mini_billboard_3_texture = (
                PowerupBoxFactory.get().tex_powerups
            )
            t_ms = int(bs.time() * 1000.0)
            assert isinstance(t_ms, int)
            self.node.mini_billboard_3_start_time = t_ms
            self.node.mini_billboard_3_end_time = t_ms + 500
            self._boxing_gloves_wear_off_flash_timer = None
            self._boxing_gloves_wear_off_timer = bs.Timer(
                0.5,
                bs.WeakCall(self._give_random_modifier),
            )

    def _give_random_modifier(self) -> None:
        if self.node:
            self.handlemessage(
                bs.PowerupMessage(random.choice(['punch', 'pap', 'speed']))
            )

    def _touched(self) -> None:
        if (
            self.mode is bs.ProjectileActorMode
            and self.node
            and self.is_alive()
        ):
            node = bs.getcollision().opposingnode
            if node != self.node:
                node.handlemessage(
                    bs.HitMessage(
                        pos=self.node.position,
                        velocity=self.node.velocity,
                        velocity_magnitude=40,
                        radius=0,
                        srcnode=self.node,
                        source_player=self.source_player,
                    )
                )
                self._hit_self(max(self.node.velocity))
                self.handlemessage(bs.DieMessage(how=bs.DeathType.IMPACT))
