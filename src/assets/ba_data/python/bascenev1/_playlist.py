# Released under AGPL-3.0-or-later. See LICENSE for details.
#
# This file incorporates work covered by the following permission notice:
#   Released under the MIT License. See LICENSE for details.
#
"""Playlist related functionality."""

from __future__ import annotations

import copy
import logging
from typing import Any, TYPE_CHECKING

import babase

if TYPE_CHECKING:
    from typing import Sequence

    from bascenev1._session import Session

PlaylistType = list[dict[str, Any]]


def filter_playlist(
    playlist: PlaylistType,
    sessiontype: type[Session],
    add_resolved_type: bool = False,
    remove_unowned: bool = True,
    mark_unowned: bool = False,
    name: str = '?',
) -> PlaylistType:
    """Return a filtered version of a playlist.

    Strips out or replaces invalid or unowned game types, makes sure all
    settings are present, and adds in a 'resolved_type' which is the actual
    type.
    """
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    from bascenev1._map import get_filtered_map_name
    from bascenev1._gameactivity import GameActivity

    assert babase.app.classic is not None

    goodlist: list[dict] = []
    unowned_maps: Sequence[str]
    available_maps: list[str] = list(babase.app.classic.maps.keys())
    if (remove_unowned or mark_unowned) and babase.app.classic is not None:
        unowned_maps = babase.app.classic.store.get_unowned_maps()
        unowned_game_types = babase.app.classic.store.get_unowned_game_types()
    else:
        unowned_maps = []
        unowned_game_types = set()

    for entry in copy.deepcopy(playlist):
        # 'map' used to be called 'level' here.
        if 'level' in entry:
            entry['map'] = entry['level']
            del entry['level']

        # We now stuff map into settings instead of it being its own thing.
        if 'map' in entry:
            entry['settings']['map'] = entry['map']
            del entry['map']

        # Update old map names to new ones.
        entry['settings']['map'] = get_filtered_map_name(
            entry['settings']['map']
        )
        if remove_unowned and entry['settings']['map'] in unowned_maps:
            continue

        # Ok, for each game in our list, try to import the module and grab
        # the actual game class. add successful ones to our initial list
        # to present to the user.
        if not isinstance(entry['type'], str):
            raise TypeError('invalid entry format')
        try:
            # Do some type filters for backwards compat.
            if entry['type'] in (
                'Assault.AssaultGame',
                'Happy_Thoughts.HappyThoughtsGame',
                'bsAssault.AssaultGame',
                'bs_assault.AssaultGame',
                'bastd.game.assault.AssaultGame',
            ):
                entry['type'] = 'bascenev1lib.game.assault.AssaultGame'
            if entry['type'] in (
                'King_of_the_Hill.KingOfTheHillGame',
                'bsKingOfTheHill.KingOfTheHillGame',
                'bs_king_of_the_hill.KingOfTheHillGame',
                'bastd.game.kingofthehill.KingOfTheHillGame',
            ):
                entry[
                    'type'
                ] = 'bascenev1lib.game.kingofthehill.KingOfTheHillGame'
            if entry['type'] in (
                'Capture_the_Flag.CTFGame',
                'bsCaptureTheFlag.CTFGame',
                'bs_capture_the_flag.CTFGame',
                'bastd.game.capturetheflag.CaptureTheFlagGame',
            ):
                entry[
                    'type'
                ] = 'bascenev1lib.game.capturetheflag.CaptureTheFlagGame'
            if entry['type'] in (
                'Death_Match.DeathMatchGame',
                'bsDeathMatch.DeathMatchGame',
                'bs_death_match.DeathMatchGame',
                'bastd.game.deathmatch.DeathMatchGame',
            ):
                entry['type'] = 'bascenev1lib.game.deathmatch.DeathMatchGame'
            if entry['type'] in (
                'ChosenOne.ChosenOneGame',
                'bsChosenOne.ChosenOneGame',
                'bs_chosen_one.ChosenOneGame',
                'bastd.game.chosenone.ChosenOneGame',
            ):
                entry['type'] = 'bascenev1lib.game.chosenone.ChosenOneGame'
            if entry['type'] in (
                'Conquest.Conquest',
                'Conquest.ConquestGame',
                'bsConquest.ConquestGame',
                'bs_conquest.ConquestGame',
                'bastd.game.conquest.ConquestGame',
            ):
                entry['type'] = 'bascenev1lib.game.conquest.ConquestGame'
            if entry['type'] in (
                'Elimination.EliminationGame',
                'bsElimination.EliminationGame',
                'bs_elimination.EliminationGame',
                'bastd.game.elimination.EliminationGame',
            ):
                entry['type'] = 'bascenev1lib.game.elimination.EliminationGame'
            if entry['type'] in (
                'Football.FootballGame',
                'bsFootball.FootballTeamGame',
                'bs_football.FootballTeamGame',
                'bastd.game.football.FootballTeamGame',
            ):
                entry['type'] = 'bascenev1lib.game.football.FootballTeamGame'
            if entry['type'] in (
                'Hockey.HockeyGame',
                'bsHockey.HockeyGame',
                'bs_hockey.HockeyGame',
                'bastd.game.hockey.HockeyGame',
            ):
                entry['type'] = 'bascenev1lib.game.hockey.HockeyGame'
            if entry['type'] in (
                'Keep_Away.KeepAwayGame',
                'bsKeepAway.KeepAwayGame',
                'bs_keep_away.KeepAwayGame',
                'bastd.game.keepaway.KeepAwayGame',
            ):
                entry['type'] = 'bascenev1lib.game.keepaway.KeepAwayGame'
            if entry['type'] in (
                'Race.RaceGame',
                'bsRace.RaceGame',
                'bs_race.RaceGame',
                'bastd.game.race.RaceGame',
            ):
                entry['type'] = 'bascenev1lib.game.race.RaceGame'
            if entry['type'] in (
                'bsEasterEggHunt.EasterEggHuntGame',
                'bs_easter_egg_hunt.EasterEggHuntGame',
                'bastd.game.easteregghunt.EasterEggHuntGame',
            ):
                entry[
                    'type'
                ] = 'bascenev1lib.game.easteregghunt.EasterEggHuntGame'
            if entry['type'] in (
                'bsMeteorShower.MeteorShowerGame',
                'bs_meteor_shower.MeteorShowerGame',
                'bastd.game.meteorshower.MeteorShowerGame',
            ):
                entry[
                    'type'
                ] = 'bascenev1lib.game.meteorshower.MeteorShowerGame'
            if entry['type'] in (
                'bsTargetPractice.TargetPracticeGame',
                'bs_target_practice.TargetPracticeGame',
                'bastd.game.targetpractice.TargetPracticeGame',
            ):
                entry[
                    'type'
                ] = 'bascenev1lib.game.targetpractice.TargetPracticeGame'
            if entry['type'] == 'bastd.game.assassination.AssassinationGame':
                entry[
                    'type'
                ] = 'bascenev1lib.game.assassination.AssassinationGame'
            if entry['type'] == 'bastd.game.packapunch.PackAPunchGame':
                entry['type'] = 'bascenev1lib.game.packapunch.PackAPunchGame'
            if entry['type'] == 'bastd.game.runningbombs.GameRunningBombs':
                entry[
                    'type'
                ] = 'bascenev1lib.game.runningbombs.RunningBombsGame'
            if entry['type'] == 'bastd.game.soccer.SoccerGame':
                entry['type'] = 'bascenev1lib.game.soccer.SoccerGame'
            if entry['type'] == 'bastd.game.village.VillageGame':
                entry['type'] = 'bascenev1lib.game.village.VillageGame'

            gameclass = babase.getclass(entry['type'], GameActivity)

            if entry['settings']['map'] not in available_maps:
                raise babase.MapNotFoundError()

            if remove_unowned and gameclass in unowned_game_types:
                continue
            if add_resolved_type:
                entry['resolved_type'] = gameclass
            if mark_unowned and entry['settings']['map'] in unowned_maps:
                entry['is_unowned_map'] = True
            if mark_unowned and gameclass in unowned_game_types:
                entry['is_unowned_game'] = True

            # Make sure all settings the game defines are present.
            neededsettings = gameclass.get_available_settings(sessiontype)
            for setting in neededsettings:
                if setting.name not in entry['settings']:
                    entry['settings'][setting.name] = setting.default

            goodlist.append(entry)

        except babase.MapNotFoundError:
            logging.warning(
                'Map \'%s\' not found while scanning playlist \'%s\'.',
                entry['settings']['map'],
                name,
            )
        except ImportError as exc:
            logging.warning(
                'Import failed while scanning playlist \'%s\': %s', name, exc
            )
        except Exception:
            logging.exception('Error in filter_playlist.')

    return goodlist


