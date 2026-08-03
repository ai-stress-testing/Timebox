"""Title normalization + hashing — shared primitive for duration_profiles and
the future event_memory spec (006). Dependency-free on purpose: both specs
import this rather than each writing their own copy.
"""
import hashlib


def normalize_title(s: str) -> str:
    return s.strip().casefold()


def hash_title(s: str) -> str:
    return hashlib.sha256(normalize_title(s).encode("utf-8")).hexdigest()
