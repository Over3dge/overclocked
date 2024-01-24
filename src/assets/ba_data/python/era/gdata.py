# Released under AGPL-3.0-or-later. See LICENSE for details.
#
"""Module for saving and loading shared data between different local servers"""
import os
import time
import json
from typing import Any
from pathlib import Path

import babase


def getpath(stattype: str) -> Path:
    base = Path(os.path.abspath(os.getcwd())).parent.parent / 'bso_server_data'
    stattype = stattype.split('/')
    if stattype[0].startswith('s'):
        stattype[0] = stattype[0].removeprefix('s')
        base = base / 'superdata' / babase.app.classic.server._config.super_dir
    for stat in stattype[:-1]:
        base = base / stat
    return base / (stattype[-1] + '.json')


def write(gorl: Path, data: Any) -> None:
    if not gorl.parent.exists():
        os.makedirs(gorl.parent)
    with open(gorl, 'w') as f:
        f.write(json.dumps(data))
        # truncate just in case
        f.truncate()


def load(gorl: Path, *args, update: bool = True) -> Any:
    if os.path.exists(gorl):
        with open(gorl) as f:
            stats = json.loads(f.read())
    else:
        return None
    if update:
        stats = _update(stats)
        write(gorl, stats)
    for x in args:
        try:
            stats = stats[x]
        except KeyError:
            return None
    return stats


def _update(a: Any) -> Any:
    if isinstance(a, dict):
        x = _update_dict(a)
    elif isinstance(a, list):
        x = _update_list(a)
    elif isinstance(a, str):
        x = _update_str(a)
    else:
        x = a
    return x


def _update_dict(d: dict) -> dict:
    x = {}
    for k, v in d.items():
        if isinstance(v, dict):
            v = _update_dict(v)
        elif isinstance(v, list):
            v = _update_list(v)
        elif isinstance(v, str):
            v = _update_str(v)
        if v is not None:
            x[k] = v
    return x


def _update_list(li: list) -> list:
    x = []
    for e in li:
        if isinstance(e, list):
            e = _update_list(e)
        elif isinstance(e, dict):
            e = _update_dict(e)
        elif isinstance(e, str):
            e = _update_str(e)
        if e is not None:
            x.append(e)
    return x


def _update_str(s: str) -> str | None:
    ss = s.split('␟')
    if len(ss) != 1:
        s = None if time.time() > float(ss[1]) else s
    return s