def get_default_free_for_all_playlist() -> PlaylistType:
    """Return a default playlist for free-for-all mode."""

    return [
        {
            'settings': {
                'Allow Negative Scores': False,
                'Epic Mode': False,
                'Kills to Win Per Player': 10,
                'Respawn Times': 1.0,
                'Time Limit': 300,
                'map': 'Doom Shroom',
            },
            'type': 'bascenev1lib.game.deathmatch.DeathMatchGame',
        },
        {
            'settings': {
                'Allow Negative Scores (Deathmatch Exclusive)': False,
                'Epic Mode': True,
                'Game mode': 1,
                'Lives or Kills to Win Per Player': 1,
                'Respawn Times': 1.0,
                'Time Limit': 60,
                'map': 'Step Right Up',
            },
            'type': 'bascenev1lib.game.smash.SmashGame',
        },
        {
            'settings': {
                'Basic Bombs': True,
                'Epic Mode': False,
                'Grabbing only': True,
                'Ice Bombs': True,
                'Ice Trigger Bombs': True,
                'Impulse Bombs': True,
                'Punching only': True,
                'Respawn Times': 1.0,
                'Sticky Bombs': True,
                'Time Limit': 600,
                'Trigger Bombs': True,
                'map': 'Bridgit',
            },
            'type': 'bascenev1lib.game.armsrace.ArmsRaceGame',
        },
        {
            'settings': {
                'Chosen One Gets Gloves': True,
                'Chosen One Gets Shield': False,
                'Chosen One Time': 20,
                'Epic Mode': False,
                'Respawn Times': 1.0,
                'Time Limit': 120,
                'map': 'Hockey Stadium',
            },
            'type': 'bascenev1lib.game.frozenone.FrozenOneGame',
        },
        {
            'settings': {'Epic Mode': False, 'map': 'Lake Frigid'},
            'type': 'bascenev1lib.game.icyemits.IcyEmitsGame',
        },
        {
            'settings': {
                'Enable Bottom Credit': False,
                'Enable Punching': False,
                'Enable Running': False,
                'Epic Mode': False,
                'Max Round Time': 25,
                'map': 'Doom Shroom',
            },
            'type': 'bascenev1lib.game.musicalflags.MusicalFlagsGame',
        },
        {
            'settings': {
                'Enable Bomb': False,
                'Enable Jump': True,
                'Enable Pickup': False,
                'Epic Mode': True,
                'Fast Movespeed': True,
                'Kills to Win Per Player': 5,
                'Obstacle Count': 16,
                'Obstacles': True,
                'Obstacles Bounces Shots': True,
                'Obstacles Shape': 5,
                'Random Obstacle Color': True,
                'Respawn Times': 1.0,
                'Time Limit': 60,
                'map': 'Football Stadium',
            },
            'type': 'bascenev1lib.game.quake.QuakeGame',
        },
        {
            'settings': {
                'Allow Negative Scores (Deathmatch Exclusive)': False,
                'Epic Mode': False,
                'Game mode': 2,
                'Lives or Kills to Win Per Player': 5,
                'Respawn Times': 1.0,
                'Time Limit': 120,
                'map': 'Courtyard',
            },
            'type': 'bascenev1lib.game.smash.SmashGame',
        },
        {
            'settings': {
                'Enable Bomb': False,
                'Enable Jump': True,
                'Enable Pickup': False,
                'Epic Mode': False,
                'Fast Movespeed': True,
                'Kills to Win Per Player': 5,
                'Obstacle Count': 16,
                'Obstacles': True,
                'Obstacles Bounces Shots': False,
                'Obstacles Shape': 5,
                'Random Obstacle Color': True,
                'Respawn Times': 1.0,
                'Time Limit': 120,
                'map': 'Doom Shroom',
            },
            'type': 'bascenev1lib.game.quake.QuakeGame',
        },
        {
            'settings': {
                'Allow Negative Scores': False,
                'Epic Mode': False,
                'Extra Seconds for Assassination per Target Suicide/Betrayal':
                    1,
                'Negative Points for Killing Others': 0,
                'Points for Killing The Target': 2,
                'Points for Surviving an Assassination': 3,
                'Points to Win': 10,
                'Respawn Times': 0.5,
                'Seconds for Assassination': 20,
                'Time Limit': 0,
                'map': 'Step Right Up',
            },
            'type': 'bascenev1lib.game.assassination.AssassinationGame',
        },
        {
            'settings': {
                'Allow Grabbing': True,
                'Allow Negative Scores (Deathmatch Exclusive)': False,
                'Boxing Gloves': True,
                'Epic Mode': True,
                'Game mode': 1,
                'Lives or Kills to Win Per Player': 1,
                'Player Health': 1000,
                'Random Chance of Saviors on Impact': True,
                'Respawn Times': 1.0,
                'Time Limit': 60,
                'map': 'Tip Top',
            },
            'type': 'bascenev1lib.game.packapunch.PackAPunchGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Random bombs spawn': True,
                'map': 'Football Stadium',
            },
            'type': 'bascenev1lib.game.runningbombs.RunningBombsGame',
        },
        {
            'settings': {
                'Chosen One Gets Gloves': True,
                'Chosen One Gets Shield': False,
                'Chosen One Time': 30,
                'Epic Mode': 0,
                'Respawn Times': 1.0,
                'Time Limit': 300,
                'map': 'Monkey Face',
            },
            'type': 'bascenev1lib.game.chosenone.ChosenOneGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Hold Time': 30,
                'Respawn Times': 1.0,
                'Time Limit': 300,
                'map': 'Zigzag',
            },
            'type': 'bascenev1lib.game.kingofthehill.KingOfTheHillGame',
        },
        {
            'settings': {'Epic Mode': False, 'map': 'Rampage'},
            'type': 'bascenev1lib.game.meteorshower.MeteorShowerGame',
        },
        {
            'settings': {
                'Epic Mode': 1,
                'Lives Per Player': 1,
                'Respawn Times': 1.0,
                'Time Limit': 120,
                'map': 'Tip Top',
            },
            'type': 'bascenev1lib.game.elimination.EliminationGame',
        },
        {
            'settings': {
                'Allow Grabbing': True,
                'Allow Negative Scores (Deathmatch Exclusive)': True,
                'Boxing Gloves': True,
                'Epic Mode': False,
                'Game mode': 2,
                'Lives or Kills to Win Per Player': 5,
                'Player Health': 200,
                'Random Chance of Saviors on Impact': True,
                'Respawn Times': 1.0,
                'Time Limit': 300,
                'map': 'Lake Frigid',
            },
            'type': 'bascenev1lib.game.packapunch.PackAPunchGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Hold Time': 30,
                'Respawn Times': 1.0,
                'Time Limit': 300,
                'map': 'The Pad',
            },
            'type': 'bascenev1lib.game.keepaway.KeepAwayGame',
        },
        {
            'settings': {
                'Allow Negative Scores': False,
                'Epic Mode': True,
                'Kills to Win Per Player': 10,
                'Respawn Times': 0.25,
                'Time Limit': 120,
                'map': 'Rampage',
            },
            'type': 'bascenev1lib.game.deathmatch.DeathMatchGame',
        },
        {
            'settings': {
                'Bomb Spawning': 1000,
                'Epic Mode': False,
                'Laps': 3,
                'Mine Spawn Interval': 4000,
                'Mine Spawning': 4000,
                'Time Limit': 300,
                'map': 'Big G',
            },
            'type': 'bascenev1lib.game.race.RaceGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Hold Time': 30,
                'Respawn Times': 1.0,
                'Time Limit': 300,
                'map': 'Happy Thoughts',
            },
            'type': 'bascenev1lib.game.kingofthehill.KingOfTheHillGame',
        },
        {
            'settings': {
                'Enable Impact Bombs': 1,
                'Enable Triple Bombs': False,
                'Target Count': 2,
                'map': 'Doom Shroom',
            },
            'type': 'bascenev1lib.game.targetpractice.TargetPracticeGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Lives Per Player': 5,
                'Respawn Times': 1.0,
                'Time Limit': 300,
                'map': 'Step Right Up',
            },
            'type': 'bascenev1lib.game.elimination.EliminationGame',
        },
        {
            'settings': {
                'Allow Negative Scores': False,
                'Epic Mode': False,
                'Kills to Win Per Player': 10,
                'Respawn Times': 1.0,
                'Time Limit': 300,
                'map': 'Crag Castle',
            },
            'type': 'bascenev1lib.game.deathmatch.DeathMatchGame',
        },
        {
            'settings': {
                'Bomb Spawning': 0,
                'Epic Mode': False,
                'Laps': 6,
                'Mine Spawning': 2000,
                'Time Limit': 300,
                'map': 'Lake Frigid',
            },
            'type': 'bascenev1lib.game.race.RaceGame',
        },
    ]


