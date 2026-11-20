import type { GestureDefinition, GestureTypeName } from './GestureTypes'

const _ = (v: number) => v

export const GESTURE_LIBRARY: Record<GestureTypeName, GestureDefinition> = {

  /* ───────── Open Palm ─────────
     Arm slightly forward, forearm rotates outward, palm opens.
     Shoulder relaxed, small upper-arm movement.
  */
  openPalm: {
    name: 'openPalm', arm: 'right',
    phases: [
      { duration: 0.12, easing: 'easeOut', targets: { rightForeArm: { rotation: [0, 0, _(-0.06)] } } },
      { duration: 0.28, easing: 'easeInOut', targets: { rightArm: { rotation: [_(-0.04), 0, _(0.04)] }, rightForeArm: { rotation: [0, 0, _(-0.18)] } } },
      { duration: 0.50, easing: 'easeInOut', targets: { rightArm: { rotation: [_(-0.04), 0, _(0.04)] }, rightForeArm: { rotation: [0, 0, _(-0.18)] } } },
      { duration: 0.20, easing: 'easeIn', targets: { rightArm: { rotation: [_(-0.02), 0, _(0.02)] }, rightForeArm: { rotation: [0, 0, _(-0.08)] } } },
      { duration: 0.15, easing: 'easeOut', targets: { rightArm: { rotation: [0, 0, 0] }, rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },

  /* ───────── Single Hand Emphasis ─────────
     Dominant hand moves, small forward motion, returns.
     Other hand stays still.
  */
  singleHandEmphasis: {
    name: 'singleHandEmphasis', arm: 'right',
    phases: [
      { duration: 0.10, easing: 'easeOut', targets: { rightArm: { rotation: [_(0.02), 0, _(-0.01)] } } },
      { duration: 0.22, easing: 'easeInOut', targets: { rightArm: { rotation: [_(-0.10), 0, _(0.04)] }, rightForeArm: { rotation: [_(0.06), 0, _(-0.10)] } } },
      { duration: 0.40, easing: 'easeInOut', targets: { rightArm: { rotation: [_(-0.10), 0, _(0.04)] }, rightForeArm: { rotation: [_(0.06), 0, _(-0.10)] } } },
      { duration: 0.18, easing: 'easeIn', targets: { rightArm: { rotation: [_(-0.04), 0, _(0.02)] }, rightForeArm: { rotation: [_(0.02), 0, _(-0.04)] } } },
      { duration: 0.12, easing: 'easeOut', targets: { rightArm: { rotation: [0, 0, 0] }, rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },

  /* ───────── Both Hands Open ─────────
     Both arms open slightly, chest opens, shoulders rotate naturally.
  */
  bothHandsOpen: {
    name: 'bothHandsOpen', arm: 'both',
    phases: [
      { duration: 0.12, easing: 'easeOut', targets: { leftArm: { rotation: [0, 0, _(-0.02)] }, rightArm: { rotation: [0, 0, _(0.02)] } } },
      { duration: 0.30, easing: 'easeInOut', targets: { leftArm: { rotation: [_(-0.04), 0, _(-0.05)] }, rightArm: { rotation: [_(-0.04), 0, _(0.05)] }, leftForeArm: { rotation: [0, 0, _(0.06)] }, rightForeArm: { rotation: [0, 0, _(-0.06)] } } },
      { duration: 0.45, easing: 'easeInOut', targets: { leftArm: { rotation: [_(-0.04), 0, _(-0.05)] }, rightArm: { rotation: [_(-0.04), 0, _(0.05)] }, leftForeArm: { rotation: [0, 0, _(0.06)] }, rightForeArm: { rotation: [0, 0, _(-0.06)] } } },
      { duration: 0.22, easing: 'easeIn', targets: { leftArm: { rotation: [_(-0.02), 0, _(-0.02)] }, rightArm: { rotation: [_(-0.02), 0, _(0.02)] }, leftForeArm: { rotation: [0, 0, _(0.02)] }, rightForeArm: { rotation: [0, 0, _(-0.02)] } } },
      { duration: 0.15, easing: 'easeOut', targets: { leftArm: { rotation: [0, 0, 0] }, rightArm: { rotation: [0, 0, 0] }, leftForeArm: { rotation: [0, 0, 0] }, rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },

  /* ───────── Forearm Lift ─────────
     Elbow bends, forearm raises, upper arm stays mostly stable.
  */
  forearmLift: {
    name: 'forearmLift', arm: 'right',
    phases: [
      { duration: 0.10, easing: 'easeOut', targets: { rightForeArm: { rotation: [_(0.03), 0, _(-0.02)] } } },
      { duration: 0.25, easing: 'easeInOut', targets: { rightForeArm: { rotation: [_(0.18), 0, _(-0.20)] } } },
      { duration: 0.35, easing: 'easeInOut', targets: { rightForeArm: { rotation: [_(0.18), 0, _(-0.20)] } } },
      { duration: 0.18, easing: 'easeIn', targets: { rightForeArm: { rotation: [_(0.06), 0, _(-0.08)] } } },
      { duration: 0.12, easing: 'easeOut', targets: { rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },

  /* ───────── Palm Upward ─────────
     Forearm supination, palm facing upward, small wrist rotation.
  */
  palmUpward: {
    name: 'palmUpward', arm: 'right',
    phases: [
      { duration: 0.10, easing: 'easeOut', targets: { rightForeArm: { rotation: [0, 0, _(-0.04)] } } },
      { duration: 0.25, easing: 'easeInOut', targets: { rightArm: { rotation: [_(0.03), 0, _(0.03)] }, rightForeArm: { rotation: [_(0.05), 0, _(-0.20)] } } },
      { duration: 0.40, easing: 'easeInOut', targets: { rightArm: { rotation: [_(0.03), 0, _(0.03)] }, rightForeArm: { rotation: [_(0.05), 0, _(-0.20)] } } },
      { duration: 0.20, easing: 'easeIn', targets: { rightArm: { rotation: [0, 0, _(0.01)] }, rightForeArm: { rotation: [_(0.02), 0, _(-0.08)] } } },
      { duration: 0.15, easing: 'easeOut', targets: { rightArm: { rotation: [0, 0, 0] }, rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },

  /* ───────── Small Pointing ─────────
     Small forward movement, not aggressive, only during emphasis.
  */
  smallPointing: {
    name: 'smallPointing', arm: 'right',
    phases: [
      { duration: 0.08, easing: 'easeOut', targets: { rightArm: { rotation: [_(0.02), 0, 0] } } },
      { duration: 0.20, easing: 'easeInOut', targets: { rightArm: { rotation: [_(-0.08), _(0.03), _(0.03)] }, rightForeArm: { rotation: [_(0.10), 0, _(-0.08)] } } },
      { duration: 0.35, easing: 'easeInOut', targets: { rightArm: { rotation: [_(-0.08), _(0.03), _(0.03)] }, rightForeArm: { rotation: [_(0.10), 0, _(-0.08)] } } },
      { duration: 0.15, easing: 'easeIn', targets: { rightArm: { rotation: [_(-0.03), _(0.01), _(0.01)] }, rightForeArm: { rotation: [_(0.03), 0, _(-0.03)] } } },
      { duration: 0.10, easing: 'easeOut', targets: { rightArm: { rotation: [0, 0, 0] }, rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },

  /* ───────── Shoulder Emphasis ─────────
     Small shoulder raise, chest follows slightly.
  */
  shoulderEmphasis: {
    name: 'shoulderEmphasis', arm: 'both',
    phases: [
      { duration: 0.10, easing: 'easeOut', targets: { leftShoulder: { rotation: [_(0.01), 0, 0] }, rightShoulder: { rotation: [_(0.01), 0, 0] } } },
      { duration: 0.22, easing: 'easeInOut', targets: { leftShoulder: { rotation: [_(-0.05), 0, _(0.05)] }, rightShoulder: { rotation: [_(-0.05), 0, _(-0.05)] } } },
      { duration: 0.35, easing: 'easeInOut', targets: { leftShoulder: { rotation: [_(-0.05), 0, _(0.05)] }, rightShoulder: { rotation: [_(-0.05), 0, _(-0.05)] } } },
      { duration: 0.18, easing: 'easeIn', targets: { leftShoulder: { rotation: [_(-0.02), 0, _(0.02)] }, rightShoulder: { rotation: [_(-0.02), 0, _(-0.02)] } } },
      { duration: 0.12, easing: 'easeOut', targets: { leftShoulder: { rotation: [0, 0, 0] }, rightShoulder: { rotation: [0, 0, 0] } } },
    ],
  },

  /* ───────── Chest Emphasis ─────────
     Slight torso movement, head follows naturally.
  */
  chestEmphasis: {
    name: 'chestEmphasis', arm: 'right',
    phases: [
      { duration: 0.10, easing: 'easeOut', targets: { spine1: { rotation: [_(-0.01), 0, 0] } } },
      { duration: 0.25, easing: 'easeInOut', targets: { rightArm: { rotation: [_(0.04), _(-0.06), _(0.03)] }, rightForeArm: { rotation: [_(0.12), 0, _(-0.12)] }, spine1: { rotation: [_(-0.03), 0, 0] } } },
      { duration: 0.35, easing: 'easeInOut', targets: { rightArm: { rotation: [_(0.04), _(-0.06), _(0.03)] }, rightForeArm: { rotation: [_(0.12), 0, _(-0.12)] }, spine1: { rotation: [_(-0.03), 0, 0] } } },
      { duration: 0.18, easing: 'easeIn', targets: { rightArm: { rotation: [_(0.02), _(-0.02), _(0.01)] }, rightForeArm: { rotation: [_(0.04), 0, _(-0.04)] }, spine1: { rotation: [_(-0.01), 0, 0] } } },
      { duration: 0.12, easing: 'easeOut', targets: { rightArm: { rotation: [0, 0, 0] }, rightForeArm: { rotation: [0, 0, 0] }, spine1: { rotation: [0, 0, 0] } } },
    ],
  },

  /* ───────── Finger Emphasis ─────────
     If finger bones exist, animate them. Otherwise use hand rotation.
     (Finger bones exist in this avatar, so we use hand rotation as a subtle proxy.)
  */
  fingerEmphasis: {
    name: 'fingerEmphasis', arm: 'right',
    phases: [
      { duration: 0.08, easing: 'easeOut', targets: { rightHand: { rotation: [0, 0, _(-0.02)] } } },
      { duration: 0.18, easing: 'easeInOut', targets: { rightHand: { rotation: [_(0.02), 0, _(-0.07)] }, rightForeArm: { rotation: [0, 0, _(-0.04)] } } },
      { duration: 0.25, easing: 'easeInOut', targets: { rightHand: { rotation: [_(0.02), 0, _(-0.07)] }, rightForeArm: { rotation: [0, 0, _(-0.04)] } } },
      { duration: 0.12, easing: 'easeIn', targets: { rightHand: { rotation: [0, 0, _(-0.02)] }, rightForeArm: { rotation: [0, 0, _(-0.01)] } } },
      { duration: 0.10, easing: 'easeOut', targets: { rightHand: { rotation: [0, 0, 0] }, rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },

  /* ───────── Hand Rotation ─────────
     Small wrist rotation, relaxed.
  */
  handRotation: {
    name: 'handRotation', arm: 'right',
    phases: [
      { duration: 0.10, easing: 'easeOut', targets: { rightHand: { rotation: [0, _(-0.02), 0] } } },
      { duration: 0.22, easing: 'easeInOut', targets: { rightHand: { rotation: [0, _(-0.12), 0] } } },
      { duration: 0.35, easing: 'easeInOut', targets: { rightHand: { rotation: [0, _(-0.12), 0] } } },
      { duration: 0.18, easing: 'easeIn', targets: { rightHand: { rotation: [0, _(-0.04), 0] } } },
      { duration: 0.12, easing: 'easeOut', targets: { rightHand: { rotation: [0, 0, 0] } } },
    ],
  },

  /* ───────── Small Shrug ─────────
     Both shoulders raise slightly, short duration, return.
  */
  smallShrug: {
    name: 'smallShrug', arm: 'both',
    phases: [
      { duration: 0.10, easing: 'easeOut', targets: { leftShoulder: { rotation: [_(0.01), 0, 0] }, rightShoulder: { rotation: [_(0.01), 0, 0] } } },
      { duration: 0.25, easing: 'easeInOut', targets: { leftShoulder: { rotation: [_(-0.06), 0, 0] }, rightShoulder: { rotation: [_(-0.06), 0, 0] } } },
      { duration: 0.30, easing: 'easeInOut', targets: { leftShoulder: { rotation: [_(-0.06), 0, 0] }, rightShoulder: { rotation: [_(-0.06), 0, 0] } } },
      { duration: 0.20, easing: 'easeIn', targets: { leftShoulder: { rotation: [_(-0.02), 0, 0] }, rightShoulder: { rotation: [_(-0.02), 0, 0] } } },
      { duration: 0.15, easing: 'easeOut', targets: { leftShoulder: { rotation: [0, 0, 0] }, rightShoulder: { rotation: [0, 0, 0] } } },
    ],
  },

  /* ───────── Question Emphasis ─────────
     Small head tilt, open hand, slight eyebrow/expression trigger.
  */
  questionEmphasis: {
    name: 'questionEmphasis', arm: 'right',
    phases: [
      { duration: 0.12, easing: 'easeOut', targets: { head: { rotation: [0, 0, _(0.01)] }, rightForeArm: { rotation: [0, 0, _(-0.03)] } } },
      { duration: 0.28, easing: 'easeInOut', targets: { head: { rotation: [_(-0.02), 0, _(0.05)] }, rightArm: { rotation: [_(0.04), 0, _(0.05)] }, rightForeArm: { rotation: [0, 0, _(-0.12)] } } },
      { duration: 0.45, easing: 'easeInOut', targets: { head: { rotation: [_(-0.02), 0, _(0.05)] }, rightArm: { rotation: [_(0.04), 0, _(0.05)] }, rightForeArm: { rotation: [0, 0, _(-0.12)] } } },
      { duration: 0.20, easing: 'easeIn', targets: { head: { rotation: [0, 0, _(0.02)] }, rightArm: { rotation: [_(0.02), 0, _(0.02)] }, rightForeArm: { rotation: [0, 0, _(-0.04)] } } },
      { duration: 0.15, easing: 'easeOut', targets: { head: { rotation: [0, 0, 0] }, rightArm: { rotation: [0, 0, 0] }, rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },

  /* ───────── Agreement Nod ─────────
     Head only. X-axis rotation (confirmed by skeleton analysis).
     Sequence: slight down → slight up → neutral.
  */
  agreementNod: {
    name: 'agreementNod', arm: 'both',
    phases: [
      { duration: 0.08, easing: 'easeOut', targets: { head: { rotation: [_(0.01), 0, 0] } } },
      { duration: 0.18, easing: 'easeInOut', targets: { head: { rotation: [_(-0.05), 0, 0] } } },
      { duration: 0.20, easing: 'easeInOut', targets: { head: { rotation: [_(0.03), 0, 0] } } },
      { duration: 0.18, easing: 'easeIn', targets: { head: { rotation: [_(0.01), 0, 0] } } },
      { duration: 0.12, easing: 'easeOut', targets: { head: { rotation: [0, 0, 0] } } },
    ],
  },

  /* ───────── Explanation Gesture ─────────
     Common interviewer gesture: hand opens, moves slightly outward, returns.
  */
  explanationGesture: {
    name: 'explanationGesture', arm: 'right',
    phases: [
      { duration: 0.12, easing: 'easeOut', targets: { rightArm: { rotation: [_(0.02), 0, _(0.01)] }, rightForeArm: { rotation: [0, 0, _(-0.03)] } } },
      { duration: 0.30, easing: 'easeInOut', targets: { rightArm: { rotation: [_(-0.08), _(0.04), _(0.06)] }, rightForeArm: { rotation: [_(0.12), 0, _(-0.18)] } } },
      { duration: 0.50, easing: 'easeInOut', targets: { rightArm: { rotation: [_(-0.08), _(0.04), _(0.06)] }, rightForeArm: { rotation: [_(0.12), 0, _(-0.18)] } } },
      { duration: 0.20, easing: 'easeIn', targets: { rightArm: { rotation: [_(-0.03), _(0.02), _(0.02)] }, rightForeArm: { rotation: [_(0.04), 0, _(-0.06)] } } },
      { duration: 0.15, easing: 'easeOut', targets: { rightArm: { rotation: [0, 0, 0] }, rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },

  /* ───────── Closing Gesture ─────────
     Professional ending: both hands relax, small open palm, return idle.
  */
  closingGesture: {
    name: 'closingGesture', arm: 'both',
    phases: [
      { duration: 0.15, easing: 'easeOut', targets: { leftArm: { rotation: [_(0.01), 0, _(-0.01)] }, rightArm: { rotation: [_(0.01), 0, _(0.01)] }, leftForeArm: { rotation: [0, 0, _(0.02)] }, rightForeArm: { rotation: [0, 0, _(-0.02)] } } },
      { duration: 0.30, easing: 'easeInOut', targets: { leftArm: { rotation: [_(0.04), _(0.04), _(-0.04)] }, rightArm: { rotation: [_(0.04), _(-0.04), _(0.04)] }, leftForeArm: { rotation: [_(0.06), 0, _(0.08)] }, rightForeArm: { rotation: [_(0.06), 0, _(-0.08)] } } },
      { duration: 0.50, easing: 'easeInOut', targets: { leftArm: { rotation: [_(0.04), _(0.04), _(-0.04)] }, rightArm: { rotation: [_(0.04), _(-0.04), _(0.04)] }, leftForeArm: { rotation: [_(0.06), 0, _(0.08)] }, rightForeArm: { rotation: [_(0.06), 0, _(-0.08)] } } },
      { duration: 0.22, easing: 'easeIn', targets: { leftArm: { rotation: [_(0.02), _(0.02), _(-0.02)] }, rightArm: { rotation: [_(0.02), _(-0.02), _(0.02)] }, leftForeArm: { rotation: [_(0.02), 0, _(0.03)] }, rightForeArm: { rotation: [_(0.02), 0, _(-0.03)] } } },
      { duration: 0.15, easing: 'easeOut', targets: { leftArm: { rotation: [0, 0, 0] }, rightArm: { rotation: [0, 0, 0] }, leftForeArm: { rotation: [0, 0, 0] }, rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },
}
