# Released under AGPL-3.0-or-later. See LICENSE for details.
#
# This file incorporates work covered by the following permission notice:
#   Released under the MIT License. See LICENSE for details.
#
"""Snippets of code for use by the c++ layer."""
# (most of these are self-explanatory)
# pylint: disable=missing-function-docstring
from __future__ import annotations

from typing import TYPE_CHECKING

import os
import time
import random

from era import gdata
import babase
import _bascenev1
from era.utils import inform, rankint

if TYPE_CHECKING:
    from typing import Any
    import bascenev1


def launch_main_menu_session() -> None:
    assert babase.app.classic is not None

    _bascenev1.new_host_session(babase.app.classic.get_main_menu_session())


def get_player_icon(sessionplayer: bascenev1.SessionPlayer) -> dict[str, Any]:
    info = sessionplayer.get_icon_info()
    return {
        'texture': _bascenev1.gettexture(info['texture']),
        'tint_texture': _bascenev1.gettexture(info['tint_texture']),
        'tint_color': info['tint_color'],
        'tint2_color': info['tint2_color'],
    }


def filter_chat_message(msg: str, client_id: int) -> str | None:
    """Intercept/filter chat messages.

    Called for all chat messages while hosting.
    Messages originating from the host will have clientID -1.
    Should filter and return the string to be displayed, or return None
    to ignore the message.
    """
    activity = _bascenev1.get_foreground_host_activity()
    if activity:
        command = gui_command if babase.app.env.gui else server_command
        if not command(msg, client_id):
            con = activity.context
            for player in activity.players:
                if (
                    player.sessionplayer.inputdevice.client_id == client_id
                    and player.actor
                    and player.actor.node
                ):
                    actr = player.actor
                    with con:
                        import bascenev1 as bs

                        m = bs.newnode(
                            'math',
                            owner=actr.node,
                            attrs={'input1': (0, 2.1, 0), 'operation': 'add'},
                        )
                        actr.node.connectattr('torso_position', m, 'input2')
                        if actr.chat_text:
                            actr.chat_text.delete()
                            actr.chat_text = None
                        actr.chat_text = bs.newnode(
                            'text',
                            owner=actr.node,
                            attrs={
                                'text': msg,
                                'in_world': True,
                                'shadow': 1.0,
                                'flatness': 1.0,
                                'color': (1, 1, 1, 0.8),
                                'scale': 0.01,
                                'h_align': 'center',
                                'v_align': 'bottom',
                            },
                        )
                        m.connectattr('output', actr.chat_text, 'position')
                        actr.chat_text_timer = bs.Timer(
                            5, actr.chat_text.delete
                        )
            return msg
    else:
        return msg


def local_chat_message(msg: str) -> None:
    classic = babase.app.classic
    assert classic is not None
    party_window = (
        None if classic.party_window is None else classic.party_window()
    )

    if party_window is not None:
        party_window.on_chat_message(msg)


def gui_command(msg: str, client_id: int) -> bool:
    if not msg.startswith('/'):
        return False
    stripped_msg = msg[1:]
    msg_splits = stripped_msg.split(' ')
    while '' in msg_splits:
        msg_splits.remove('')
    try:
        cat = msg_splits[0]
        activity = _bascenev1.get_foreground_host_activity()
        session = activity.session
        context = activity.context
        splayer = None
        for spval in session.sessionplayers:
            if spval.inputdevice.client_id == client_id:
                splayer = spval
        plrl = []
        for player in activity.players:
            if player.sessionplayer.inputdevice.client_id == client_id:
                plrl.append(player)

        if cat == 'emote':
            with context:
                for plr in plrl:
                    if not plr.actor:
                        return True
                    plr.actor.emote(msg_splits[1])
            return True
        if not (
            client_id == -1
            and babase.app.config.get(
                'Allow Admin Panel (Will Disable Leaderboards)', False
            )
        ):
            return False
        if cat == 'powerup':
            handle_event(
                context,
                activity,
                ['everyone', 'powerup', msg_splits[1]],
                activity.players,
            )
            return True
        elif cat == 'theme':
            from bascenev1lib.actor.themes import THEME_DICT, NoneTheme

            td = dict(THEME_DICT)
            td['None Theme'] = NoneTheme
            if msg_splits[1] == 'random':
                choice = random.choice(list(td.keys())).split(' ')
                msg_splits[1] = choice[0]
                msg_splits.append(choice[1])
            with context:
                activity.decorate(td[msg_splits[1] + ' ' + msg_splits[2]], True)
            return True
        elif cat == 'modifier':
            with context:
                if msg_splits[1] == 'refresh':
                    activity.apply_modifiers()
                    return True
                if msg_splits[1] == 'renew':
                    activity.apply_modifiers(initial=True)
                    return True
                if msg_splits[1] == 'killall':
                    from bascenev1._messages import DieMessage

                    for amod in activity.active_modifiers:
                        amod.handlemessage(DieMessage())
                    activity.active_modifiers.clear()
                    return True
        elif cat == 'fun':
            if msg_splits[1] == 'killall':
                handle_event(
                    context, activity, ['everyone', 'die'], activity.players
                )
                return True
            if msg_splits[1] == 'blowall':
                handle_event(
                    context,
                    activity,
                    ['everyone', 'explode', 'normal'],
                    activity.players,
                )
                return True
            if msg_splits[1] == 'enda':
                from bascenev1._gameactivity import GameActivity

                with context:
                    if isinstance(activity, GameActivity):
                        activity.end_game()
                    else:
                        activity.end()
                return True
            if msg_splits[1] == 'ends':
                with context:
                    activity.session.end()
                return True
        return False
    except IndexError:
        return False
    except (KeyError, AttributeError):
        return True


