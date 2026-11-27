/** Small helpers shared by the Opportunity Hub pages, so a listing reads the same everywhere. */

export const MODE_LABEL: Record<string, string> = {
  typing: 'Typed answers',
  voice: 'Spoken answers',
  avatar: 'Video avatar',
};

export const modeLabel = (mode?: string | null) =>
  (mode && MODE_LABEL[mode]) || (mode ? mode.charAt(0).toUpperCase() + mode.slice(1) : '');

export const splitSkills = (s?: string | null) =>
  s?.split(',').map(x => x.trim()).filter(Boolean) ?? [];

const fmt = (d: string) =>
  new Date(d).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });

/** Where a listing stands on its dates: closed, closing soon, or just when it closes. */
export function closingInfo(expiresAt?: string | null): { text: string; tone: 'neutral' | 'soon' | 'closed' } | null {
  if (!expiresAt) return null;
  const ms = new Date(expiresAt).getTime() - Date.now();
  if (ms <= 0) return { text: 'Closed', tone: 'closed' };
  const days = Math.ceil(ms / 86400000);
  if (days <= 7) return { text: days === 1 ? 'Closes tomorrow' : `Closes in ${days} days`, tone: 'soon' };
  return { text: `Closes ${fmt(expiresAt)}`, tone: 'neutral' };
}

export const formatDate = fmt;
