from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.import_service.csv_import import ImportedCycle
from app.services.simulation.simulator import FasteningSettings

GroupKey = tuple[float, float, float, float]


@dataclass(frozen=True)
class SettingsGroup:
    key: GroupKey
    settings: FasteningSettings
    cycle_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": list(self.key),
            "settings": self.settings.to_dict(),
            "cycle_ids": self.cycle_ids,
            "cycle_count": len(self.cycle_ids),
        }


def _group_key(settings: FasteningSettings) -> GroupKey:
    return (
        round(float(settings.target_speed), 4),
        round(float(settings.target_torque), 4),
        round(float(settings.clamp_rising_time), 4),
        round(float(settings.torque_hold_time), 4),
    )


def group_cycles_by_settings(cycles: list[ImportedCycle]) -> list[SettingsGroup]:
    ordered_keys: list[GroupKey] = []
    members: dict[GroupKey, list[str]] = {}
    settings_by_key: dict[GroupKey, FasteningSettings] = {}
    for cycle in cycles:
        key = _group_key(cycle.settings)
        if key not in members:
            ordered_keys.append(key)
            members[key] = []
            settings_by_key[key] = cycle.settings
        members[key].append(cycle.cycle_id)
    return [
        SettingsGroup(key=key, settings=settings_by_key[key], cycle_ids=members[key])
        for key in ordered_keys
    ]