def server_command(msg: str, client_id: int) -> bool:
    if not msg.startswith('/'):
        return False
    import bascenev1 as bs

    stripped_msg = msg[1:]
    msg_splits = stripped_msg.split(' ')
    while '' in msg_splits:
        msg_splits.remove('')
    cat = 'help' if len(msg_splits) == 0 else msg_splits[0]
    activity = _bascenev1.get_foreground_host_activity()
    session = activity.session
    context = activity.context
    ginfo = gdata.getpath('ginfo')
    gshop = gdata.getpath('gshop')
    splayer = None
    for spval in session.sessionplayers:
        if spval.inputdevice.client_id == client_id:
            splayer = spval
    spid = splayer.get_v1_account_id() or 'anon'
    plrdatapath = gdata.getpath('gstats/' + spid)
    plrdata = gdata.load(plrdatapath) or {}
    sdpd(plrdata)
    alliancedatapath = None
    alliancedata = None
    if plrdata['allianceidref']:
        alliancedatapath = gdata.getpath(
            'galliances/' + plrdata['allianceidref']
        )
        alliancedata = gdata.load(alliancedatapath)
        alliancedata.setdefault('invref', None)
        alliancedata.setdefault('public', False)
    plrl = []
    for player in activity.players:
        if player.sessionplayer.inputdevice.client_id == client_id:
            plrl.append(player)
    pemote = None

    try:
        if cat == 'code':
            if len(msg_splits) == 1:
                inform('codeUsage', 'normal', client_id, plrdata['lang'])
                return True
            scommand = msg_splits[1]
            if scommand == 'promo':
                pcode = msg_splits[2]
                pval = gdata.load(ginfo, 'pcodes', pcode, update=False)
                if pval and pcode not in plrdata['upcodes']:
                    plrdata['upcodes'].append(pcode)
                    for r in pval:
                        if isinstance(r, int):
                            plrdata['spoints'] += r
                            inform(
                                'successfulCodeRegister',
                                'success',
                                client_id,
                                plrdata['lang'],
                                [str(r) + ' SPoints'],
                            )
                        else:
                            rs = r.split('␟')
                            if any(
                                rs[0] == o.split('␟')[0]
                                for o in plrdata['items'] + plrdata['equipped']
                            ):
                                inform(
                                    'alreadyOwned',
                                    'warning',
                                    client_id,
                                    plrdata['lang'],
                                    [rs[0]],
                                )
                            else:
                                nr = rs[0]
                                if len(rs) == 2:
                                    nr += '␟' + str(time.time() + float(rs[1]))
                                plrdata['items'].append(nr)
                                inform(
                                    'successfulCodeRegister',
                                    'success',
                                    client_id,
                                    plrdata['lang'],
                                    [nr],
                                )
                else:
                    inform('usedCode', 'error', client_id, plrdata['lang'])
            elif scommand == 'purchase':
                pcode = msg_splits[2]
                pval = gdata.load(ginfo, 'purchases', pcode, update=False)
                if pval:
                    ginfod = gdata.load(ginfo, update=False)
                    for r in pval:
                        rm = True
                        if isinstance(r, int):
                            plrdata['spoints'] += r
                            inform(
                                'successfulCodeRegister',
                                'success',
                                client_id,
                                plrdata['lang'],
                                [str(r) + ' SPoints'],
                            )
                        else:
                            rs = r.split('␟')
                            if any(
                                rs[0] == o.split('␟')[0]
                                for o in plrdata['items'] + plrdata['equipped']
                            ):
                                inform(
                                    'alreadyOwned',
                                    'warning',
                                    client_id,
                                    plrdata['lang'],
                                    [rs[0]],
                                )
                                rm = False
                            else:
                                nr = rs[0]
                                if len(rs) == 2:
                                    nr += '␟' + str(time.time() + float(rs[1]))
                                plrdata['items'].append(nr)
                                inform(
                                    'successfulCodeRegister',
                                    'success',
                                    client_id,
                                    plrdata['lang'],
                                    [nr],
                                )
                        if rm:
                            ginfod['purchases'][pcode].remove(r)
                            gdata.write(ginfo, ginfod)
                    if len(ginfod['purchases'][pcode]) == 0:
                        ginfod['purchases'].pop(pcode)
                        gdata.write(ginfo, ginfod)
                else:
                    inform('usedCode', 'error', client_id, plrdata['lang'])
        elif cat == 'tag':
            if len(msg_splits) == 1:
                inform('tagUsage', 'normal', client_id, plrdata['lang'])
                return True
            scommand = msg_splits[1]
            if scommand == 'rank':
                if not gdata.load(
                    ginfo, 'staff_list', spid, update=False
                ) and not any(
                    'vip@other' == o.split('␟')[0] for o in plrdata['items']
                ):
                    inform(
                        'rankTagNotOwned', 'error', client_id, plrdata['lang']
                    )
                    return True
                tagstat = plrdata['tag']
                if tagstat in (True, None):
                    plrdata['tag'] = False
                    inform(
                        'rankTagHidden', 'success', client_id, plrdata['lang']
                    )
                else:
                    plrdata['tag'] = True
                    inform(
                        'rankTagVisible', 'success', client_id, plrdata['lang']
                    )
            elif scommand == 'alliance':
                if not alliancedata:
                    inform('notInAlliance', 'error', client_id, plrdata['lang'])
                    return True
                tagstat = plrdata['alliancetag']
                if tagstat in (True, None):
                    plrdata['alliancetag'] = False
                    inform(
                        'allianceTagHidden',
                        'success',
                        client_id,
                        plrdata['lang'],
                    )
                else:
                    plrdata['alliancetag'] = True
                    inform(
                        'allianceTagVisible',
                        'success',
                        client_id,
                        plrdata['lang'],
                    )
            elif scommand == 'league':
                tagstat = plrdata['leaguetag']
                if tagstat in (True, None):
                    plrdata['leaguetag'] = False
                    inform(
                        'leagueTagHidden', 'success', client_id, plrdata['lang']
                    )
                else:
                    plrdata['leaguetag'] = True
                    inform(
                        'leagueTagVisible',
                        'success',
                        client_id,
                        plrdata['lang'],
                    )
            elif scommand == 'top':
                tagstat = plrdata['toptag']
                if tagstat in (True, None):
                    plrdata['toptag'] = False
                    inform(
                        'topTagHidden', 'success', client_id, plrdata['lang']
                    )
                else:
                    plrdata['toptag'] = True
                    inform(
                        'topTagVisible', 'success', client_id, plrdata['lang']
                    )
            elif scommand == 'custom':
                if len(msg_splits) == 3 and msg_splits[2] == 'delete':
                    plrdata['cstmtext'] = None
                    plrdata['cstmcolor'] = None
                    inform(
                        'customTagDeleted',
                        'success',
                        client_id,
                        plrdata['lang'],
                    )
                elif any(
                    o.split('␟')[0] in ('vip@other', 'tag@other')
                    for o in plrdata['items']
                ):
                    base = ''
                    r = None
                    g = None
                    b = None
                    for i, x in enumerate(msg_splits):
                        if i > 1:
                            if i == len(msg_splits) - 3:
                                r = int(x) / 255
                            elif i == len(msg_splits) - 2:
                                g = int(x) / 255
                            elif i == len(msg_splits) - 1:
                                b = int(x) / 255
                            else:
                                base += x if i == 2 else ' ' + x
                    while base[0] == '<':
                        base = base.removeprefix('<')
                    while base[-1] == '>':
                        base = base.removesuffix('>')
                    if (
                        base != ''
                        and r
                        and 0 < r <= 1
                        and g
                        and 0 < g <= 1
                        and b
                        and 0 < b <= 1
                    ):
                        plrdata['cstmtext'] = base
                        plrdata['cstmcolor'] = (r, g, b, 1)
                        inform(
                            'newCustomTag',
                            'success',
                            client_id,
                            plrdata['lang'],
                        )
                        if not any(
                            o.split('␟')[0] == 'vip@other'
                            for o in plrdata['items']
                        ):
                            for o in plrdata['items']:
                                if o.split('␟')[0] == 'tag@other':
                                    plrdata['items'].remove(o)
                                    break
                    else:
                        inform(
                            'genericError',
                            'error',
                            client_id,
                            plrdata['lang'],
                            ['tag'],
                        )
                else:
                    inform(
                        'customTagNotOwned',
                        'warning',
                        client_id,
                        plrdata['lang'],
                    )
                    inform(
                        'purchaseGuide',
                        'normal',
                        client_id,
                        plrdata['lang'],
                        ['other', 'tag'],
                    )
        elif cat == 'shop':
            sp = plrdata['spoints']
            if len(msg_splits) == 1:
                clist = gdata.load(gshop, update=False)
                ctxt = ''
                for i in clist:
                    ctxt += i + '\n'
                inform('shopMain', 'normal', client_id, plrdata['lang'], [ctxt])
                if sp > 0:
                    inform(
                        'amountOfSPoints',
                        'success',
                        client_id,
                        plrdata['lang'],
                        [str(sp)],
                    )
                else:
                    inform('0SPoints', 'warning', client_id, plrdata['lang'])
                return True
            scat = msg_splits[1]
            nlist = gdata.load(gshop, scat, update=False)
            if not nlist:
                inform(
                    'invalidShopCategory', 'error', client_id, plrdata['lang']
                )
                return True
            if len(msg_splits) == 2:
                txt = ''
                for i in nlist:
                    txt += i + ": " + str(nlist[i]['price']) + ' SPoints\n'
                txt = txt.removesuffix('\n')
                bs.broadcastmessage(
                    message=txt,
                    color=(1, 1, 1),
                    clients=[client_id],
                    transient=True,
                )
            elif len(msg_splits) == 3:
                item = msg_splits[2]
                if item not in nlist:
                    inform(
                        'invalidShopItem',
                        'error',
                        client_id,
                        plrdata['lang'],
                        [scat],
                    )
                    return True
                owned = [
                    o.split('␟')[0]
                    for o in plrdata['items'] + plrdata['equipped']
                ]
                if item + '@' + scat not in owned:
                    if sp < nlist[item]['price']:
                        inform(
                            'insufficientFunds',
                            'error',
                            client_id,
                            plrdata['lang'],
                            [str(nlist[item]['price'] - sp)],
                        )
                        inform(
                            'howToEarn', 'normal', client_id, plrdata['lang']
                        )
                    else:
                        plrdata['spoints'] = sp - nlist[item]['price']
                        plrdata['items'].append(item + '@' + scat)
                        inform(
                            'successfulPurchase',
                            'success',
                            client_id,
                            plrdata['lang'],
                            [item + '@' + scat],
                        )
                        if item + '@' + scat == 'tag@other':
                            inform(
                                'tagUsage', 'normal', client_id, plrdata['lang']
                            )
                        elif item + '@' + scat == 'wheel@other':
                            inform(
                                'wheelUsage',
                                'normal',
                                client_id,
                                plrdata['lang'],
                            )
                        elif scat == 'emote':
                            inform(
                                'howToUse',
                                'normal',
                                client_id,
                                plrdata['lang'],
                                ['/emote ' + item],
                            )
                        elif scat == 'powerup':
                            inform(
                                'howToUse',
                                'normal',
                                client_id,
                                plrdata['lang'],
                                ['/powerup ' + item],
                            )
                        else:
                            inform(
                                'howToUse',
                                'normal',
                                client_id,
                                plrdata['lang'],
                                ['/equip ' + scat + ' ' + item],
                            )
                else:
                    inform(
                        'alreadyOwned',
                        'warning',
                        client_id,
                        plrdata['lang'],
                        [item + '@' + scat],
                    )
        elif cat == 'equip':
            if len(msg_splits) == 1:
                inform('equipUsage', 'normal', client_id, plrdata['lang'])
                return True
            scat = msg_splits[1]
            item = msg_splits[2]
            te = None
            for o in plrdata['items'] + plrdata['equipped']:
                if o.split('␟')[0] == item + '@' + scat:
                    te = o
                    break
            if not te or scat in ('other', 'emote', 'powerup'):
                inform(
                    'unknownItemStatusE',
                    'warning',
                    client_id,
                    plrdata['lang'],
                    [item + '@' + scat],
                )
                return True
            for i in plrdata['equipped']:
                if te != i and scat == i.split('␟')[0].split('@')[1]:
                    plrdata['items'].append(i)
                    plrdata['equipped'].remove(i)
                    inform(
                        'unequipped', 'success', client_id, plrdata['lang'], [i]
                    )
            if te in plrdata['items']:
                plrdata['items'].remove(te)
                plrdata['equipped'].append(te)
                inform('equipped', 'success', client_id, plrdata['lang'], [te])
            else:
                plrdata['items'].append(te)
                plrdata['equipped'].remove(te)
                inform(
                    'unequipped', 'success', client_id, plrdata['lang'], [te]
                )
            equipped = True
        elif cat == 'emote':
            if len(msg_splits) == 1:
                inform('emoteUsage', 'normal', client_id, plrdata['lang'])
                return True
            emote = msg_splits[1]
            if any(
                o.split('␟')[0] == emote + '@emote' for o in plrdata['items']
            ):
                pemote = emote
            else:
                inform(
                    'unknownItemStatus',
                    'warning',
                    client_id,
                    plrdata['lang'],
                    [emote + '@emote'],
                )
        elif cat == 'lang':
            if len(msg_splits) == 1:
                inform('langUsage', 'normal', client_id, 'Mixed')
                return True
            lang = msg_splits[1]
            if lang == 'eng':
                plrdata['lang'] = 'English'
            elif lang == 'fa':
                plrdata['lang'] = 'Farsi'
            else:
                inform('invalidLang', 'warning', client_id, plrdata['lang'])
                return True
            inform('langUpdated', 'success', client_id, plrdata['lang'])
        elif cat == 'help':
            inform('helpNormal', 'normal', client_id, plrdata['lang'])
        elif cat == 'wheel':
            if len(msg_splits) == 1:
                inform('wheelUsage', 'normal', client_id, plrdata['lang'])
                return True
            if not babase.app.classic.server._config.allow_chaotic_commands:
                inform('chaosDisabled', 'normal', client_id, plrdata['lang'])
                return True
            if not any(
                o.split('␟')[0] == 'wheel@other' for o in plrdata['items']
            ):
                inform('wheelNotOwned', 'normal', client_id, plrdata['lang'])
                inform(
                    'purchaseGuide',
                    'normal',
                    client_id,
                    plrdata['lang'],
                    ['other', 'wheel'],
                )
                return True
            action = msg_splits[1]
            if action == 'luck':
                if plrdata['luck'] < 3:
                    if plrdata['spoints'] >= 5:
                        plrdata['spoints'] -= 5
                        plrdata['luck'] += 1
                        inform(
                            'wheelLuckIncrease',
                            'success',
                            client_id,
                            plrdata['lang'],
                            [str(3 - plrdata['luck'])],
                        )
                    else:
                        inform(
                            'insufficientFunds',
                            'error',
                            client_id,
                            plrdata['lang'],
                            [str(5 - plrdata['spoints'])],
                        )
                        inform(
                            'howToEarn', 'normal', client_id, plrdata['lang']
                        )
                else:
                    inform('maxWheelLuck', 'error', client_id, plrdata['lang'])
            elif action == 'chaos':
                if plrdata['chaos'] < 3:
                    if plrdata['spoints'] >= 5:
                        plrdata['spoints'] -= 5
                        plrdata['chaos'] += 1
                        inform(
                            'wheelChaosIncrease',
                            'success',
                            client_id,
                            plrdata['lang'],
                            [str(3 - plrdata['chaos'])],
                        )
                    else:
                        inform(
                            'insufficientFunds',
                            'error',
                            client_id,
                            plrdata['lang'],
                            [str(5 - plrdata['spoints'])],
                        )
                        inform(
                            'howToEarn', 'normal', client_id, plrdata['lang']
                        )
                else:
                    inform('maxWheelChaos', 'error', client_id, plrdata['lang'])
            elif action == 'charge':
                if plrdata['charge'] < 3:
                    if plrdata['spoints'] >= 5:
                        plrdata['spoints'] -= 5
                        plrdata['charge'] += 1
                        inform(
                            'wheelCharged',
                            'success',
                            client_id,
                            plrdata['lang'],
                            [str(3 - plrdata['charge'])],
                        )
                    else:
                        inform(
                            'insufficientFunds',
                            'error',
                            client_id,
                            plrdata['lang'],
                            [str(5 - plrdata['spoints'])],
                        )
                        inform(
                            'howToEarn', 'normal', client_id, plrdata['lang']
                        )
                else:
                    inform(
                        'maxWheelCharge', 'error', client_id, plrdata['lang']
                    )
            elif action == 'spin':
                if len(plrl) == 0 or not any(
                    plr.actor and plr.actor.node for plr in plrl
                ):
                    inform(
                        'needsInGamePlr', 'error', client_id, plrdata['lang']
                    )
                    return True
                ge = gdata.load(
                    ginfo, 'wgc' + str(plrdata['chaos']), update=False
                )
                be = gdata.load(
                    ginfo, 'wbc' + str(plrdata['chaos']), update=False
                )
                match plrdata['luck']:
                    case 0:
                        e = ge + be + be
                    case 1:
                        e = ge + be
                    case 2:
                        e = ge + ge + be
                    case _:
                        e = ge
                for _ in range(plrdata['charge']):
                    plrlist = []
                    while plrlist is not None and len(plrlist) == 0:
                        tbr = random.choice(e)
                        event = tbr.split(' ')
                        match event[0]:
                            case 'everyone':
                                plrlist = activity.players
                            case 'random':
                                plrlist = [random.choice(activity.players)]
                            case 'self':
                                plrlist = plrl
                            case 'others':
                                plrlist = [
                                    plr
                                    for plr in activity.players
                                    if plr not in plrl
                                ]
                            case 'severyone':
                                ap = []
                                for plr in activity.players:
                                    pid = (
                                        plr.sessionplayer.get_v1_account_id()
                                        or 'anon'
                                    )
                                    if pid not in ap:
                                        plrlist.append(plr)
                                        ap.append(pid)
                            case 'sself':
                                plrlist = [plrl[0]]
                            case 'activity':
                                plrlist = None
                            case _:
                                raise ValueError('Invalid event target')
                    gdata.write(plrdatapath, plrdata)
                    handle_event(context, activity, event, plrlist)
                    plrdata = gdata.load(plrdatapath)
                    sdpd(plrdata)
                    while tbr in e:
                        e.remove(tbr)
                    inform(
                        'somethingHappened',
                        'success',
                        client_id,
                        plrdata['lang'],
                    )
                plrdata['luck'] = 0
                plrdata['chaos'] = 0
                plrdata['charge'] = 1
                for o in plrdata['items']:
                    if o.split('␟')[0] == 'wheel@other':
                        plrdata['items'].remove(o)
                        break
        elif cat == 'alliance':
            if len(msg_splits) == 1:
                inform('allianceUsage', 'normal', client_id, plrdata['lang'])
                return True
            nlistpath = gdata.getpath('galliancenames')
            nlist = gdata.load(nlistpath) or []
            scommand = msg_splits[1]
            if scommand == 'create':
                if alliancedata:
                    inform(
                        'alreadyInAlliance', 'error', client_id, plrdata['lang']
                    )
                    return True
                if plrdata['spoints'] < 1000:
                    inform(
                        'insufficientFunds',
                        'error',
                        client_id,
                        plrdata['lang'],
                        [str(1000 - plrdata['spoints'])],
                    )
                    inform('howToEarn', 'normal', client_id, plrdata['lang'])
                    return True
                name = msg_splits[2]
                if not name.isalnum() or len(msg_splits) > 3:
                    inform('isNotAlnum', 'warning', client_id, plrdata['lang'])
                    return True
                if len(name) >= 20:
                    inform(
                        'tooLong', 'warning', client_id, plrdata['lang'], ['20']
                    )
                    return True
                if name.lower() in nlist:
                    inform('nameTaken', 'warning', client_id, plrdata['lang'])
                    return True
                allianceid = (
                    str(random.randint(0, 9))
                    + str(random.randint(0, 9))
                    + str(random.randint(0, 9))
                    + str(random.randint(0, 9))
                    + str(random.randint(0, 9))
                )
                while gdata.load(gdata.getpath('galliances/' + allianceid)):
                    allianceid = (
                        str(random.randint(0, 9))
                        + str(random.randint(0, 9))
                        + str(random.randint(0, 9))
                        + str(random.randint(0, 9))
                        + str(random.randint(0, 9))
                    )
                alliancedatapath = gdata.getpath('galliances/' + allianceid)
                alliancedata = {'name': name, 'members': {spid: 'owner'}}
                nlist.append(name.lower())
                plrdata['allianceidref'] = allianceid
                plrdata['spoints'] -= 1000
                inform(
                    'allianceCreateSuccess',
                    'success',
                    client_id,
                    plrdata['lang'],
                )
            elif scommand == 'invite':
                if not alliancedata:
                    inform('notInAlliance', 'error', client_id, plrdata['lang'])
                    return True
                if alliancedata['members'][spid] == 'member':
                    inform(
                        'insufficientAllianceRank',
                        'error',
                        client_id,
                        plrdata['lang'],
                    )
                    return True
                if alliancedata['public']:
                    inform(
                        'publicAllianceCantGenerateInvite',
                        'warning',
                        client_id,
                        plrdata['lang'],
                    )
                    return True
                if alliancedata['invref']:
                    invid = alliancedata['invref']
                    uses = gdata.load(
                        gdata.getpath('gallianceinvites/' + invid), 'uses'
                    )
                else:
                    invid = (
                        str(random.randint(0, 9))
                        + str(random.randint(0, 9))
                        + str(random.randint(0, 9))
                        + str(random.randint(0, 9))
                        + str(random.randint(0, 9))
                    )
                    while not invid or gdata.load(
                        gdata.getpath('gallianceinvites/' + invid)
                    ):
                        invid = (
                            str(random.randint(0, 9))
                            + str(random.randint(0, 9))
                            + str(random.randint(0, 9))
                            + str(random.randint(0, 9))
                            + str(random.randint(0, 9))
                        )
                    uses = (
                        max(1, int(msg_splits[2]))
                        if len(msg_splits) == 3
                        else 1
                    )
                    gdata.write(
                        gdata.getpath('gallianceinvites/' + invid),
                        {'allianceid': plrdata['allianceidref'], 'uses': uses},
                    )
                    alliancedata['invref'] = invid
                inform(
                    'allianceInviteSuccess',
                    'success',
                    client_id,
                    plrdata['lang'],
                    [invid, str(uses)],
                )
            elif scommand == 'join':
                if alliancedata:
                    inform(
                        'alreadyInAlliance', 'error', client_id, plrdata['lang']
                    )
                    return True
                invid = msg_splits[2].lower()
                invpath = gdata.getpath('gallianceinvites/' + invid)
                inv = gdata.load(invpath)
                if not inv:
                    inform(
                        'invalidAllianceInvite',
                        'warning',
                        client_id,
                        plrdata['lang'],
                    )
                    return True
                alliancedatapath = gdata.getpath(
                    'galliances/' + inv['allianceid']
                )
                alliancedata = gdata.load(alliancedatapath)
                # FIXME: we dont want to limit how many players can join an
                #  alliance, but we should somehow punish servers that pass a
                #  certain amount of members
                alliancedata['members'][spid] = 'member'
                inv.setdefault('uses', None)
                if inv['uses']:
                    inv['uses'] -= 1
                    if inv['uses'] == 0:
                        alliancedata['invref'] = None
                        os.remove(invpath)
                    else:
                        gdata.write(invpath, inv)
                plrdata['allianceidref'] = inv['allianceid']
                inform(
                    'allianceJoinSuccess',
                    'success',
                    client_id,
                    plrdata['lang'],
                    [alliancedata['name']],
                )
            elif scommand == 'leave':
                if not alliancedata:
                    inform('notInAlliance', 'error', client_id, plrdata['lang'])
                    return True
                ownercount = 0
                for i in alliancedata['members']:
                    if alliancedata['members'][i] == 'owner':
                        ownercount += 1
                if alliancedata['members'][spid] == 'owner' and ownercount == 1:
                    inform(
                        'allianceOwnerCantLeave',
                        'error',
                        client_id,
                        plrdata['lang'],
                    )
                    return True
                alliancedata['members'].pop(spid)
                plrdata['allianceidref'] = None
                inform(
                    'allianceLeaveSuccessful',
                    'success',
                    client_id,
                    plrdata['lang'],
                )
            elif scommand == 'destroy':
                if not alliancedata:
                    inform('notInAlliance', 'error', client_id, plrdata['lang'])
                    return True
                if not alliancedata['members'][spid] == 'owner':
                    inform(
                        'insufficientAllianceRank',
                        'error',
                        client_id,
                        plrdata['lang'],
                    )
                    return True
                nlist.remove(alliancedata['name'].lower())
                if alliancedata['invref']:
                    os.remove(
                        gdata.getpath(
                            'gallianceinvites/' + alliancedata['invref']
                        )
                    )
                os.remove(alliancedatapath)
                for i in alliancedata['members']:
                    tempplrdatapath = gdata.getpath('gstats/' + i)
                    tempplrdata = gdata.load(tempplrdatapath)
                    tempplrdata['allianceidref'] = None
                    gdata.write(tempplrdatapath, tempplrdata)
                plrdata['allianceidref'] = None
                alliancedatapath = None
                alliancedata = None
                inform(
                    'allianceDeletionSuccess',
                    'success',
                    client_id,
                    plrdata['lang'],
                )
            elif scommand == 'plrlist':
                if not alliancedata:
                    inform('notInAlliance', 'error', client_id, plrdata['lang'])
                    return True
                txt = ''
                for i, x in enumerate(alliancedata['members']):
                    un = gdata.load(gdata.getpath('gstats/' + x), 'un')
                    txt += (
                        str(i).upper()
                        + ' - '
                        + alliancedata['members'][x]
                        + ' - '
                        + (un or x)
                        + '\n'
                    )
                txt = txt.removesuffix('\n')
                inform(
                    'alliancePlayerList',
                    'success',
                    client_id,
                    plrdata['lang'],
                    [txt],
                )
            elif scommand == 'kick':
                if not alliancedata:
                    inform('notInAlliance', 'error', client_id, plrdata['lang'])
                    return True
                if rankint(alliancedata['members'][spid]) < 2:
                    inform(
                        'insufficientAllianceRank',
                        'error',
                        client_id,
                        plrdata['lang'],
                    )
                    return True
                pid = None
                try:
                    for i, x in enumerate(alliancedata['members']):
                        if i == int(msg_splits[2]):
                            pid = x
                            break
                except ValueError:
                    pid = msg_splits[2]
                if rankint(alliancedata['members'][spid]) <= rankint(
                    alliancedata['members'][pid]
                ):
                    inform(
                        'cantKickHigherRanks',
                        'warning',
                        client_id,
                        plrdata['lang'],
                    )
                    return True
                alliancedata['members'].pop(pid)
                tempplrdatapath = gdata.getpath('gstats/' + pid)
                tempplrdata = gdata.load(tempplrdatapath)
                tempplrdata['allianceidref'] = None
                gdata.write(tempplrdatapath, tempplrdata)
                inform(
                    'allianceKickSuccessful',
                    'success',
                    client_id,
                    plrdata['lang'],
                )
            elif scommand == 'promote':
                if not alliancedata:
                    inform('notInAlliance', 'error', client_id, plrdata['lang'])
                    return True
                if alliancedata['members'][spid] == 'member':
                    inform(
                        'insufficientAllianceRank',
                        'error',
                        client_id,
                        plrdata['lang'],
                    )
                    return True
                pid = None
                try:
                    for i, x in enumerate(alliancedata['members']):
                        if i == int(msg_splits[2]):
                            pid = x
                            break
                except ValueError:
                    pid = msg_splits[2]
                if rankint(alliancedata['members'][spid]) <= rankint(
                    alliancedata['members'][pid]
                ):
                    inform(
                        'cantPromoteHigherThanSelf',
                        'warning',
                        client_id,
                        plrdata['lang'],
                    )
                    return True
                alliancedata['members'][pid] = rankint(
                    rankint(alliancedata['members'][pid]) + 1
                )
                inform(
                    'alliancePromoteSuccess',
                    'success',
                    client_id,
                    plrdata['lang'],
                )
            elif scommand == 'demote':
                if not alliancedata:
                    inform('notInAlliance', 'error', client_id, plrdata['lang'])
                    return True
                if alliancedata['members'][spid] == 'member':
                    inform(
                        'insufficientAllianceRank',
                        'error',
                        client_id,
                        plrdata['lang'],
                    )
                    return True
                pid = None
                try:
                    for i, x in enumerate(alliancedata['members']):
                        if i == int(msg_splits[2]):
                            pid = x
                            break
                except ValueError:
                    pid = msg_splits[2]
                if (
                    rankint(alliancedata['members'][spid])
                    <= rankint(alliancedata['members'][pid])
                    and spid != pid
                ):
                    inform(
                        'cantDemoteHigherThanSelf',
                        'warning',
                        client_id,
                        plrdata['lang'],
                    )
                    return True
                ownercount = 0
                for i in alliancedata['members']:
                    if alliancedata['members'][i] == 'owner':
                        ownercount += 1
                if alliancedata['members'][pid] == 'owner' and ownercount == 1:
                    inform(
                        'allianceOwnerCantBeDemoted',
                        'warning',
                        client_id,
                        plrdata['lang'],
                    )
                    return True
                if alliancedata['members'][pid] == 'member':
                    inform(
                        'alreadyLowestRank',
                        'warning',
                        client_id,
                        plrdata['lang'],
                    )
                    return True
                alliancedata['members'][pid] = rankint(
                    rankint(alliancedata['members'][pid]) - 1
                )
                inform(
                    'allianceDemoteSuccess',
                    'success',
                    client_id,
                    plrdata['lang'],
                )
            elif scommand == 'public':
                if not alliancedata:
                    inform('notInAlliance', 'error', client_id, plrdata['lang'])
                    return True
                if alliancedata['members'][spid] != 'owner':
                    inform(
                        'insufficientAllianceRank',
                        'error',
                        client_id,
                        plrdata['lang'],
                    )
                    return True
                if alliancedata['public']:
                    inform(
                        'allianceAlreadyPublic',
                        'warning',
                        client_id,
                        plrdata['lang'],
                    )
                    return True
                alliancedata['public'] = True
                lname = alliancedata['name'].lower()
                gdata.write(
                    gdata.getpath('gallianceinvites/' + lname),
                    {'allianceid': plrdata['allianceidref']},
                )
                inform(
                    'alliancePublicSuccess',
                    'success',
                    client_id,
                    plrdata['lang'],
                )
            elif scommand == 'private':
                if not alliancedata:
                    inform('notInAlliance', 'error', client_id, plrdata['lang'])
                    return True
                if alliancedata['members'][spid] != 'owner':
                    inform(
                        'insufficientAllianceRank',
                        'error',
                        client_id,
                        plrdata['lang'],
                    )
                    return True
                if not alliancedata['public']:
                    inform(
                        'allianceAlreadyPrivate',
                        'warning',
                        client_id,
                        plrdata['lang'],
                    )
                    return True
                alliancedata['public'] = False
                lname = alliancedata['name'].lower()
                os.remove(gdata.getpath('gallianceinvites/' + lname))
                inform(
                    'alliancePrivateSuccess',
                    'success',
                    client_id,
                    plrdata['lang'],
                )
            gdata.write(nlistpath, nlist)
        elif cat == 'powerup':
            if len(msg_splits) == 1:
                inform('powerupUsage', 'normal', client_id, plrdata['lang'])
                return True
            if not babase.app.classic.server._config.allow_chaotic_commands:
                inform('chaosDisabled', 'normal', client_id, plrdata['lang'])
                return True
            pu = msg_splits[1]
            te = None
            for o in plrdata['items']:
                if o.split('␟')[0] == pu + '@powerup':
                    te = o
                    break
            if not te:
                gdata.write(plrdatapath, plrdata)
                server_command('/shop powerup ' + pu, client_id)
                plrdata = gdata.load(plrdatapath)
                sdpd(plrdata)
            for o in plrdata['items']:
                if o.split('␟')[0] == pu + '@powerup':
                    te = o
                    break
            if not te:
                inform(
                    'unknownItemStatus',
                    'warning',
                    client_id,
                    plrdata['lang'],
                    [pu + '@powerup'],
                )
                return True
            if len(plrl) == 0 or not any(
                plr.actor and plr.actor.node for plr in plrl
            ):
                inform('needsInGamePlr', 'error', client_id, plrdata['lang'])
                return True
            handle_event(
                context, activity, ['everyone', 'powerup', pu], activity.players
            )
            plrdata['items'].remove(te)
            inform('somethingHappened', 'success', client_id, plrdata['lang'])
        elif cat == 'membership':
            te = None
            for o in plrdata['items']:
                if o.split('␟')[0] == 'vip@other':
                    te = o
                    break
            if te:
                te = te.split('␟')
                if len(te) == 1:
                    inform(
                        'permanentMembership',
                        'success',
                        client_id,
                        plrdata['lang'],
                    )
                else:
                    end = float(te[1]) - time.time()
                    endstr = ' seconds'
                    if end >= 60:
                        end /= 60
                        endstr = ' minutes'
                        if end >= 60:
                            end /= 60
                            endstr = ' hours'
                            if end >= 24:
                                end /= 24
                                endstr = ' days'
                    inform(
                        'membershipEndsIn',
                        'success',
                        client_id,
                        plrdata['lang'],
                        [str(round(end)) + endstr],
                    )
            else:
                inform('noMembership', 'warning', client_id, plrdata['lang'])
        else:
            inform('invalidCommand', 'error', client_id, plrdata['lang'])
            return True
        gdata.write(plrdatapath, plrdata)
        if alliancedatapath and alliancedata:
            gdata.write(alliancedatapath, alliancedata)
        with context:
            for plr in plrl:
                if plr.actor:
                    plr.actor.give_ranks()
                    plr.actor.give_alliances()
                    plr.actor.give_tops()
                    plr.actor.give_tops()
                    plr.actor.give_cstms()
                    plr.actor.equip()
                    if pemote:
                        plr.actor.emote(pemote)
                elif pemote:
                    inform(
                        'needsInGamePlr', 'error', client_id, plrdata['lang']
                    )
    except (IndexError, ValueError, KeyError) as error:
        try:
            inform('genericError', 'error', client_id, plrdata['lang'], [cat])
            print(error)
        except KeyError:
            inform('genericError', 'error', client_id, v=[cat])
    return True


