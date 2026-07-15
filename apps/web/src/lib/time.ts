/* Date/time helpers. The API speaks ISO-8601 UTC with a Z suffix. */

import { date_ymd_pattern, time_hhmm_pattern } from "./patterns";

export const day_start_hour = 6;
export const day_end_hour = 24;
export const visible_hours = day_end_hour - day_start_hour;
export const days_per_week = 7;

const ms_per_minute = 60_000;
const ms_per_day = 86_400_000;
const month_names = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
] as const;
const weekday_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] as const;

function pad2(value: number): string {
  return String(value).padStart(2, "0");
}

export function to_iso(date: Date): string {
  return date.toISOString();
}

/** Monday-start week. */
export function start_of_week(date: Date): Date {
  const result = new Date(date);
  result.setHours(0, 0, 0, 0);
  const monday_offset = (result.getDay() + 6) % 7;
  result.setDate(result.getDate() - monday_offset);
  return result;
}

export function add_days(date: Date, count: number): Date {
  const result = new Date(date);
  result.setDate(result.getDate() + count);
  return result;
}

export type WeekRange = { start: Date; end: Date; days: Date[] };

export function week_range(anchor: Date): WeekRange {
  const start = start_of_week(anchor);
  const days = Array.from({ length: days_per_week }, (_, index) =>
    add_days(start, index),
  );
  return { start, end: add_days(start, days_per_week), days };
}

export function is_same_day(a: Date, b: Date): boolean {
  const same_date = a.getDate() === b.getDate();
  const same_month = a.getMonth() === b.getMonth();
  const same_year = a.getFullYear() === b.getFullYear();
  return same_date && same_month && same_year;
}

export function slot_start(day: Date, hour: number): Date {
  const result = new Date(day);
  result.setHours(hour, 0, 0, 0);
  return result;
}

/* ------------------------------------------------------------ formatting */

export function format_hour_label(hour: number): string {
  return `${pad2(hour % 24)}:00`;
}

export function format_day_label(day: Date): string {
  return `${weekday_names[day.getDay()] ?? ""} ${day.getDate()}`;
}

export function format_week_title(range: WeekRange): string {
  const start = range.days[0];
  const last = range.days[range.days.length - 1];
  if (!start || !last) return "";
  const start_month = month_names[start.getMonth()] ?? "";
  const end_month = month_names[last.getMonth()] ?? "";
  const same_month = start.getMonth() === last.getMonth();
  const left = `${start_month} ${start.getDate()}`;
  const right = same_month
    ? `${last.getDate()}`
    : `${end_month} ${last.getDate()}`;
  return `${left} – ${right}, ${last.getFullYear()}`;
}

export function format_time(iso: string): string {
  const date = new Date(iso);
  return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

export function format_time_range(start_iso: string, end_iso: string): string {
  return `${format_time(start_iso)} – ${format_time(end_iso)}`;
}

export function format_day_and_time(iso: string): string {
  const date = new Date(iso);
  const weekday = weekday_names[date.getDay()] ?? "";
  const month = month_names[date.getMonth()] ?? "";
  return `${weekday} ${date.getDate()} ${month}, ${format_time(iso)}`;
}

export function minutes_between(start_iso: string, end_iso: string): number {
  const delta = new Date(end_iso).getTime() - new Date(start_iso).getTime();
  return Math.round(delta / ms_per_minute);
}

/* ------------------------------------------- <input type=datetime-local> */

export function iso_to_local_input(iso: string): string {
  const date = new Date(iso);
  const date_part = `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
  return `${date_part}T${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

export function local_input_to_iso(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : date.toISOString();
}

/* --------------------------------------------- <input type=date / time> */

/** "YYYY-MM-DD" (local wall-clock date) for an ISO instant. */
export function date_input_value(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

/** "HH:MM" (local wall-clock time) for an ISO instant. */
export function time_input_value(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

/** Combine a "YYYY-MM-DD" date and "HH:MM" time (local) into an ISO instant. */
export function compose_local_iso(date_str: string, time_str: string): string {
  if (!date_ymd_pattern.test(date_str) || !time_hhmm_pattern.test(time_str)) {
    return "";
  }
  const date = new Date(`${date_str}T${time_str}`);
  return Number.isNaN(date.getTime()) ? "" : date.toISOString();
}

/** ISO instant for local midnight of the day AFTER "YYYY-MM-DD". */
export function next_day_midnight_iso(date_str: string): string {
  if (!date_ymd_pattern.test(date_str)) return "";
  const date = new Date(`${date_str}T00:00`);
  if (Number.isNaN(date.getTime())) return "";
  date.setDate(date.getDate() + 1);
  return date.toISOString();
}

export function next_full_hour(from: Date): Date {
  const result = new Date(from);
  result.setMinutes(0, 0, 0);
  result.setHours(result.getHours() + 1);
  return result;
}

export function add_minutes_iso(iso: string, minutes: number): string {
  return new Date(new Date(iso).getTime() + minutes * ms_per_minute).toISOString();
}

/* ------------------------------------------------------- grid placement */

export type DayLayout = { top_pct: number; height_pct: number };

/** Position of an event inside one day column, as % of the visible window. */
export function event_day_layout(
  start_iso: string,
  end_iso: string,
  day: Date,
): DayLayout | null {
  const window_start = slot_start(day, day_start_hour).getTime();
  const window_end = window_start + visible_hours * (ms_per_day / 24);
  const start = Math.max(new Date(start_iso).getTime(), window_start);
  const end = Math.min(new Date(end_iso).getTime(), window_end);
  if (end <= start) return null;
  const window_span = window_end - window_start;
  const top_pct = ((start - window_start) / window_span) * 100;
  const height_pct = Math.max(((end - start) / window_span) * 100, 1.5);
  return { top_pct, height_pct };
}
