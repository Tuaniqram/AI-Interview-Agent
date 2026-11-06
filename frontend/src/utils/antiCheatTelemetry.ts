import { useEffect, useRef } from 'react';

export interface AntiCheatTelemetry {
  paste_chars: number;
  focus_lost_count: number;
  /** 'typing' | 'voice' — voice answers skip paste/typing-rate signals */
  answer_source?: 'typing' | 'voice';
  /** Inter-key intervals (ms) for the current answer — transcription cadence analysis */
  keystroke_intervals: number[];
  /** ms between the question appearing and the first keystroke (0 = none typed) */
  first_key_ms: number | null;
  /** Pointer left the browser window/viewport while it stayed focused (second-screen reading) */
  pointer_leaves: number;
  /** rAF heartbeat divergences from wall clock (debugger pause / VM snapshot) */
  heartbeat_gaps: number;
}

const MAX_INTERVALS = 4000;
const POINTER_DEBOUNCE_MS = 1500;
const HEARTBEAT_DEBOUNCE_MS = 2000;
const TAMPER_DIVERGENCE_MS = 500;

/**
 * Collects client-side anti-cheat telemetry (contract: docs/anti-cheat-guard.md
 * §4.1 + §4.6). Counters reset when the question changes. Telemetry is a
 * *signal*, not proof — a determined candidate can clear or fake these values,
 * which is exactly why the heartbeat/pointer/cadence signals exist: they are
 * invariants of the runtime rather than events a spoofing script can trivially
 * fabricate consistently.
 */
export function useAntiCheatTelemetry(questionNumber: number | undefined) {
  const ref = useRef<AntiCheatTelemetry>({
    paste_chars: 0,
    focus_lost_count: 0,
    keystroke_intervals: [],
    first_key_ms: null,
    pointer_leaves: 0,
    heartbeat_gaps: 0,
  });
  const lastQuestion = useRef<number | undefined>(questionNumber);
  const clockRef = useRef({ answerShownAt: Date.now(), lastKeyAt: 0, typingStarted: false });

  useEffect(() => {
    if (questionNumber !== undefined && lastQuestion.current !== questionNumber) {
      ref.current.paste_chars = 0;
      ref.current.focus_lost_count = 0;
      ref.current.keystroke_intervals = [];
      ref.current.first_key_ms = null;
      ref.current.pointer_leaves = 0;
      ref.current.heartbeat_gaps = 0;
      clockRef.current = { answerShownAt: Date.now(), lastKeyAt: 0, typingStarted: false };
      lastQuestion.current = questionNumber;
    }
  }, [questionNumber]);

  useEffect(() => {
    let lastVisibilityAt = 0;
    let lastBlurAt = 0;
    let lastPointerAt = 0;
    let lastHeartbeatAt = 0;

    const onPaste = (e: ClipboardEvent) => {
      const text = e.clipboardData?.getData('text') || '';
      if (text.length > 0) ref.current.paste_chars += text.length;
    };

    const onVisibility = () => {
      if (!document.hidden) return;
      const now = Date.now();
      if (now - lastVisibilityAt > 1000) {
        ref.current.focus_lost_count += 1;
        lastVisibilityAt = now;
      }
    };

    const onBlur = () => {
      const now = Date.now();
      // Avoid double-counting the same tab-switch (visibilitychange + blur).
      if (now - lastBlurAt > 1000 && now - lastVisibilityAt > 1000) {
        ref.current.focus_lost_count += 1;
        lastBlurAt = now;
      }
    };

    // Pointer leaving the window while it keeps focus = side-by-side screen
    // reading (moving the mouse to another monitor's app). relatedTarget is
    // null only when the pointer exits the window/viewport entirely.
    const onPointerOut = (e: PointerEvent) => {
      if (e.relatedTarget !== null && !(e.relatedTarget instanceof Window)) return;
      const now = Date.now();
      if (now - lastPointerAt > POINTER_DEBOUNCE_MS) {
        ref.current.pointer_leaves += 1;
        lastPointerAt = now;
      }
    };

    // Heartbeat: rAF ticks while the page is visible and JS runs. When the
    // page is frozen (debugger breakpoint, VM snapshot, throttled tab) the
    // rAF clock stands still while the wall clock advances — the divergence
    // between the two is an invariant a spoofing script must actively fake.
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const isField = !!target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA');
      if (!isField || e.repeat) return;
      const now = Date.now();
      if (!clockRef.current.typingStarted) {
        clockRef.current.typingStarted = true;
        clockRef.current.lastKeyAt = now;
        ref.current.first_key_ms = now - clockRef.current.answerShownAt;
        return;
      }
      const interval = now - clockRef.current.lastKeyAt;
      clockRef.current.lastKeyAt = now;
      if (interval >= 0 && interval < 60000) {
        if (ref.current.keystroke_intervals.length < MAX_INTERVALS) {
          ref.current.keystroke_intervals.push(interval);
        }
      }
    };

    let lastWall = Date.now();
    let lastRaf = performance.now();
    let rafId = 0;
    const heartbeat = () => {
      const wallNow = Date.now();
      const rafNow = performance.now();
      const wallDelta = wallNow - lastWall;
      const rafDelta = rafNow - lastRaf;
      lastWall = wallNow;
      lastRaf = rafNow;
      const now = wallNow;
      if (rafDelta >= 0 && wallDelta - rafDelta > TAMPER_DIVERGENCE_MS && !document.hidden && now - lastHeartbeatAt > HEARTBEAT_DEBOUNCE_MS) {
        ref.current.heartbeat_gaps += 1;
        lastHeartbeatAt = now;
      }
      rafId = requestAnimationFrame(heartbeat);
    };
    rafId = requestAnimationFrame(heartbeat);

    window.addEventListener('paste', onPaste);
    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('blur', onBlur);
    window.addEventListener('pointerout', onPointerOut);
    window.addEventListener('keydown', onKeyDown);
    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener('paste', onPaste);
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('blur', onBlur);
      window.removeEventListener('pointerout', onPointerOut);
      window.removeEventListener('keydown', onKeyDown);
    };
  }, []);

  return ref;
}
