"""UUID v7 generation (RFC 9562) — time-ordered primary keys on every table."""
import os
import time
import uuid


def uuid7() -> str:
    timestamp_ms = time.time_ns() // 1_000_000
    rand = os.urandom(10)
    raw = bytearray(16)
    raw[0:6] = timestamp_ms.to_bytes(6, "big")
    raw[6] = 0x70 | (rand[0] & 0x0F)
    raw[7] = rand[1]
    raw[8] = 0x80 | (rand[2] & 0x3F)
    raw[9:16] = rand[3:10]
    return str(uuid.UUID(bytes=bytes(raw)))
