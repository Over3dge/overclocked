# Released under AGPL-3.0-or-later. See LICENSE for details.
#
"""Some utilities"""
from era import gdata
import bascenev1 as bs

from typing import Sequence


def inform(tid: str, ttype: str | Sequence[float], client_id: int,
           lang: str | None = None, v: list | None = None) -> None:
    glang = gdata.getpath('glang')
    if lang is None:
        inform('selectLang', 'error', client_id, 'Mixed')
    plang = lang or 'Mixed'
    basetxt = ''
    if plang == 'Mixed':
        if gdata.load(glang, tid):
            for i in gdata.load(glang, tid).values():
                basetxt += i + '\n'
            basetxt = basetxt.removesuffix('\n')
        basetxt = None if basetxt == '' else basetxt
    else:
        basetxt = gdata.load(glang, tid, plang)
    pv = v or []
    match ttype:
        case 'success':
            color = (0, 1, 0)
        case 'warning':
            color = (1, 1, 0)
        case 'error':
            color = (1, 0, 0)
        case 'normal':
            color = (1, 1, 1)
        case (int() | float(), int() | float(), int() | float()):
            color = ttype
        case _:
            raise ValueError('Not a valid ttype for inform')
    if not basetxt:
        basetxt = str([tid] + pv)
        print('missing glang entry, using fallback: ' + basetxt)
    for i, x in enumerate(pv):
        basetxt = basetxt.replace('${' + str(i) + '}', x)
    basetxt = basetxt.replace('␟', '#')
    bs.broadcastmessage(message=basetxt, color=color, clients=[client_id],
                        transient=True)


def rankint(rank: str | int) -> int | str:
    """takes a rank/number and returns a number/rank representing it"""
    match rank:
        case 3:
            return 'owner'
        case 2:
            return 'co-owner'
        case 1:
            return 'recruiter'
        case 0:
            return 'member'
        case 'owner':
            return 3
        case 'co-owner':
            return 2
        case 'recruiter':
            return 1
        case 'member':
            return 0
        case _:
            raise ValueError(rank + ' is not a valid rank')


def chasattr(obj: object, attr: str):
    try:
        getattr(obj, attr)
        return True
    except (AttributeError, RuntimeError):
        return False
