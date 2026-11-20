/** Turn internal names and records into text a person can read. Pure functions, no dependencies. */

const capitalize = (text: string) => (text ? text.charAt(0).toUpperCase() + text.slice(1) : text);

/** "candidate_feedback" -> "Candidate feedback". */
export function humanizeName(name: string): string {
  return capitalize(name.replace(/[_-]+/g, ' ').trim());
}

/** "marketplace.create" -> "Create marketplace"; anything without a dot is just humanised. */
export function humanizeAction(action: string): string {
  const parts = action.split('.').filter(Boolean);
  if (parts.length === 2) return `${capitalize(parts[1])} ${parts[0].replace(/[_-]+/g, ' ')}`;
  return humanizeName(action);
}

/** A short display form of one value from an audit record. */
function shortValue(value: unknown): string {
  const text = typeof value === 'string' ? value : JSON.stringify(value);
  return text.length > 70 ? `${text.slice(0, 67)}...` : text;
}

/**
 * An audit record's details as "title: Backend Engineer · interview mode: typing". Ids and empty values are left
 * out: they mean nothing to a reader (the record's own id is shown separately).
 */
export function summarizeDetails(details: Record<string, unknown> | string | null | undefined): string {
  if (!details) return '';
  if (typeof details === 'string') {
    try {
      const parsed = JSON.parse(details);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return summarizeDetails(parsed as Record<string, unknown>);
    } catch {
      /* not JSON: show it as written */
    }
    return shortValue(details);
  }
  return Object.entries(details)
    .filter(([key, value]) => value !== null && value !== '' && !/(^|_)id$/i.test(key))
    .map(([key, value]) => `${key.replace(/_/g, ' ')}: ${shortValue(value)}`)
    .join(' · ');
}
