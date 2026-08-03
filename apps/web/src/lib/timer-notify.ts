/** Canvas timer completion alerts: a short synthesized chime via the Web
 * Audio API, plus a best-effort desktop Notification. No service worker —
 * this is a foreground, client-computed timer with no server push to
 * justify one; a plain `Notification` from the open tab already covers "the
 * app is open but not focused" without the extra build/registration surface
 * a service worker would add for a single-user local app.
 */

let audio_ctx: AudioContext | null = null;

/** Call from a real user gesture (e.g. clicking "Start") so browser autoplay
 * policies don't block the chime later, when a timer completes with no
 * fresh gesture behind it. Safe to call repeatedly. */
export function unlock_audio(): void {
  if (audio_ctx) {
    void audio_ctx.resume();
    return;
  }
  const ctor = window.AudioContext;
  if (!ctor) return;
  audio_ctx = new ctor();
}

function beep(ctx: AudioContext, start_at: number, frequency: number, duration_s: number): void {
  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();
  oscillator.type = "sine";
  oscillator.frequency.value = frequency;
  gain.gain.setValueAtTime(0.0001, start_at);
  gain.gain.exponentialRampToValueAtTime(0.25, start_at + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, start_at + duration_s);
  oscillator.connect(gain);
  gain.connect(ctx.destination);
  oscillator.start(start_at);
  oscillator.stop(start_at + duration_s);
}

/** A short two-tone chime — audible over normal desktop volume without
 * being alarming. Silently no-ops if Web Audio isn't available; the toast
 * still shows either way. */
export function play_completion_chime(): void {
  if (!audio_ctx) unlock_audio();
  if (!audio_ctx) return;
  void audio_ctx.resume();
  const now = audio_ctx.currentTime;
  beep(audio_ctx, now, 880, 0.16);
  beep(audio_ctx, now + 0.18, 1174.66, 0.22);
}

/** Best-effort, one-time — never re-prompts once the user has answered
 * (granted or denied); call on canvas page mount. */
export function request_notification_permission(): void {
  if (!("Notification" in window)) return;
  if (Notification.permission === "default") {
    void Notification.requestPermission();
  }
}

export function notify_timer_complete(title: string): void {
  play_completion_chime();
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  try {
    // eslint-disable-next-line no-new
    new Notification("Timer complete", { body: title, tag: "timebox-canvas-timer" });
  } catch {
    // Some browsers refuse to construct Notification directly (without a
    // service worker) once the page is backgrounded on certain platforms —
    // the chime + toast already covers the alert either way.
  }
}
