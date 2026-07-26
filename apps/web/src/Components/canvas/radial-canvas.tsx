import { useEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import { format_elapsed } from "../focus/session-timer";
import { display_seconds } from "./timer-math";
import type { CanvasItem } from "../../lib/api-schemas";

/*
 * The Radial Canvas's core primitive rendering: a hand-rolled r/theta
 * layout drawn on a <canvas> element (this repo's convention — reach for
 * <canvas>/WebGL over hand-authored SVG path data for anything generative;
 * see specs/010-radial-canvas/spec.md "Architecture"). All r/theta math
 * happens in one fixed logical coordinate space (`logical_size_px`);
 * pointer events are converted into that space from the canvas's actual
 * on-screen (CSS-scaled) size, so the canvas can be styled responsively
 * via Tailwind (`w-full aspect-square`) without re-deriving geometry.
 */

const tick_interval_ms = 1_000;
const logical_size_px = 640;
const marker_radius_px = 46;
const marker_margin_px = 12;
const drag_threshold_px = 4;
const title_font = "600 12px var(--tb-font-sans)";
const clock_font = "700 15px var(--tb-font-mono)";
const max_title_chars = 14;

type Point = { x: number; y: number };
type DragState = { id: string; start: Point; r: number; theta: number; moved: boolean };

function polar_to_point(r: number, theta_deg: number, max_radius: number, center: Point): Point {
  const theta_rad = (theta_deg * Math.PI) / 180;
  return {
    x: center.x + r * max_radius * Math.cos(theta_rad),
    y: center.y + r * max_radius * Math.sin(theta_rad),
  };
}

function point_to_polar(
  point: Point,
  max_radius: number,
  center: Point,
): { r: number; theta: number } {
  const dx = point.x - center.x;
  const dy = point.y - center.y;
  const distance = Math.hypot(dx, dy);
  const theta_deg = ((Math.atan2(dy, dx) * 180) / Math.PI + 360) % 360;
  return { r: Math.min(1, distance / max_radius), theta: theta_deg };
}

/** Canvas drawing needs concrete color strings, not Tailwind classes — read
 * the token's resolved value from the DOM rather than hardcoding one. */
function css_var(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function marker_color(item: CanvasItem): string {
  if (item.status === "completed") return css_var("--tb-color-ok");
  if (item.status === "running") return css_var("--tb-accent");
  return css_var("--tb-color-slate");
}

function truncate_title(title: string): string {
  return title.length > max_title_chars ? `${title.slice(0, max_title_chars - 1)}…` : title;
}

export function RadialCanvas({ items, on_select, on_move }: {
  items: CanvasItem[];
  on_select: (item: CanvasItem) => void;
  on_move: (id: string, r: number, theta: number) => void;
}) {
  const canvas_ref = useRef<HTMLCanvasElement>(null);
  const drag_ref = useRef<DragState | null>(null);
  const [, force_tick] = useState(0);
  const [drag_override, set_drag_override] = useState<{ id: string; r: number; theta: number } | null>(
    null,
  );

  const center: Point = { x: logical_size_px / 2, y: logical_size_px / 2 };
  const max_radius = logical_size_px / 2 - marker_radius_px - marker_margin_px;

  // One-time backing-store setup: draw in a fixed logical coordinate space,
  // scaled for the device's pixel ratio; CSS handles the responsive display size.
  useEffect(() => {
    const canvas = canvas_ref.current;
    if (!canvas) return;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = logical_size_px * ratio;
    canvas.height = logical_size_px * ratio;
    const ctx = canvas.getContext("2d");
    ctx?.setTransform(ratio, 0, 0, ratio, 0, 0);
  }, []);

  useEffect(() => {
    const id = setInterval(() => force_tick((n) => n + 1), tick_interval_ms);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const canvas = canvas_ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    ctx.clearRect(0, 0, logical_size_px, logical_size_px);

    ctx.strokeStyle = css_var("--tb-border");
    ctx.lineWidth = 1;
    for (const fraction of [0.33, 0.66, 1]) {
      ctx.beginPath();
      ctx.arc(center.x, center.y, max_radius * fraction, 0, Math.PI * 2);
      ctx.stroke();
    }

    const now_ms = Date.now();
    for (const item of items) {
      const override = drag_override && drag_override.id === item.id ? drag_override : null;
      const r = override?.r ?? item.r;
      const theta = override?.theta ?? item.theta;
      const point = polar_to_point(r, theta, max_radius, center);

      ctx.beginPath();
      ctx.arc(point.x, point.y, marker_radius_px, 0, Math.PI * 2);
      ctx.fillStyle = marker_color(item);
      ctx.globalAlpha = item.status === "paused" ? 0.55 : 0.88;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.lineWidth = 2;
      ctx.strokeStyle = css_var("--tb-border-strong");
      ctx.stroke();

      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = css_var("--tb-text-hi");
      ctx.font = title_font;
      ctx.fillText(truncate_title(item.title), point.x, point.y - 11);
      ctx.font = clock_font;
      ctx.fillText(format_elapsed(display_seconds(item, now_ms)), point.x, point.y + 9);
    }
    // Re-render every tick (for live MM:SS) and whenever items/drag state change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, drag_override]);

  const to_logical_point = (event: ReactPointerEvent<HTMLCanvasElement>): Point => {
    const rect = event.currentTarget.getBoundingClientRect();
    const scale = logical_size_px / rect.width;
    return { x: (event.clientX - rect.left) * scale, y: (event.clientY - rect.top) * scale };
  };

  const hit_test = (point: Point): CanvasItem | null => {
    for (let index = items.length - 1; index >= 0; index -= 1) {
      const item = items[index];
      if (!item) continue;
      const marker = polar_to_point(item.r, item.theta, max_radius, center);
      if (Math.hypot(marker.x - point.x, marker.y - point.y) <= marker_radius_px) return item;
    }
    return null;
  };

  const handle_pointer_down = (event: ReactPointerEvent<HTMLCanvasElement>) => {
    const point = to_logical_point(event);
    const hit = hit_test(point);
    if (!hit) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    drag_ref.current = { id: hit.id, start: point, r: hit.r, theta: hit.theta, moved: false };
  };

  const handle_pointer_move = (event: ReactPointerEvent<HTMLCanvasElement>) => {
    const drag = drag_ref.current;
    if (!drag) return;
    const point = to_logical_point(event);
    if (!drag.moved && Math.hypot(point.x - drag.start.x, point.y - drag.start.y) < drag_threshold_px) {
      return;
    }
    const { r, theta } = point_to_polar(point, max_radius, center);
    drag_ref.current = { ...drag, r, theta, moved: true };
    set_drag_override({ id: drag.id, r, theta });
  };

  const handle_pointer_up = () => {
    const drag = drag_ref.current;
    drag_ref.current = null;
    set_drag_override(null);
    if (!drag) return;
    if (drag.moved) {
      on_move(drag.id, drag.r, drag.theta);
      return;
    }
    const item = items.find((candidate) => candidate.id === drag.id);
    if (item) on_select(item);
  };

  return (
    <div className="mx-auto w-full max-w-(--tb-canvas-diameter)">
      <canvas
        ref={canvas_ref}
        role="img"
        aria-label="Radial canvas of timers and stopwatches — click one to edit, drag to reposition"
        className="aspect-square w-full touch-none rounded-full"
        onPointerDown={handle_pointer_down}
        onPointerMove={handle_pointer_move}
        onPointerUp={handle_pointer_up}
      />
    </div>
  );
}
