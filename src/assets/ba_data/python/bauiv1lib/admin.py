# Released under AGPL-3.0-or-later. See LICENSE for details.
#
"""Provides a popup window as our GUI admin panel."""

from __future__ import annotations

from bauiv1lib.popup import PopupWindow
import bauiv1 as bui
import bascenev1 as bs


class AdminWindow(PopupWindow):
    """Popup window which is our admin panel."""

    def __init__(
        self, position: tuple[float, float], scale: float | None = None
    ):
        # pylint: disable=too-many-locals
        assert bui.app.classic is not None
        uiscale = bui.app.ui_v1.uiscale
        if scale is None:
            scale = 1.23
        self._transitioning_out = False
        self._width = 670.0
        self._height = 520.0
        bg_color = (0.5, 0.5, 0.5)

        # creates our _root_widget
        super().__init__(
            position=position,
            size=(self._width, self._height),
            scale=scale,
            bg_color=bg_color,
        )

        self._cancel_button = bui.buttonwidget(
            parent=self.root_widget,
            position=(50, self._height - 30),
            size=(50, 50),
            scale=0.5,
            label='',
            color=bg_color,
            on_activate_call=self._on_cancel_press,
            autoselect=True,
            icon=bui.gettexture('crossOut'),
            iconscale=1.2,
        )

        self._title_text = bui.textwidget(
            parent=self.root_widget,
            position=(0, self._height - 10),
            size=(self._width, 10),
            h_align='center',
            v_align='top',
            text='Admin Panel',
            color=(1, 1, 1, 1),
        )

        bui.containerwidget(
            edit=self.root_widget, cancel_button=self._cancel_button
        )

        from bauiv1lib.helpui import POWERUP_NAMES

        self._p_scroll_width = self._width / 2 - 50
        self._p_scroll_height = self._height / 2 - 75.0
        self._p_sub_width = self._p_scroll_width * 0.95
        self._p_sub_height = 1200
        bui.textwidget(
            parent=self.root_widget,
            position=(15, self._height - 60),
            size=(self._width / 2, 10),
            h_align='center',
            v_align='bottom',
            text='Powerups',
            color=bui.app.ui_v1.title_color,
        )
        bui.textwidget(
            parent=self.root_widget,
            position=(15, self._height - 75),
            size=(self._width / 2, 10),
            scale=0.6,
            h_align='center',
            v_align='bottom',
            text='(everyone receives the selected powerup)',
            color=bui.app.ui_v1.title_color,
        )
        self._p_scrollwidget = bui.scrollwidget(
            parent=self.root_widget,
            position=(50, self._height / 2),
            simple_culling_v=20.0,
            highlight=False,
            size=(self._p_scroll_width, self._p_scroll_height),
            selection_loops_to_parent=True,
        )
        bui.widget(edit=self._p_scrollwidget, right_widget=self._p_scrollwidget)
        self._p_subcontainer = bui.containerwidget(
            parent=self._p_scrollwidget,
            size=(self._p_sub_width, self._p_sub_height),
            background=False,
            selection_loops_to_parent=True,
        )
        pv = 50
        for dat in [
            ['powerupPunch', 'punch'],
            ['powerupPap', 'pap'],
            ['powerupShield', 'shield'],
            ['powerupUno', 'uno'],
            ['powerupInv', 'inv'],
            ['powerupBomb', 'triple_bombs'],
            ['powerupBigBombs', 'big_bombs'],
            ['powerupLightBombs', 'light_bombs'],
            ['powerupHealth', 'health'],
            ['powerupSpeed', 'speed'],
            ['powerupPowerups', 'powerups'],
            ['powerupBot', 'bot'],
            ['powerupIceBombs', 'ice_bombs'],
            ['powerupImpactBombs', 'impact_bombs'],
            ['powerupStickyBombs', 'sticky_bombs'],
            ['powerupImpulseBombs', 'impulse_bombs'],
            ['powerupLandMines', 'land_mines'],
            ['powerupIcepactBombs', 'icepact_bombs'],
            ['powerupWonderBombs', 'wonder'],
            ['powerupPortal', 'portal'],
            ['powerup0g', '0g'],
            ['powerupCoins', 'coins'],
            ['powerupDev', 'dev'],
            ['powerupCurse', 'curse'],
        ]:
            tex = dat[0]
            name = POWERUP_NAMES.get(tex) or bui.Lstr(
                resource='helpWindow.' + tex + 'NameText'
            )
            bui.buttonwidget(
                parent=self._p_subcontainer,
                position=(5, self._p_sub_height - pv),
                size=(self._p_sub_width - 20, 40),
                label=name,
                icon=bui.gettexture(tex),
                on_activate_call=bui.Call(bs.chatmessage, '/powerup ' + dat[1]),
            )
            pv += 50

        from bascenev1lib.actor.themes import THEME_DICT

        self._t_scroll_width = self._width / 2 - 50
        self._t_scroll_height = self._height / 2 - 75.0
        self._t_sub_width = self._t_scroll_width * 0.95
        self._t_sub_height = 400
        bui.textwidget(
            parent=self.root_widget,
            position=(15, self._height / 2 - 40),
            size=(self._width / 2, 10),
            h_align='center',
            v_align='bottom',
            text='Themes',
            color=bui.app.ui_v1.title_color,
        )
        self._t_scrollwidget = bui.scrollwidget(
            parent=self.root_widget,
            position=(50, 35),
            simple_culling_v=20.0,
            highlight=False,
            size=(self._t_scroll_width, self._t_scroll_height),
            selection_loops_to_parent=True,
        )
        bui.widget(edit=self._t_scrollwidget, right_widget=self._t_scrollwidget)
        self._t_subcontainer = bui.containerwidget(
            parent=self._t_scrollwidget,
            size=(self._t_sub_width, self._t_sub_height),
            background=False,
            selection_loops_to_parent=True,
        )
        bui.buttonwidget(
            parent=self._t_subcontainer,
            position=(5, self._t_sub_height - 50),
            size=(self._t_sub_width - 20, 40),
            label='Random',
            on_activate_call=bui.Call(bs.chatmessage, '/theme random'),
        )
        pv = 100
        for name in THEME_DICT.keys():
            bui.buttonwidget(
                parent=self._t_subcontainer,
                position=(5, self._t_sub_height - pv),
                size=(self._t_sub_width - 20, 40),
                label=name.split(' ')[0],
                on_activate_call=bui.Call(bs.chatmessage, '/theme ' + name),
            )
            pv += 50
        bui.buttonwidget(
            parent=self._t_subcontainer,
            position=(5, self._t_sub_height - pv),
            size=(self._t_sub_width - 20, 40),
            label='None',
            on_activate_call=bui.Call(bs.chatmessage, '/theme None Theme'),
        )

        self._o_scroll_width = self._width / 2 - 50
        self._o_scroll_height = self._height / 2 - 65.0
        self._o_sub_width = self._o_scroll_width * 0.95
        self._o_sub_height = 350
        bui.textwidget(
            parent=self.root_widget,
            position=(self._width / 2 - 15, self._height / 2 - 30),
            size=(self._width / 2, 10),
            h_align='center',
            v_align='bottom',
            text='Other',
            color=bui.app.ui_v1.title_color,
        )
        self._o_scrollwidget = bui.scrollwidget(
            parent=self.root_widget,
            position=(self._width / 2 + 15, 35),
            simple_culling_v=20.0,
            highlight=False,
            size=(self._o_scroll_width, self._o_scroll_height),
            selection_loops_to_parent=True,
        )
        bui.widget(edit=self._o_scrollwidget, right_widget=self._o_scrollwidget)
        self._o_subcontainer = bui.containerwidget(
            parent=self._o_scrollwidget,
            size=(self._o_sub_width, self._o_sub_height),
            background=False,
            selection_loops_to_parent=True,
        )
        v = 50
        bui.buttonwidget(
            parent=self._o_subcontainer,
            position=(5, self._o_sub_height - v),
            size=(self._o_sub_width - 20, 40),
            label='End Activity',
            on_activate_call=bui.Call(bs.chatmessage, '/fun enda'),
        )
        v += 50
        bui.buttonwidget(
            parent=self._o_subcontainer,
            position=(5, self._o_sub_height - v),
            size=(self._o_sub_width - 20, 40),
            label='End Session',
            on_activate_call=bui.Call(bs.chatmessage, '/fun ends'),
        )
        v += 50
        bui.buttonwidget(
            parent=self._o_subcontainer,
            position=(5, self._o_sub_height - v),
            size=(self._o_sub_width - 20, 40),
            label='Explode All Players',
            on_activate_call=bui.Call(bs.chatmessage, '/fun blowall'),
        )
        v += 50
        bui.buttonwidget(
            parent=self._o_subcontainer,
            position=(5, self._o_sub_height - v),
            size=(self._o_sub_width - 20, 40),
            label='Kill All Players',
            on_activate_call=bui.Call(bs.chatmessage, '/fun killall'),
        )
        v += 50
        bui.buttonwidget(
            parent=self._o_subcontainer,
            position=(5, self._o_sub_height - v),
            size=(self._o_sub_width - 20, 40),
            label='Re-select Modifiers',
            on_activate_call=bui.Call(bs.chatmessage, '/modifier refresh'),
        )
        v += 50
        bui.buttonwidget(
            parent=self._o_subcontainer,
            position=(5, self._o_sub_height - v),
            size=(self._o_sub_width - 20, 40),
            label='Re-select Modifiers (+ modifier announcement)',
            on_activate_call=bui.Call(bs.chatmessage, '/modifier renew'),
        )
        v += 50
        bui.buttonwidget(
            parent=self._o_subcontainer,
            position=(5, self._o_sub_height - v),
            size=(self._o_sub_width - 20, 40),
            label='Remove All Modifiers',
            on_activate_call=bui.Call(bs.chatmessage, '/modifier killall'),
        )
        v += 50

    def _on_cancel_press(self) -> None:
        self._transition_out()

    def _transition_out(self) -> None:
        if not self._transitioning_out:
            self._transitioning_out = True
            bui.containerwidget(edit=self.root_widget, transition='out_scale')

    def on_popup_cancel(self) -> None:
        bui.getsound('swish').play()
        self._transition_out()