def get_default_teams_playlist() -> PlaylistType:
    """Return a default playlist for teams mode."""

    return [
        {
            'settings': {
                'Epic Mode': False,
                'Flag Idle Return Time': 30,
                'Flag Touch Return Time': 0,
                'Respawn Times': 1.0,
                'Score to Win': 3,
                'Time Limit': 120,
                'map': 'Bridgit',
            },
            'type': 'bascenev1lib.game.capturetheflag.CaptureTheFlagGame',
        },
        {
            'settings': {
                'Balance Total Lives (Elimination Exclusive)': False,
                'Epic Mode': True,
                'Game mode': 1,
                'Lives or Kills to Win Per Player': 1,
                'Respawn Times': 1.0,
                'Solo Mode (Elimination Exclusive)': False,
                'Time Limit': 60,
                'map': 'Step Right Up',
            },
            'type': 'bascenev1lib.game.smash.SmashGame',
        },
        {
            'settings': {
                'Enable Bomb': False,
                'Enable Jump': True,
                'Enable Pickup': False,
                'Epic Mode': False,
                'Fast Movespeed': True,
                'Kills to Win Per Player': 5,
                'Obstacle Count': 16,
                'Obstacles': True,
                'Obstacles Bounces Shots': False,
                'Obstacles Shape': 5,
                'Random Obstacle Color': True,
                'Respawn Times': 1.0,
                'Time Limit': 120,
                'map': 'Doom Shroom',
            },
            'type': 'bascenev1lib.game.quake.QuakeGame',
        },
        {
            'settings': {
                'Balance Total Lives (Elimination Exclusive)': False,
                'Epic Mode': False,
                'Game mode': 2,
                'Lives or Kills to Win Per Player': 5,
                'Respawn Times': 1.0,
                'Solo Mode (Elimination Exclusive)': False,
                'Time Limit': 120,
                'map': 'Courtyard',
            },
            'type': 'bascenev1lib.game.smash.SmashGame',
        },
        {
            'settings': {
                'Enable Bomb': False,
                'Enable Jump': True,
                'Enable Pickup': False,
                'Epic Mode': True,
                'Fast Movespeed': True,
                'Kills to Win Per Player': 5,
                'Obstacle Count': 16,
                'Obstacles': True,
                'Obstacles Bounces Shots': True,
                'Obstacles Shape': 5,
                'Random Obstacle Color': True,
                'Respawn Times': 1.0,
                'Time Limit': 60,
                'map': 'Football Stadium',
            },
            'type': 'bascenev1lib.game.quake.QuakeGame',
        },
        {
            'settings': {
                'Basic Bombs': True,
                'Epic Mode': False,
                'Grabbing only': True,
                'Ice Bombs': True,
                'Ice Trigger Bombs': True,
                'Impulse Bombs': True,
                'Punching only': True,
                'Respawn Times': 1.0,
                'Sticky Bombs': True,
                'Time Limit': 0,
                'Trigger Bombs': True,
                'map': 'Zigzag',
            },
            'type': 'bascenev1lib.game.armsrace.ArmsRaceGame',
        },
        {
            'settings': {
                'Chosen One Gets Gloves': True,
                'Chosen One Gets Shield': False,
                'Chosen One Time': 20,
                'Epic Mode': False,
                'Respawn Times': 1.0,
                'Time Limit': 120,
                'map': 'Hockey Stadium',
            },
            'type': 'bascenev1lib.game.frozenone.FrozenOneGame',
        },
        {
            'settings': {'Epic Mode': False, 'map': 'Lake Frigid'},
            'type': 'bascenev1lib.game.icyemits.IcyEmitsGame',
        },
        {
            'settings': {
                'Enable Bottom Credit': False,
                'Enable Punching': False,
                'Enable Running': False,
                'Epic Mode': False,
                'Max Round Time': 25,
                'map': 'Doom Shroom',
            },
            'type': 'bascenev1lib.game.musicalflags.MusicalFlagsGame',
        },
        {
            'settings': {
                'Disable Bombs': False,
                'Disable Punch': False,
                'Enable Bottom Credits': False,
                'Epic Mode': True,
                'Icy Floor': True,
                'Respawn Times': 1.0,
                'Score to Win': 5,
                'Time Limit': 120,
                'map': 'Closed Arena',
            },
            'type': 'bascenev1lib.game.volleyball.VolleyBallGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Random bombs spawn': True,
                'map': 'Football Stadium',
            },
            'type': 'bascenev1lib.game.runningbombs.RunningBombsGame',
        },
        {
            'settings': {
                'Allow Bombs': False,
                'Allow Powerups': False,
                'Epic Mode': False,
                'Respawn Times': 1.0,
                'Score to Win': 5,
                'Time Limit': 300,
                'map': 'Soccer Stadium',
            },
            'type': 'bascenev1lib.game.soccer.SoccerGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Extra Seconds for Assassination per Target Suicide/Betrayal':
                    2,
                'Negative Points for Killing Others': 0,
                'Points for Killing The Target': 2,
                'Points for Surviving an Assassination': 3,
                'Points to Win': 10,
                'Respawn Times': 1.0,
                'Seconds for Assassination': 30,
                'Time Limit': 0,
                'map': 'Happy Thoughts',
            },
            'type': 'bascenev1lib.game.assassination.AssassinationGame',
        },
        {
            'settings': {'Epic Mode': False, 'map': 'Crag Castle'},
            'type': 'bascenev1lib.game.meteorshower.MeteorShowerGame',
        },
        {
            'settings': {
                'Allow Grabbing': True,
                'Balance Total Lives (Elimination Exclusive)': False,
                'Boxing Gloves': True,
                'Epic Mode': False,
                'Game mode': 1,
                'Lives or Kills to Win Per Player': 5,
                'Player Health': 1000,
                'Random Chance of Saviors on Impact': True,
                'Respawn Times': 1.0,
                'Solo Mode (Elimination Exclusive)': False,
                'Time Limit': 300,
                'map': 'Tip Top',
            },
            'type': 'bascenev1lib.game.packapunch.PackAPunchGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Extra Seconds for Assassination per Target Suicide/Betrayal':
                    1,
                'Negative Points for Killing Others': 0,
                'Points for Killing The Target': 2,
                'Points for Surviving an Assassination': 3,
                'Points to Win': 10,
                'Respawn Times': 0.5,
                'Seconds for Assassination': 20,
                'Time Limit': 0,
                'map': 'Crag Castle',
            },
            'type': 'bascenev1lib.game.assassination.AssassinationGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Respawn Times': 1.0,
                'Score to Win': 3,
                'Time Limit': 300,
                'map': 'Step Right Up',
            },
            'type': 'bascenev1lib.game.assault.AssaultGame',
        },
        {
            'settings': {
                'Allow Grabbing': True,
                'Balance Total Lives (Elimination Exclusive)': False,
                'Boxing Gloves': True,
                'Epic Mode': False,
                'Game mode': 2,
                'Lives or Kills to Win Per Player': 5,
                'Player Health': 1000,
                'Random Chance of Saviors on Impact': True,
                'Respawn Times': 1.0,
                'Solo Mode (Elimination Exclusive)': False,
                'Time Limit': 300,
                'map': 'Doom Shroom',
            },
            'type': 'bascenev1lib.game.packapunch.PackAPunchGame',
        },
        {
            'settings': {
                'Balance Total Lives': False,
                'Epic Mode': False,
                'Lives Per Player': 3,
                'Respawn Times': 1.0,
                'Solo Mode': True,
                'Time Limit': 300,
                'map': 'Rampage',
            },
            'type': 'bascenev1lib.game.elimination.EliminationGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Kills to Win Per Player': 5,
                'Respawn Times': 1.0,
                'Time Limit': 300,
                'map': 'Roundabout',
            },
            'type': 'bascenev1lib.game.deathmatch.DeathMatchGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Respawn Times': 1.0,
                'Score to Win': 3,
                'Time Limit': 120,
                'map': 'Hockey Stadium',
            },
            'type': 'bascenev1lib.game.hockey.HockeyGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Hold Time': 30,
                'Respawn Times': 1.0,
                'Time Limit': 300,
                'map': 'Monkey Face',
            },
            'type': 'bascenev1lib.game.keepaway.KeepAwayGame',
        },
        {
            'settings': {
                'Balance Total Lives': False,
                'Epic Mode': True,
                'Lives Per Player': 1,
                'Respawn Times': 1.0,
                'Solo Mode': False,
                'Time Limit': 60,
                'map': 'Tip Top',
            },
            'type': 'bascenev1lib.game.elimination.EliminationGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Respawn Times': 1.0,
                'Score to Win': 3,
                'Time Limit': 300,
                'map': 'Crag Castle',
            },
            'type': 'bascenev1lib.game.assault.AssaultGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Kills to Win Per Player': 5,
                'Respawn Times': 1.0,
                'Time Limit': 300,
                'map': 'Doom Shroom',
            },
            'type': 'bascenev1lib.game.deathmatch.DeathMatchGame',
        },
        {
            'settings': {'Epic Mode': False, 'map': 'Rampage'},
            'type': 'bascenev1lib.game.meteorshower.MeteorShowerGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Flag Idle Return Time': 30,
                'Flag Touch Return Time': 0,
                'Respawn Times': 1.0,
                'Score to Win': 2,
                'Time Limit': 300,
                'map': 'Roundabout',
            },
            'type': 'bascenev1lib.game.capturetheflag.CaptureTheFlagGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Respawn Times': 1.0,
                'Score to Win': 21,
                'Time Limit': 300,
                'map': 'Football Stadium',
            },
            'type': 'bascenev1lib.game.football.FootballTeamGame',
        },
        {
            'settings': {
                'Epic Mode': True,
                'Respawn Times': 0.25,
                'Score to Win': 3,
                'Time Limit': 60,
                'map': 'Bridgit',
            },
            'type': 'bascenev1lib.game.assault.AssaultGame',
        },
        {
            'settings': {
                'Enable Impact Bombs': 1,
                'Enable Triple Bombs': False,
                'Target Count': 2,
                'map': 'Doom Shroom',
            },
            'type': 'bascenev1lib.game.targetpractice.TargetPracticeGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Hold Time': 30,
                'Respawn Times': 1.0,
                'Time Limit': 300,
                'map': 'Tip Top',
            },
            'type': 'bascenev1lib.game.kingofthehill.KingOfTheHillGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Respawn Times': 1.0,
                'Score to Win': 2,
                'Time Limit': 300,
                'map': 'Zigzag',
            },
            'type': 'bascenev1lib.game.assault.AssaultGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Flag Idle Return Time': 30,
                'Flag Touch Return Time': 0,
                'Respawn Times': 1.0,
                'Score to Win': 3,
                'Time Limit': 300,
                'map': 'Happy Thoughts',
            },
            'type': 'bascenev1lib.game.capturetheflag.CaptureTheFlagGame',
        },
        {
            'settings': {
                'Bomb Spawning': 1000,
                'Entire Team Must Finish': False,
                'Epic Mode': True,
                'Laps': 1,
                'Mine Spawning': 2000,
                'Time Limit': 300,
                'map': 'Big G',
            },
            'type': 'bascenev1lib.game.race.RaceGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Kills to Win Per Player': 5,
                'Respawn Times': 1.0,
                'Time Limit': 300,
                'map': 'Monkey Face',
            },
            'type': 'bascenev1lib.game.deathmatch.DeathMatchGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Hold Time': 30,
                'Respawn Times': 1.0,
                'Time Limit': 300,
                'map': 'Lake Frigid',
            },
            'type': 'bascenev1lib.game.keepaway.KeepAwayGame',
        },
        {
            'settings': {
                'Epic Mode': False,
                'Flag Idle Return Time': 30,
                'Flag Touch Return Time': 3,
                'Respawn Times': 1.0,
                'Score to Win': 2,
                'Time Limit': 300,
                'map': 'Tip Top',
            },
            'type': 'bascenev1lib.game.capturetheflag.CaptureTheFlagGame',
        },
        {
            'settings': {
                'Balance Total Lives': False,
                'Epic Mode': False,
                'Lives Per Player': 3,
                'Respawn Times': 1.0,
                'Solo Mode': False,
                'Time Limit': 300,
                'map': 'Crag Castle',
            },
            'type': 'bascenev1lib.game.elimination.EliminationGame',
        },
        {
            'settings': {
                'Epic Mode': True,
                'Respawn Times': 0.25,
                'Time Limit': 120,
                'map': 'Zigzag',
            },
            'type': 'bascenev1lib.game.conquest.ConquestGame',
        },
    ]
