from dataclasses import dataclass


@dataclass
class DanmakuElem:
    id: int = 0
    progress: int = 0
    mode: int = 0
    fontsize: int = 0
    color: int = 0
    mid_hash: str = ""
    content: str = ""
    ctime: int = 0
    weight: int = 0
    pool: int = 0

    @property
    def timeline(self) -> float:
        return self.progress / 1000.0

    @property
    def send_time(self) -> str | None:
        if self.ctime <= 0:
            return None
        from datetime import datetime, timedelta, timezone
        tz = timezone(timedelta(hours=8))
        return datetime.fromtimestamp(self.ctime, tz=tz).strftime("%Y-%m-%d %H:%M:%S")


WIRE_VARINT = 0
WIRE_64BIT = 1
WIRE_LENGTH_DELIMITED = 2
WIRE_32BIT = 5


def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while pos < len(data):
        byte = data[pos]
        result |= (byte & 0x7F) << shift
        pos += 1
        if not (byte & 0x80):
            break
        shift += 7
    return result, pos


def _read_length_delimited(data: bytes, pos: int) -> tuple[bytes, int]:
    length, pos = _read_varint(data, pos)
    return data[pos:pos + length], pos + length


def parse_danmaku_seg(data: bytes) -> list[dict]:
    results = []
    pos = 0
    while pos < len(data):
        if pos >= len(data):
            break
        tag, pos = _read_varint(data, pos)
        field_number = tag >> 3
        wire_type = tag & 0x07

        if field_number == 1 and wire_type == WIRE_LENGTH_DELIMITED:
            elem_data, pos = _read_length_delimited(data, pos)
            elem = _parse_danmaku_elem(elem_data)
            results.append(elem)
        elif wire_type == WIRE_VARINT:
            _, pos = _read_varint(data, pos)
        elif wire_type == WIRE_64BIT:
            pos += 8
        elif wire_type == WIRE_32BIT:
            pos += 4
        elif wire_type == WIRE_LENGTH_DELIMITED:
            _, pos = _read_length_delimited(data, pos)
        else:
            break

    return results


def _parse_danmaku_elem(data: bytes) -> dict:
    elem = DanmakuElem()
    pos = 0
    while pos < len(data):
        if pos >= len(data):
            break
        tag, pos = _read_varint(data, pos)
        field_number = tag >> 3
        wire_type = tag & 0x07

        if wire_type == WIRE_VARINT:
            val, pos = _read_varint(data, pos)
            if field_number == 1:
                elem.id = val
            elif field_number == 2:
                elem.progress = val
            elif field_number == 3:
                elem.mode = val
            elif field_number == 4:
                elem.fontsize = val
            elif field_number == 5:
                elem.color = val
            elif field_number == 8:
                elem.ctime = val
            elif field_number == 9:
                elem.weight = val
            elif field_number == 11:
                elem.pool = val
        elif wire_type == WIRE_LENGTH_DELIMITED:
            raw, pos = _read_length_delimited(data, pos)
            try:
                val = raw.decode("utf-8")
            except UnicodeDecodeError:
                val = ""
            if field_number == 6:
                elem.mid_hash = val
            elif field_number == 7:
                elem.content = val
        elif wire_type == WIRE_64BIT:
            pos += 8
        elif wire_type == WIRE_32BIT:
            pos += 4
        else:
            break

    return {
        "id": elem.id,
        "progress": elem.progress,
        "mode": elem.mode,
        "fontsize": elem.fontsize,
        "color": elem.color,
        "mid_hash": elem.mid_hash,
        "content": elem.content,
        "ctime": elem.ctime,
        "weight": elem.weight,
        "pool": elem.pool,
        "timeline": elem.timeline,
        "send_time": elem.send_time,
    }
