import type { GestureTypeName } from '../animator/gestures/GestureTypes'

const GESTURE_MAP: Record<string, GestureTypeName | null> = {
  none: null,
  nod: 'agreementNod',
  open_palm: 'openPalm',
  emphasis: 'singleHandEmphasis',
  thinking: 'questionEmphasis',
  listening: 'palmUpward',
}

export function mapGestureHint(hint: string): GestureTypeName | null {
  return GESTURE_MAP[hint] ?? null
}
