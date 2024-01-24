# Released under the MIT License. See LICENSE for details.
#
"""UI for browsing available co-op levels/games/etc."""
# FIXME: Break this up.
# pylint: disable=too-many-lines

from __future__ import annotations

import logging
from threading import Thread
from typing import TYPE_CHECKING

from bauiv1lib.store.button import StoreButton
from bauiv1lib.store.browser import StoreBrowserWindow
import bauiv1 as bui

if TYPE_CHECKING:
    from typing import Any


class CoopBrowserWindow(bui.Window):
    """Window for browsing co-op levels/games/etc."""

    def __init__(
        self,
        transition: str | None = 'in_right',
        origin_widget: bui.Widget | None = None,
    ):
        # pylint: disable=too-many-statements
        # pylint: disable=cyclic-import

        plus = bui.app.plus
        assert plus is not None

        # Preload some modules we use in a background thread so we won't
        # have a visual hitch when the user taps them.
        Thread(target=self._preload_modules).start()

        bui.set_analytics_screen('Coop Window')

        app = bui.app
        assert app.classic is not None
        cfg = app.config

        # If they provided an origin-widget, scale up from that.
        scale_origin: tuple[float, float] | None
        if origin_widget is not None:
            self._transition_out = 'out_scale'
            scale_origin = origin_widget.get_screen_space_center()
            transition = 'in_scale'
        else:
            self._transition_out = 'out_right'
            scale_origin = None

        self.star_tex = bui.gettexture('star')
        self.lsbt = bui.getmesh('level_select_button_transparent')
        self.lsbo = bui.getmesh('level_select_button_opaque')
        self.a_outline_tex = bui.gettexture('achievementOutline')
        self.a_outline_mesh = bui.getmesh('achievementOutline')
        self._campaign_sub_container: bui.Widget | None = None
        self._easy_button: bui.Widget | None = None
        self._hard_button: bui.Widget | None = None
        self._hard_button_lock_image: bui.Widget | None = None
        self._campaign_percent_text: bui.Widget | None = None

        assert bui.app.classic is not None
        uiscale = bui.app.ui_v1.uiscale
        self._width = 1520 if uiscale is bui.UIScale.SMALL else 1120
        self._x_inset = x_inset = 200 if uiscale is bui.UIScale.SMALL else 0
        self._height = (
            657
            if uiscale is bui.UIScale.SMALL
            else 730
            if uiscale is bui.UIScale.MEDIUM
            else 800
        )
        app.ui_v1.set_main_menu_location('Coop Select')
        self._r = 'coopSelectWindow'
        top_extra = 20 if uiscale is bui.UIScale.SMALL else 0

        self._campaign_difficulty = plus.get_v1_account_misc_val(
            'campaignDifficulty', 'easy'
        )

        super().__init__(
            root_widget=bui.containerwidget(
                size=(self._width, self._height + top_extra),
                toolbar_visibility='menu_full',
                scale_origin_stack_offset=scale_origin,
                stack_offset=(
                    (0, -15)
                    if uiscale is bui.UIScale.SMALL
                    else (0, 0)
                    if uiscale is bui.UIScale.MEDIUM
                    else (0, 0)
                ),
                transition=transition,
                scale=(
                    1.2
                    if uiscale is bui.UIScale.SMALL
                    else 0.8
                    if uiscale is bui.UIScale.MEDIUM
                    else 0.75
                ),
            )
        )

        if app.ui_v1.use_toolbars and uiscale is bui.UIScale.SMALL:
            self._back_button = None
        else:
            self._back_button = bui.buttonwidget(
                parent=self._root_widget,
                position=(
                    75 + x_inset,
                    self._height
                    - 87
                    - (4 if uiscale is bui.UIScale.SMALL else 0),
                ),
                size=(120, 60),
                scale=1.2,
                autoselect=True,
                label=bui.Lstr(resource='backText'),
                button_type='back',
            )

        self._store_button: StoreButton | None
        self._store_button_widget: bui.Widget | None

        if not app.ui_v1.use_toolbars:
            sbtn = self._store_button = StoreButton(
                parent=self._root_widget,
                position=(
                    self._width - (170 + x_inset),
                    self._height
                    - 85
                    - (4 if uiscale is bui.UIScale.SMALL else 0),
                ),
                size=(100, 60),
                color=(0.6, 0.4, 0.7),
                show_tickets=True,
                button_type='square',
                sale_scale=0.85,
                textcolor=(0.9, 0.7, 1.0),
                scale=1.05,
                on_activate_call=bui.WeakCall(self._switch_to_score, None),
            )
            self._store_button_widget = sbtn.get_button()
            bui.widget(
                edit=self._back_button,
                right_widget=self._store_button_widget,
            )
            bui.widget(
                edit=self._store_button_widget,
                left_widget=self._back_button,
            )
        else:
            self._store_button = None
            self._store_button_widget = None

        # Move our corner buttons dynamically to keep them out of the way of
        # the party icon :-(
        self._update_corner_button_positions()
        self._update_corner_button_positions_timer = bui.AppTimer(
            1.0, bui.WeakCall(self._update_corner_button_positions), repeat=True
        )

        self._selected_campaign_level = cfg.get(
            'Selected Coop Campaign Level', None
        )
        self._selected_custom_level = cfg.get(
            'Selected Coop Custom Level', None
        )

        # Don't want initial construction affecting our last-selected.
        self._do_selection_callbacks = False
        v = self._height - 95
        txt = bui.textwidget(
            parent=self._root_widget,
            position=(
                self._width * 0.5,
                v + 40 - (0 if uiscale is bui.UIScale.SMALL else 0),
            ),
            size=(0, 0),
            text=bui.Lstr(
                resource='playModes.singlePlayerCoopText',
                fallback_resource='playModes.coopText',
            ),
            h_align='center',
            color=app.ui_v1.title_color,
            scale=1.5,
            maxwidth=500,
            v_align='center',
        )

        if app.ui_v1.use_toolbars and uiscale is bui.UIScale.SMALL:
            bui.textwidget(edit=txt, text='')

        if self._back_button is not None:
            bui.buttonwidget(
                edit=self._back_button,
                button_type='backSmall',
                size=(60, 50),
                position=(
                    75 + x_inset,
                    self._height
                    - 87
                    - (4 if uiscale is bui.UIScale.SMALL else 0)
                    + 6,
                ),
                label=bui.charstr(bui.SpecialChar.BACK),
            )

        self._selected_row = cfg.get('Selected Coop Row', None)

        self._scroll_width = self._width - (130 + 2 * x_inset)
        self._scroll_height = self._height - (
            190
            if uiscale is bui.UIScale.SMALL and app.ui_v1.use_toolbars
            else 160
        )

        self._subcontainerwidth = 800.0
        self._subcontainerheight = self._height - 200

        self._scrollwidget = bui.scrollwidget(
            parent=self._root_widget,
            highlight=False,
            position=(65 + x_inset, 120)
            if uiscale is bui.UIScale.SMALL and app.ui_v1.use_toolbars
            else (65 + x_inset, 70),
            size=(self._scroll_width, self._scroll_height),
            simple_culling_v=10.0,
            claims_left_right=True,
            claims_tab=True,
            selection_loops_to_parent=True,
        )
        self._subcontainer: bui.Widget | None = None

        # Take note of our account state; we'll refresh later if this changes.
        self._account_state_num = plus.get_v1_account_state_num()

        # Same for fg/bg state.
        self._fg_state = app.fg_state

        self._refresh()
        self._restore_state()

        # This will pull new data periodically, update timers, etc.
        self._update_timer = bui.AppTimer(
            1.0, bui.WeakCall(self._update_hard_mode_lock_image), repeat=True
        )
        self._update_hard_mode_lock_image()

    def _update_corner_button_positions(self) -> None:
        assert bui.app.classic is not None
        uiscale = bui.app.ui_v1.uiscale
        offs = (
            -55
            if uiscale is bui.UIScale.SMALL and bui.is_party_icon_visible()
            else 0
        )
        if self._store_button is not None:
            self._store_button.set_position(
                (
                    self._width - 170 + offs - self._x_inset,
                    self._height
                    - 85
                    - (4 if uiscale is bui.UIScale.SMALL else 0),
                )
            )

    # noinspection PyUnresolvedReferences
    @staticmethod
    def _preload_modules() -> None:
        """Preload modules we use; avoids hitches (called in bg thread)."""
        import bauiv1lib.purchase as _unused1
        import bauiv1lib.coop.gamebutton as _unused2
        import bauiv1lib.confirm as _unused3
        import bauiv1lib.account as _unused4
        import bauiv1lib.store.browser as _unused5
        import bauiv1lib.account.viewer as _unused6
        import bauiv1lib.play as _unused7

    def _update_hard_mode_lock_image(self) -> None:
        assert bui.app.classic is not None
        try:
            bui.imagewidget(
                edit=self._hard_button_lock_image,
                opacity=0.0
                if bui.app.classic.accounts.have_pro_options()
                else 1.0,
            )
        except Exception:
            logging.exception('Error updating campaign lock.')

    def _set_campaign_difficulty(self, difficulty: str) -> None:
        # pylint: disable=cyclic-import
        from bauiv1lib.purchase import PurchaseWindow

        plus = bui.app.plus
        assert plus is not None

        assert bui.app.classic is not None
        if difficulty != self._campaign_difficulty:
            if (
                difficulty == 'hard'
                and not bui.app.classic.accounts.have_pro_options()
            ):
                PurchaseWindow(items=['pro'])
                return
            bui.getsound('gunCocking').play()
            if difficulty not in ('easy', 'hard'):
                print('ERROR: invalid campaign difficulty:', difficulty)
                difficulty = 'easy'
            self._campaign_difficulty = difficulty
            plus.add_v1_account_transaction(
                {
                    'type': 'SET_MISC_VAL',
                    'name': 'campaignDifficulty',
                    'value': difficulty,
                }
            )
            self._refresh_campaign_row()
        else:
            bui.getsound('click01').play()

    def _refresh_campaign_row(self) -> None:
        # pylint: disable=too-many-locals
        # pylint: disable=cyclic-import
        from bauiv1lib.coop.gamebutton import GameButton

        parent_widget = self._campaign_sub_container

        # Clear out anything in the parent widget already.
        assert parent_widget is not None
        for child in parent_widget.get_children():
            child.delete()

        h = 0
        v2 = -2
        sel_color = (0.75, 0.85, 0.5)
        sel_color_hard = (0.4, 0.7, 0.2)
        un_sel_color = (0.5, 0.5, 0.5)
        sel_textcolor = (2, 2, 0.8)
        un_sel_textcolor = (0.6, 0.6, 0.6)
        self._easy_button = bui.buttonwidget(
            parent=parent_widget,
            position=(h + 30, v2 + 105),
            size=(120, 70),
            label=bui.Lstr(resource='difficultyEasyText'),
            button_type='square',
            autoselect=True,
            enable_sound=False,
            on_activate_call=bui.Call(self._set_campaign_difficulty, 'easy'),
            on_select_call=bui.Call(self.sel_change, 'campaign', 'easyButton'),
            color=sel_color
            if self._campaign_difficulty == 'easy'
            else un_sel_color,
            textcolor=sel_textcolor
            if self._campaign_difficulty == 'easy'
            else un_sel_textcolor,
        )
        bui.widget(edit=self._easy_button, show_buffer_left=100)
        if self._selected_campaign_level == 'easyButton':
            bui.containerwidget(
                edit=parent_widget,
                selected_child=self._easy_button,
                visible_child=self._easy_button,
            )
        lock_tex = bui.gettexture('lock')

        self._hard_button = bui.buttonwidget(
            parent=parent_widget,
            position=(h + 30, v2 + 32),
            size=(120, 70),
            label=bui.Lstr(resource='difficultyHardText'),
            button_type='square',
            autoselect=True,
            enable_sound=False,
            on_activate_call=bui.Call(self._set_campaign_difficulty, 'hard'),
            on_select_call=bui.Call(self.sel_change, 'campaign', 'hardButton'),
            color=sel_color_hard
            if self._campaign_difficulty == 'hard'
            else un_sel_color,
            textcolor=sel_textcolor
            if self._campaign_difficulty == 'hard'
            else un_sel_textcolor,
        )
        self._hard_button_lock_image = bui.imagewidget(
            parent=parent_widget,
            size=(30, 30),
            draw_controller=self._hard_button,
            position=(h + 30 - 10, v2 + 32 + 70 - 35),
            texture=lock_tex,
        )
        self._update_hard_mode_lock_image()
        bui.widget(edit=self._hard_button, show_buffer_left=100)
        if self._selected_campaign_level == 'hardButton':
            bui.containerwidget(
                edit=parent_widget,
                selected_child=self._hard_button,
                visible_child=self._hard_button,
            )

        h_spacing = 200
        campaign_buttons = []
        if self._campaign_difficulty == 'easy':
            campaignname = 'Easy'
        else:
            campaignname = 'Default'
        items = [
            campaignname + ':Onslaught Training',
            campaignname + ':Rookie Onslaught',
            campaignname + ':Rookie Football',
            campaignname + ':Pro Onslaught',
            campaignname + ':Pro Football',
            campaignname + ':Pro Runaround',
            campaignname + ':Uber Onslaught',
            campaignname + ':Uber Football',
            campaignname + ':Uber Runaround',
        ]
        items += [campaignname + ':The Last Stand']
        if self._selected_campaign_level is None:
            self._selected_campaign_level = items[0]
        h = 150
        for i in items:
            is_last_sel = i == self._selected_campaign_level
            campaign_buttons.append(
                GameButton(
                    self, parent_widget, i, h, v2, is_last_sel, 'campaign'
                ).get_button()
            )
            h += h_spacing

        bui.widget(edit=campaign_buttons[0], left_widget=self._easy_button)

        if self._back_button is not None:
            bui.widget(edit=self._easy_button, up_widget=self._back_button)
            for btn in campaign_buttons:
                bui.widget(
                    edit=btn, up_widget=self._back_button
                )

        # Update our existing percent-complete text.
        assert bui.app.classic is not None
        campaign = bui.app.classic.getcampaign(campaignname)
        levels = campaign.levels
        levels_complete = sum((1 if l.complete else 0) for l in levels)

        # Last level cant be completed; hence the -1.
        progress = min(1.0, float(levels_complete) / (len(levels) - 1))
        p_str = str(int(progress * 100.0)) + '%'

        self._campaign_percent_text = bui.textwidget(
            edit=self._campaign_percent_text,
            text=bui.Lstr(
                value='${C} (${P})',
                subs=[
                    ('${C}', bui.Lstr(resource=self._r + '.campaignText')),
                    ('${P}', p_str),
                ],
            ),
        )

    def _refresh(self) -> None:
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-locals
        # pylint: disable=cyclic-import
        from bauiv1lib.coop.gamebutton import GameButton

        plus = bui.app.plus
        assert plus is not None
        assert bui.app.classic is not None

        # (Re)create the sub-container if need be.
        if self._subcontainer is not None:
            self._subcontainer.delete()

        self._subcontainer = bui.containerwidget(
            parent=self._scrollwidget,
            size=(self._subcontainerwidth, self._subcontainerheight),
            background=False,
            claims_left_right=True,
            claims_tab=True,
            selection_loops_to_parent=True,
        )

        bui.containerwidget(
            edit=self._root_widget, selected_child=self._scrollwidget
        )
        if self._back_button is not None:
            bui.containerwidget(
                edit=self._root_widget, cancel_button=self._back_button
            )

        w_parent = self._subcontainer
        h_base = 6

        v = self._subcontainerheight - 73

        self._campaign_percent_text = bui.textwidget(
            parent=w_parent,
            position=(h_base + 27, v + 30),
            size=(0, 0),
            text='',
            h_align='left',
            v_align='center',
            color=bui.app.ui_v1.title_color,
            scale=1.1,
        )

        row_v_show_buffer = 100
        v -= 198

        h_scroll = bui.hscrollwidget(
            parent=w_parent,
            size=(self._scroll_width - 10, 205),
            position=(-5, v),
            simple_culling_h=70,
            highlight=False,
            border_opacity=0.0,
            color=(0.45, 0.4, 0.5),
            on_select_call=lambda: self._on_row_selected('campaign'),
        )
        self._campaign_h_scroll = h_scroll
        bui.widget(
            edit=h_scroll,
            show_buffer_top=row_v_show_buffer,
            show_buffer_bottom=row_v_show_buffer,
            autoselect=True,
        )
        if self._selected_row == 'campaign':
            bui.containerwidget(
                edit=w_parent, selected_child=h_scroll, visible_child=h_scroll
            )
        bui.containerwidget(edit=h_scroll, claims_left_right=True)
        self._campaign_sub_container = bui.containerwidget(
            parent=h_scroll, size=(180 + 200 * 10, 200), background=False
        )
        v -= 198

        # Custom Games. (called 'Practice' in UI these days).
        v -= 50
        bui.textwidget(
            parent=w_parent,
            position=(h_base + 27, v + 30 + 198),
            size=(0, 0),
            text=bui.Lstr(
                resource='practiceText',
                fallback_resource='coopSelectWindow.customText',
            ),
            h_align='left',
            v_align='center',
            color=bui.app.ui_v1.title_color,
            scale=1.1,
        )

        items = [
            'Challenges:Running Bombs',
            'Challenges:Epic Running Bombs',
            'Challenges:Infinite Onslaught',
            'Challenges:Infinite Runaround',
            'Challenges:Ninja Fight',
            'Challenges:Pro Ninja Fight',
            'Challenges:Meteor Shower',
            'Challenges:Target Practice B',
            'Challenges:Target Practice',
        ]

        # Show easter-egg-hunt either if its easter or we own it.
        if plus.get_v1_account_misc_read_val(
            'easter', False
        ) or plus.get_purchased('games.easter_egg_hunt'):
            items = [
                'Challenges:Easter Egg Hunt',
                'Challenges:Pro Easter Egg Hunt',
            ] + items

        # If we've defined custom games, put them at the beginning.
        if bui.app.classic.custom_coop_practice_games:
            items = bui.app.classic.custom_coop_practice_games + items

        self._custom_h_scroll = custom_h_scroll = h_scroll = bui.hscrollwidget(
            parent=w_parent,
            size=(self._scroll_width - 10, 205),
            position=(-5, v),
            highlight=False,
            border_opacity=0.0,
            color=(0.45, 0.4, 0.5),
            on_select_call=bui.Call(self._on_row_selected, 'custom'),
        )
        bui.widget(
            edit=h_scroll,
            show_buffer_top=row_v_show_buffer,
            show_buffer_bottom=1.5 * row_v_show_buffer,
            autoselect=True,
        )
        if self._selected_row == 'custom':
            bui.containerwidget(
                edit=w_parent, selected_child=h_scroll, visible_child=h_scroll
            )
        bui.containerwidget(edit=h_scroll, claims_left_right=True)
        sc2 = bui.containerwidget(
            parent=h_scroll,
            size=(max(self._scroll_width - 24, 30 + 200 * len(items)), 200),
            background=False,
        )
        h_spacing = 200
        self._custom_buttons: list[GameButton] = []
        h = 0
        v2 = -2
        for item in items:
            is_last_sel = item == self._selected_custom_level
            self._custom_buttons.append(
                GameButton(self, sc2, item, h, v2, is_last_sel, 'custom')
            )
            h += h_spacing

        # We can't fill in our campaign row until tourney buttons are in place.
        # (for wiring up)
        self._refresh_campaign_row()

        if self._back_button is not None:
            bui.buttonwidget(
                edit=self._back_button, on_activate_call=self._back
            )
        else:
            bui.containerwidget(
                edit=self._root_widget, on_cancel_call=self._back
            )

        # There's probably several 'onSelected' callbacks pushed onto the
        # event queue.. we need to push ours too so we're enabled *after* them.
        bui.pushcall(self._enable_selectable_callback)

    def _on_row_selected(self, row: str) -> None:
        if self._do_selection_callbacks:
            if self._selected_row != row:
                self._selected_row = row

    def _enable_selectable_callback(self) -> None:
        self._do_selection_callbacks = True

    def _switch_to_score(
        self,
        show_tab: StoreBrowserWindow.TabID
        | None = StoreBrowserWindow.TabID.EXTRAS,
    ) -> None:
        # pylint: disable=cyclic-import
        from bauiv1lib.account import show_sign_in_prompt

        # no-op if our underlying widget is dead or on its way out.
        if not self._root_widget or self._root_widget.transitioning_out:
            return

        plus = bui.app.plus
        assert plus is not None

        if plus.get_v1_account_state() != 'signed_in':
            show_sign_in_prompt()
            return
        self._save_state()
        bui.containerwidget(edit=self._root_widget, transition='out_left')
        assert self._store_button is not None
        assert bui.app.classic is not None
        bui.app.ui_v1.set_main_menu_window(
            StoreBrowserWindow(
                origin_widget=self._store_button.get_button(),
                show_tab=show_tab,
                back_location='CoopBrowserWindow',
            ).get_root_widget(),
            from_window=self._root_widget,
        )

    def run_game(self, game: str) -> None:
        """Run the provided game."""
        # pylint: disable=too-many-branches
        # pylint: disable=cyclic-import
        from bauiv1lib.confirm import ConfirmWindow
        from bauiv1lib.purchase import PurchaseWindow
        from bauiv1lib.account import show_sign_in_prompt

        plus = bui.app.plus
        assert plus is not None

        assert bui.app.classic is not None

        args: dict[str, Any] = {}

        if game == 'Easy:The Last Stand':
            ConfirmWindow(
                bui.Lstr(
                    resource='difficultyHardUnlockOnlyText',
                    fallback_resource='difficultyHardOnlyText',
                ),
                cancel_button=False,
                width=460,
                height=130,
            )
            return

        # Infinite onslaught/runaround require pro; bring up a store link
        # if need be.
        if (
            game
            in (
                'Challenges:Infinite Runaround',
                'Challenges:Infinite Onslaught',
            )
            and not bui.app.classic.accounts.have_pro()
        ):
            if plus.get_v1_account_state() != 'signed_in':
                show_sign_in_prompt()
            else:
                PurchaseWindow(items=['pro'])
            return

        required_purchase: str | None
        if game in ['Challenges:Meteor Shower']:
            required_purchase = 'games.meteor_shower'
        elif game in [
            'Challenges:Target Practice',
            'Challenges:Target Practice B',
        ]:
            required_purchase = 'games.target_practice'
        elif game in ['Challenges:Ninja Fight']:
            required_purchase = 'games.ninja_fight'
        elif game in ['Challenges:Pro Ninja Fight']:
            required_purchase = 'games.ninja_fight'
        elif game in [
            'Challenges:Easter Egg Hunt',
            'Challenges:Pro Easter Egg Hunt',
        ]:
            required_purchase = 'games.easter_egg_hunt'
        else:
            required_purchase = None

        if required_purchase is not None and not plus.get_purchased(
            required_purchase
        ):
            if plus.get_v1_account_state() != 'signed_in':
                show_sign_in_prompt()
            else:
                PurchaseWindow(items=[required_purchase])
            return

        self._save_state()

        if bui.app.classic.launch_coop_game(game, args=args):
            bui.containerwidget(edit=self._root_widget, transition='out_left')

    def _back(self) -> None:
        # pylint: disable=cyclic-import
        from bauiv1lib.play import PlayWindow

        # no-op if our underlying widget is dead or on its way out.
        if not self._root_widget or self._root_widget.transitioning_out:
            return

        # If something is selected, store it.
        self._save_state()
        bui.containerwidget(
            edit=self._root_widget, transition=self._transition_out
        )
        assert bui.app.classic is not None
        bui.app.ui_v1.set_main_menu_window(
            PlayWindow(transition='in_left').get_root_widget(),
            from_window=self._root_widget,
        )

    def _save_state(self) -> None:
        cfg = bui.app.config
        try:
            sel = self._root_widget.get_selected_child()
            if sel == self._back_button:
                sel_name = 'Back'
            elif sel == self._store_button_widget:
                sel_name = 'Store'
            elif sel == self._scrollwidget:
                sel_name = 'Scroll'
            else:
                raise ValueError('unrecognized selection')
            assert bui.app.classic is not None
            bui.app.ui_v1.window_states[type(self)] = {'sel_name': sel_name}
        except Exception:
            logging.exception('Error saving state for %s.', self)

        cfg['Selected Coop Row'] = self._selected_row
        cfg['Selected Coop Custom Level'] = self._selected_custom_level
        cfg['Selected Coop Campaign Level'] = self._selected_campaign_level
        cfg.commit()

    def _restore_state(self) -> None:
        try:
            assert bui.app.classic is not None
            sel_name = bui.app.ui_v1.window_states.get(type(self), {}).get(
                'sel_name'
            )
            if sel_name == 'Back':
                sel = self._back_button
            elif sel_name == 'Scroll':
                sel = self._scrollwidget
            elif sel_name == 'Store':
                sel = self._store_button_widget
            else:
                sel = self._scrollwidget
            bui.containerwidget(edit=self._root_widget, selected_child=sel)
        except Exception:
            logging.exception('Error restoring state for %s.', self)

    def sel_change(self, row: str, game: str) -> None:
        """(internal)"""
        if self._do_selection_callbacks:
            if row == 'custom':
                self._selected_custom_level = game
            elif row == 'campaign':
                self._selected_campaign_level = game
