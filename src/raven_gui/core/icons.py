"""Reading a program's icon out of its resources as an .ico file."""

from __future__ import annotations

import logging
import struct
from pathlib import Path

import pefile

logger = logging.getLogger(__name__)

_RT_ICON = pefile.RESOURCE_TYPE["RT_ICON"]
_RT_GROUP_ICON = pefile.RESOURCE_TYPE["RT_GROUP_ICON"]
_GROUP_HEADER = struct.Struct("<HHH")
# A group entry ends in the resource id of the image; an .ico entry ends in the offset of the image in the file.
_GROUP_ENTRY = struct.Struct("<BBBBHHIH")
_FILE_ENTRY = struct.Struct("<BBBBHHII")


def _resources(pe: pefile.PE, kind: int) -> dict[int, bytes]:
    """Return the first language of every resource of a kind, by resource id."""
    found: dict[int, bytes] = {}
    root = getattr(pe, "DIRECTORY_ENTRY_RESOURCE", None)
    for type_entry in root.entries if root else []:
        if type_entry.id != kind:
            continue
        for name_entry in type_entry.directory.entries:
            languages = name_entry.directory.entries
            if languages:
                data = languages[0].data.struct
                found[name_entry.id if name_entry.id is not None else len(found)] = pe.get_data(
                    data.OffsetToData, data.Size
                )
    return found


def icon_from_group(group: bytes, images: dict[int, bytes]) -> bytes | None:
    """Assemble an .ico file from an icon group resource and the icon images it names."""
    if len(group) < _GROUP_HEADER.size:
        return None
    _reserved, kind, count = _GROUP_HEADER.unpack_from(group)
    entries = []
    for index in range(count):
        offset = _GROUP_HEADER.size + index * _GROUP_ENTRY.size
        if offset + _GROUP_ENTRY.size > len(group):
            break
        *fields, image_id = _GROUP_ENTRY.unpack_from(group, offset)
        if image_id in images:
            entries.append((fields, images[image_id]))
    if not entries:
        return None
    header = _GROUP_HEADER.pack(0, kind, len(entries))
    offset = _GROUP_HEADER.size + len(entries) * _FILE_ENTRY.size
    directory, data = b"", b""
    for (width, height, colors, reserved, planes, bits, _size), image in entries:
        directory += _FILE_ENTRY.pack(width, height, colors, reserved, planes, bits, len(image), offset + len(data))
        data += image
    return header + directory + data


def extract_icon(program: Path) -> bytes | None:
    """Return the program's main icon as an .ico file, or None when it has none or cannot be read."""
    try:
        pe = pefile.PE(str(program), fast_load=True)
        try:
            pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
            groups = _resources(pe, _RT_GROUP_ICON)
            if not groups:
                return None
            # The main icon is the group with the lowest id, the one Windows Explorer shows.
            return icon_from_group(groups[min(groups)], _resources(pe, _RT_ICON))
        finally:
            pe.close()
    except (OSError, pefile.PEFormatError) as error:
        logger.warning("No icon read from %s: %s", program, error)
        return None