# FIXME: this should be moved from hooks
def handle_event(
    context: bascenev1.ContextRef,
    activity: bascenev1.GameActivity,
    event: list,
    plrlist: list | None,
) -> None:
    import bascenev1 as bs
    from bascenev1lib.actor.bomb import Blast
    from bascenev1lib.actor.anomalies import Portal, BlackHole

    with context:
        if plrlist:
            for plr in plrlist:
                match event[1]:
                    case 'powerup':
                        if plr.actor and plr.actor.node:
                            if event[2] == 'deflect':
                                if plr.actor.shield:
                                    plr.actor.shield.delete()
                                    plr.actor.shield = None
                                    plr.actor.shield_hitpoints = 0
                                    plr.actor.shield_decay_timer = None
                                if plr.actor.reflect:
                                    plr.actor.reflect.delete()
                                    plr.actor.reflect = None
                                    plr.actor.reflect_hitpoints = 0
                                    plr.actor.reflect_decay_timer = None
                                plr.actor.equip_deflects(20)
                            else:
                                plr.actor.handlemessage(
                                    bs.PowerupMessage(event[2])
                                )
                    case 'die':
                        if plr.actor and plr.actor.node:
                            plr.actor.handlemessage(bs.DieMessage())
                    case 'portal_trap':
                        if plr.actor and plr.actor.node:
                            pos = plr.actor.node.position
                            p0 = Portal(pos).autoretain()
                            p1 = Portal(
                                (pos[0], pos[1] + 1, pos[2])
                            ).autoretain()
                            p0.pair = p1
                            if len(event) > 2:
                                bs.timer(
                                    int(event[2]),
                                    bs.WeakCall(
                                        p0.handlemessage, bs.DieMessage()
                                    ),
                                )
                                bs.timer(
                                    int(event[2]),
                                    bs.WeakCall(
                                        p1.handlemessage, bs.DieMessage()
                                    ),
                                )
                    case 'explode':
                        if plr.actor and plr.actor.node:
                            Blast(
                                plr.actor.node.position,
                                blast_type=event[2],
                                hit_subtype=event[2],
                            )
                    case 'knockout':
                        if plr.actor and plr.actor.node:
                            plr.actor.node.handlemessage(
                                'knockout', int(event[2])
                            )
                    case 'dev':
                        if plr.actor and plr.actor.node:
                            bh = BlackHole(
                                plr.actor.node.position, radius=int(event[2])
                            ).autoretain()
                            if len(event) > 3:
                                bs.timer(
                                    int(event[3]),
                                    bs.WeakCall(
                                        bh.handlemessage, bs.DieMessage()
                                    ),
                                )
                    case 'disable':
                        if plr.actor and plr.actor.node:
                            plr.actor.connect_controls_to_player(
                                True, False, False, False
                            )
                    case "reward":
                        plrdatapath = gdata.getpath(
                            'gstats/'
                            + (plr._sessionplayer.get_v1_account_id() or 'anon')
                        )
                        plrdata = gdata.load(plrdatapath) or {}
                        plrdata.setdefault('spoints', 0)
                        plrdata.setdefault('items', [])
                        plrdata.setdefault('equipped', [])
                        try:
                            plrdata['spoints'] += int(event[2])
                        except ValueError:
                            rs = event[2].split('␟')
                            if (
                                rs[0]
                                not in plrdata['items'] + plrdata['equipped']
                            ):
                                r = rs[0]
                                if len(rs) != 1:
                                    r += '␟' + str(time.time() + float(rs[1]))
                                plrdata['items'].append(r)
                        gdata.write(plrdatapath, plrdata)
                    case _:
                        raise ValueError('Invalid event type')
        else:
            bnds = list(
                activity.map.get_def_bound_box('area_of_interest_bounds')
            )
            match event[2]:
                case 'center':
                    pos = (
                        (bnds[0] + bnds[3]) / 2,
                        (bnds[1] + bnds[4]) / 2,
                        (bnds[2] + bnds[5]) / 2,
                    )
                case 'random':
                    pos = (
                        random.uniform(bnds[0], bnds[3]),
                        random.uniform(bnds[1], bnds[4]),
                        random.uniform(bnds[2], bnds[5]),
                    )
                case 'ranpowuppos':
                    pos = random.choice(activity.map.powerup_spawn_points)
                case _:
                    pos = (0, 0, 0)
            match event[1]:
                case 'dev':
                    bh = BlackHole(pos, radius=int(event[3])).autoretain()
                    if len(event) > 4:
                        bs.timer(
                            int(event[4]),
                            bs.WeakCall(bh.handlemessage, bs.DieMessage()),
                        )


def sdpd(plrdata: dict) -> None:
    plrdata.setdefault('upcodes', [])
    plrdata.setdefault('spoints', 0)
    plrdata.setdefault('items', [])
    plrdata.setdefault('equipped', [])
    plrdata.setdefault('tag', None)
    plrdata.setdefault('lang', None)
    plrdata.setdefault('chaos', 0)
    plrdata.setdefault('luck', 0)
    plrdata.setdefault('charge', 1)
    plrdata.setdefault('allianceidref', None)
    plrdata.setdefault('alliancetag', None)
    plrdata.setdefault('toptag', None)
    plrdata.setdefault('leaguetag', None)
