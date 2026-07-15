/* All regular expressions live here (constitution III.5) — named exports only. */

/** 24h wall-clock time, e.g. "09:30" or "23:05". */
export const time_hhmm_pattern = /^(?:[01]\d|2[0-3]):[0-5]\d$/;

/** Value emitted by <input type="datetime-local">, minute precision. */
export const datetime_local_pattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/;
