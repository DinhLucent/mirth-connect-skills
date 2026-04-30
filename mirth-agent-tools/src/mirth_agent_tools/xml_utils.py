from __future__ import annotations

import difflib
import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelSummary:
    id: str | None
    name: str | None


def parse_channel_summary(channel_xml: str) -> ChannelSummary:
    root = ET.fromstring(channel_xml)
    return ChannelSummary(
        id=_find_first_text(root, ("id",)),
        name=_find_first_text(root, ("name",)),
    )


def parse_channel_list(channels_xml: str) -> list[ChannelSummary]:
    root = ET.fromstring(channels_xml)
    channels: list[ChannelSummary] = []

    if root.tag == "channel":
        return [parse_channel_summary(channels_xml)]

    for channel in root.iter():
        if channel.tag == "channel":
            channels.append(
                ChannelSummary(
                    id=_find_first_text(channel, ("id",)),
                    name=_find_first_text(channel, ("name",)),
                )
            )
    return channels


def diff_xml(old_xml: str, new_xml: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            old_xml.splitlines(),
            new_xml.splitlines(),
            fromfile="before.xml",
            tofile="after.xml",
            lineterm="",
        )
    )


def _find_first_text(root: ET.Element, names: tuple[str, ...]) -> str | None:
    for name in names:
        found = root.find(name)
        if found is not None and found.text:
            return found.text.strip()
    return None
