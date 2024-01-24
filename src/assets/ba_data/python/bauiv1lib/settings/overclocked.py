# Released under AGPL-3.0-or-later. See LICENSE for details.
#
"""UI functionality for advanced settings."""

from __future__ import annotations

import logging

import bauiv1 as bui


def restart(val: bool) -> None:
    bui.screenmessage(
        bui.Lstr(resource='settingsWindowAdvanced.mustRestartText'),
        color=(1.0, 0.5, 0.0),
    )


class OverclockedSettingsWindow(bui.Window):
    """Window for editing overclocked settings."""

    def __init__(
        self,
        transition: str = 'in_right',
        origin_widget: bui.Widget | None = None,
    ):
        # pylint: disable=too-many-statements
        import threading

        if bui.app.classic is None:
            raise RuntimeError('This requires classic support.')

        # Preload some modules we use in a background thread so we won't
        # have a visual hitch when the user taps them.
        threading.Thread(target=self._preload_modules).start()

        app = bui.app
        assert app.classic is not None

        # If they provided an origin-widget, scale up from that.
        scale_origin: tuple[float, float] | None
        if origin_widget is not None:
            self._transition_out = 'out_scale'
            scale_origin = origin_widget.get_screen_space_center()
            transition = 'in_scale'
        else:
            self._transition_out = 'out_right'
            scale_origin = None

        uiscale = bui.app.ui_v1.uiscale
        self._width = 870.0 if uiscale is bui.UIScale.SMALL else 670.0
        x_inset = 100 if uiscale is bui.UIScale.SMALL else 0
        self._height = (
            390.0
            if uiscale is bui.UIScale.SMALL
            else 450.0
            if uiscale is bui.UIScale.MEDIUM
            else 520.0
        )
        self._spacing = 32
        self._menu_open = False
        top_extra = 10 if uiscale is bui.UIScale.SMALL else 0
        super().__init__(
            root_widget=bui.containerwidget(
                size=(self._width, self._height + top_extra),
                transition=transition,
                toolbar_visibility='menu_minimal',
                scale_origin_stack_offset=scale_origin,
                scale=(
                    2.06
                    if uiscale is bui.UIScale.SMALL
                    else 1.4
                    if uiscale is bui.UIScale.MEDIUM
                    else 1.0
                ),
                stack_offset=(0, -25)
                if uiscale is bui.UIScale.SMALL
                else (0, 0),
            )
        )

        self._scroll_width = self._width - (100 + 2 * x_inset)
        self._scroll_height = self._height - 115.0
        self._sub_width = self._scroll_width * 0.95
        self._sub_height = 1250.0

        self._extra_button_spacing = self._spacing * 2.5

        self._r = 'settingsWindowOverclocked'

        if app.ui_v1.use_toolbars and uiscale is bui.UIScale.SMALL:
            bui.containerwidget(
                edit=self._root_widget, on_cancel_call=self._do_back
            )
            self._back_button = None
        else:
            self._back_button = bui.buttonwidget(
                parent=self._root_widget,
                position=(53 + x_inset, self._height - 60),
                size=(140, 60),
                scale=0.8,
                autoselect=True,
                label=bui.Lstr(resource='backText'),
                button_type='back',
                on_activate_call=self._do_back,
            )
            bui.containerwidget(
                edit=self._root_widget, cancel_button=self._back_button
            )

        self._title_text = bui.textwidget(
            parent=self._root_widget,
            position=(0, self._height - 52),
            size=(self._width, 25),
            text='Overclocked Settings',
            color=app.ui_v1.title_color,
            h_align='center',
            v_align='top',
        )

        if self._back_button is not None:
            bui.buttonwidget(
                edit=self._back_button,
                button_type='backSmall',
                size=(60, 60),
                label=bui.charstr(bui.SpecialChar.BACK),
            )

        self._scrollwidget = bui.scrollwidget(
            parent=self._root_widget,
            position=(50 + x_inset, 50),
            simple_culling_v=20.0,
            highlight=False,
            size=(self._scroll_width, self._scroll_height),
            selection_loops_to_parent=True,
        )
        bui.widget(edit=self._scrollwidget, right_widget=self._scrollwidget)
        self._subcontainer = bui.containerwidget(
            parent=self._scrollwidget,
            size=(self._sub_width, self._sub_height),
            background=False,
            selection_loops_to_parent=True,
        )

        from bauiv1lib.config import ConfigNumberEdit, ConfigCheckBox

        v = self._sub_height - 35
        this_button_width = 410
        v -= self._spacing * 1.2

        # Set all of the config values we need if they're not already present
        cfg = bui.app.config
        cfg.setdefault('At-The-End-of-Space Theme', False)
        cfg.setdefault('At-The-End-of-Time Theme', True)
        cfg.setdefault('Autumn Theme', True)
        cfg.setdefault('Cruel-Night Theme', True)
        cfg.setdefault('Minty-Toxicity Theme', True)
        cfg.setdefault('Under-The-Sakura Theme', True)
        cfg.setdefault('Allow Overcharged Modifiers', True)
        cfg.setdefault('Modifier Count', 3)
        cfg.setdefault('Chaos Modifier', True)
        cfg.setdefault('Gamble Modifier', True)
        cfg.setdefault('Impenetrable Modifier', True)
        cfg.setdefault('Low-Gravity Modifier', True)
        cfg.setdefault('Mini-Bombs Modifier', True)
        cfg.setdefault('Mini-Punch Modifier', True)
        cfg.setdefault('No-Powerups Modifier', True)
        cfg.setdefault('Omni-Punch Modifier', True)
        cfg.setdefault('Spaz-Rain Modifier', True)
        cfg.setdefault('Super-Bombs Modifier', True)
        cfg.setdefault('Third-Party Modifier', True)
        cfg.setdefault('Unbalanced Modifier', True)
        cfg.setdefault('Untested Modifier', True)
        cfg.setdefault('Vulnerable Modifier', True)
        cfg.setdefault('Disable Powerup Pop-ups', False)
        cfg.setdefault('Allow Admin Panel (Will Disable Leaderboards)', False)
        cfg.setdefault('Vanillaclocked', False)
        cfg.apply_and_commit()

        self._at_the_end_of_space_theme_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='At-The-End-of-Space Theme',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._at_the_end_of_time_theme_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='At-The-End-of-Time Theme',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._autumn_theme_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Autumn Theme',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._cruel_night_theme_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Cruel-Night Theme',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._minty_toxicity_theme_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Minty-Toxicity Theme',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._under_the_sakura_theme_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Under-The-Sakura Theme',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 2.5

        self._modifier_count_numedit = ConfigNumberEdit(
            parent=self._subcontainer,
            position=(50, v),
            configkey='Modifier Count',
            minval=0,
            maxval=8,
            increment=1,
            xoffset=80,
            f=0,
        )

        v -= self._spacing * 0.8
        bui.textwidget(
            parent=self._subcontainer,
            position=(self._sub_width * 0.5, v + 10),
            size=(0, 0),
            text='A modifier count of 4 or above is not recommended.',
            maxwidth=self._sub_width * 0.9,
            max_height=55,
            flatness=1.0,
            scale=0.65,
            color=(1, 1, 0, 0.8),
            h_align='center',
            v_align='center',
        )
        v -= self._spacing * 1.2

        self._chaos_modifier_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Chaos Modifier',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._gamble_modifier_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Gamble Modifier',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._impenetrable_modifier_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Impenetrable Modifier',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._low_gravity_modifier_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Low-Gravity Modifier',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._mini_bombs_modifier_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Mini-Bombs Modifier',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._mini_punch_modifier_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Mini-Punch Modifier',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._no_powerups_modifier_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='No-Powerups Modifier',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._omni_punch_modifier_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Omni-Punch Modifier',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._spaz_rain_modifier_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Spaz-Rain Modifier',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._super_bombs_modifier_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Super-Bombs Modifier',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._third_party_modifier_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Third-Party Modifier',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._unbalanced_modifier_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Unbalanced Modifier',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._untested_modifier_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Untested Modifier',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._vulnerable_modifier_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Vulnerable Modifier',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.5

        self._overclocked_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Allow Overcharged Modifiers',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 2.5

        self._powerup_popups_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Disable Powerup Pop-ups',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 1.2

        self._cheats_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Allow Admin Panel (Will Disable Leaderboards)',
            scale=1.0,
            maxwidth=430,
        )

        v -= self._spacing * 2.5

        self._vanillaclocked_checkbox = ConfigCheckBox(
            parent=self._subcontainer,
            position=(50, v),
            size=(self._sub_width - 100, 30),
            configkey='Vanillaclocked',
            scale=1.0,
            maxwidth=430,
            value_change_call=restart,
        )

        v -= self._spacing * 1.4

        bui.textwidget(
            parent=self._subcontainer,
            position=(self._sub_width * 0.5, v + 10),
            size=(0, 0),
            text='This allows BombSquad players to join without installing\n'
            'OVERCLOCKED by disabling some features and replacing\nsome '
            'assets.',
            maxwidth=self._sub_width * 0.9,
            max_height=55,
            flatness=1.0,
            scale=0.65,
            color=(0.4, 0.9, 0.4, 0.8),
            h_align='center',
            v_align='center',
        )

        self._restore_state()

    # noinspection PyUnresolvedReferences
    @staticmethod
    def _preload_modules() -> None:
        """Preload modules we use (called in bg thread)."""
        from bauiv1lib import config as _unused1

    def _save_state(self) -> None:
        # pylint: disable=too-many-branches
        try:
            sel = self._root_widget.get_selected_child()
            if sel == self._scrollwidget:
                sel = self._subcontainer.get_selected_child()
                if sel == self._at_the_end_of_space_theme_checkbox.widget:
                    sel_name = 'AtTheEndOfSpaceTheme'
                elif sel == self._at_the_end_of_time_theme_checkbox.widget:
                    sel_name = 'AtTheEndOfTimeTheme'
                elif sel == self._autumn_theme_checkbox.widget:
                    sel_name = 'AutumnTheme'
                elif sel == self._cruel_night_theme_checkbox.widget:
                    sel_name = 'CruelNightTheme'
                elif sel == self._minty_toxicity_theme_checkbox.widget:
                    sel_name = 'MintyToxicityTheme'
                elif sel == self._under_the_sakura_theme_checkbox.widget:
                    sel_name = 'UnderTheSakuraTheme'
                elif sel == self._overclocked_checkbox.widget:
                    sel_name = 'OverclockedModifiers'
                elif sel == self._modifier_count_numedit.minusbutton:
                    sel_name = 'ModifierCountMinus'
                elif sel == self._modifier_count_numedit.plusbutton:
                    sel_name = 'ModifierCountPlus'
                elif sel == self._chaos_modifier_checkbox.widget:
                    sel_name = 'ChaosModifier'
                elif sel == self._gamble_modifier_checkbox.widget:
                    sel_name = 'GambleModifier'
                elif sel == self._impenetrable_modifier_checkbox.widget:
                    sel_name = 'ImpenetrableModifier'
                elif sel == self._low_gravity_modifier_checkbox.widget:
                    sel_name = 'LowGravityModifier'
                elif sel == self._mini_bombs_modifier_checkbox.widget:
                    sel_name = 'MiniBombsModifier'
                elif sel == self._mini_punch_modifier_checkbox.widget:
                    sel_name = 'MiniPunchModifier'
                elif sel == self._no_powerups_modifier_checkbox.widget:
                    sel_name = 'NoPowerupsModifier'
                elif sel == self._omni_punch_modifier_checkbox.widget:
                    sel_name = 'OmniPunchModifier'
                elif sel == self._spaz_rain_modifier_checkbox.widget:
                    sel_name = 'SpazRainModifier'
                elif sel == self._super_bombs_modifier_checkbox.widget:
                    sel_name = 'SuperBombsModifier'
                elif sel == self._third_party_modifier_checkbox.widget:
                    sel_name = 'ThirdPartyModifier'
                elif sel == self._unbalanced_modifier_checkbox.widget:
                    sel_name = 'UnbalancedModifier'
                elif sel == self._untested_modifier_checkbox.widget:
                    sel_name = 'UntestedModifier'
                elif sel == self._vulnerable_modifier_checkbox.widget:
                    sel_name = 'VulnerableModifier'
                elif sel == self._powerup_popups_checkbox.widget:
                    sel_name = 'PowerupPopups'
                elif sel == self._cheats_checkbox.widget:
                    sel_name = 'Cheats'
                elif sel == self._vanillaclocked_checkbox.widget:
                    sel_name = 'Vanillaclocked'
                else:
                    raise ValueError(f'unrecognized selection \'{sel}\'')
            elif sel == self._back_button:
                sel_name = 'Back'
            else:
                raise ValueError(f'unrecognized selection \'{sel}\'')
            assert bui.app.classic is not None
            bui.app.ui_v1.window_states[type(self)] = {'sel_name': sel_name}

        except Exception:
            logging.exception('Error saving state for %s.', self)

    def _restore_state(self) -> None:
        # pylint: disable=too-many-branches
        try:
            assert bui.app.classic is not None
            sel_name = bui.app.ui_v1.window_states.get(type(self), {}).get(
                'sel_name'
            )
            if sel_name == 'Back':
                sel = self._back_button
            else:
                bui.containerwidget(
                    edit=self._root_widget, selected_child=self._scrollwidget
                )
                if sel_name == 'AtTheEndOfSpaceTheme':
                    sel = self._at_the_end_of_space_theme_checkbox.widget
                elif sel_name == 'AtTheEndOfTimeTheme':
                    sel = self._at_the_end_of_time_theme_checkbox.widget
                elif sel_name == 'AutumnTheme':
                    sel = self._autumn_theme_checkbox.widget
                elif sel_name == 'CruelNightTheme':
                    sel = self._cruel_night_theme_checkbox.widget
                elif sel_name == 'MintyToxicityTheme':
                    sel = self._minty_toxicity_theme_checkbox.widget
                elif sel_name == 'UnderTheSakuraTheme':
                    sel = self._under_the_sakura_theme_checkbox.widget
                elif sel_name == 'OverclockedModifiers':
                    sel = self._overclocked_checkbox.widget
                elif sel_name == 'ModifierCountMinus':
                    sel = self._modifier_count_numedit.minusbutton
                elif sel_name == 'ModifierCountPlus':
                    sel = self._modifier_count_numedit.plusbutton
                elif sel_name == 'ChaosModifier':
                    sel = self._chaos_modifier_checkbox.widget
                elif sel_name == 'GambleModifier':
                    sel = self._gamble_modifier_checkbox.widget
                elif sel_name == 'ImpenetrableModifier':
                    sel = self._impenetrable_modifier_checkbox.widget
                elif sel_name == 'LowGravityModifier':
                    sel = self._low_gravity_modifier_checkbox.widget
                elif sel_name == 'MiniBombsModifier':
                    sel = self._mini_bombs_modifier_checkbox.widget
                elif sel_name == 'MiniPunchModifier':
                    sel = self._mini_punch_modifier_checkbox.widget
                elif sel_name == 'NoPowerupsModifier':
                    sel = self._no_powerups_modifier_checkbox.widget
                elif sel_name == 'OmniPunchModifier':
                    sel = self._omni_punch_modifier_checkbox.widget
                elif sel_name == 'SpazRainModifier':
                    sel = self._spaz_rain_modifier_checkbox.widget
                elif sel_name == 'SuperBombsModifier':
                    sel = self._super_bombs_modifier_checkbox.widget
                elif sel_name == 'ThirdPartyModifier':
                    sel = self._third_party_modifier_checkbox.widget
                elif sel_name == 'UnbalancedModifier':
                    sel = self._unbalanced_modifier_checkbox.widget
                elif sel_name == 'UntestedModifier':
                    sel = self._untested_modifier_checkbox.widget
                elif sel_name == 'VulnerableModifier':
                    sel = self._vulnerable_modifier_checkbox.widget
                elif sel_name == 'PowerupPopups':
                    sel = self._powerup_popups_checkbox.widget
                elif sel_name == 'Cheats':
                    sel = self._cheats_checkbox.widget
                elif sel_name == 'Vanillaclocked':
                    sel = self._vanillaclocked_checkbox.widget
                else:
                    sel = None
                if sel is not None:
                    bui.containerwidget(
                        edit=self._subcontainer,
                        selected_child=sel,
                        visible_child=sel,
                    )
        except Exception:
            logging.exception('Error restoring state for %s.', self)

    def _do_back(self) -> None:
        from bauiv1lib.settings.allsettings import AllSettingsWindow

        # no-op if our underlying widget is dead or on its way out.
        if not self._root_widget or self._root_widget.transitioning_out:
            return

        self._save_state()
        bui.containerwidget(
            edit=self._root_widget, transition=self._transition_out
        )
        assert bui.app.classic is not None
        bui.app.ui_v1.set_main_menu_window(
            AllSettingsWindow(transition='in_left').get_root_widget(),
            from_window=self._root_widget,
        )
