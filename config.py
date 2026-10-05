import os
import json
from wake_on_lan import formatMagicPacket

WAKE_TARGETS_PATH = os.environ.get("WAKE_TARGETS_FILE", "wake_targets.json")


def load_wake_targets(path=WAKE_TARGETS_PATH):
    with open(path) as f:
        raw = json.load(f)

    targets = {}
    for key, entry in raw.items():
        mac = entry.get("mac", "")
        label = entry.get("label", key)
        try:
            formatMagicPacket(mac)  # validate now, fail loud at startup rather than at request time
        except ValueError:
            raise ValueError(f"Invalid MAC address for target '{key}': {mac!r}")
        targets[key] = {"label": label, "mac": mac}
    return targets


WAKE_TARGETS = load_wake_targets()