#!/usr/bin/python3

import json
import os
import shutil
from pathlib import Path


HOME = Path.home()

DATA = (
    HOME
    / ".local/share/g834jz-rgb-manager"
)

DEFAULT = (
    DATA
    / "default.json"
)

STATE = (
    DATA
    / "state.json"
)

PROFILES = (
    DATA
    / "profiles"
)

ACTIVE = (
    HOME
    / ".config/g834jz-rgb-base-packets.json"
)


def validate(path):

    try:
        packets = json.loads(
            path.read_text()
        )
    except Exception:
        return False

    if (
        not isinstance(packets, list)
        or len(packets) != 11
    ):
        return False

    for row in packets:

        if (
            not isinstance(row, list)
            or len(row) != 64
        ):
            return False

        for value in row:

            if (
                not isinstance(value, int)
                or value < 0
                or value > 255
            ):
                return False

    return True


if not DEFAULT.is_file():
    raise SystemExit(0)


config = json.loads(
    DEFAULT.read_text()
)

profile_id = config.get(
    "id"
)

if (
    not profile_id
    or "/" in profile_id
    or "\\" in profile_id
    or ".." in profile_id
):
    raise SystemExit(
        "Nieprawidłowy profil domyślny."
    )


directory = (
    PROFILES
    / profile_id
)

packets = (
    directory
    / "g834jz-rgb-base-packets.json"
)

metadata = (
    directory
    / "profile.json"
)


if not validate(packets):
    raise SystemExit(
        "Profil domyślny ma nieprawidłową bazę RGB."
    )


ACTIVE.parent.mkdir(
    parents=True,
    exist_ok=True
)


temporary = (
    ACTIVE.parent
    / ".g834jz-rgb-base-packets.default.tmp"
)

shutil.copy2(
    packets,
    temporary
)

if not validate(temporary):
    temporary.unlink(
        missing_ok=True
    )

    raise SystemExit(
        "Walidacja kopii profilu nie powiodła się."
    )


os.replace(
    temporary,
    ACTIVE
)


name = profile_id

try:
    info = json.loads(
        metadata.read_text()
    )

    name = info.get(
        "name",
        profile_id
    )

except Exception:
    pass


state_tmp = (
    STATE.with_suffix(".tmp")
)

state_tmp.write_text(
    json.dumps(
        {
            "id": profile_id,
            "name": name,
        },
        ensure_ascii=False,
        indent=4,
    )
)

os.replace(
    state_tmp,
    STATE
)
