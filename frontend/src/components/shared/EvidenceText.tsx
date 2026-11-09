import type { ReactNode } from 'react';

const escapeRegExp = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/**
 * Typographic look-alikes folded to plain characters, one character for one, so positions in the folded text are
 * positions in the original. Models often write a non-breaking hyphen or a curly quote where the answer has a
 * plain one; that must not stop a quote from matching.
 */
const fold = (text: string) =>
  text
    .replace(/[‐-―−]/g, '-')
    .replace(/[‘’]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/[   ]/g, ' ');

/** Where `quote` appears in `text`, ignoring case, spacing and typographic look-alikes; `null` if it does not appear. */
function locate(text: string, quote: string): [number, number] | null {
  const words = fold(quote).trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return null;
  const match = new RegExp(words.map(escapeRegExp).join('\\s+'), 'i').exec(fold(text));
  return match ? [match.index, match.index + match[0].length] : null;
}

/**
 * A candidate's answer with the words a score rests on highlighted (`.evidence-mark`). A quote is highlighted only
 * where it appears word for word in the answer; anything the model merely paraphrased is left unmarked, so the
 * highlight never presents a paraphrase as a quotation.
 */
export function EvidenceText({ text, quotes }: { text: string; quotes: string[] }) {
  const spans = quotes
    .map(q => locate(text, q))
    .filter((s): s is [number, number] => s !== null)
    .sort((a, b) => a[0] - b[0]);

  // Drop spans that overlap an earlier one.
  const merged: Array<[number, number]> = [];
  for (const span of spans) {
    const last = merged[merged.length - 1];
    if (last && span[0] < last[1]) {
      last[1] = Math.max(last[1], span[1]);
    } else {
      merged.push([span[0], span[1]]);
    }
  }

  const nodes: ReactNode[] = [];
  let cursor = 0;
  merged.forEach(([start, end], i) => {
    if (start > cursor) nodes.push(text.slice(cursor, start));
    nodes.push(<mark key={i} className="evidence-mark">{text.slice(start, end)}</mark>);
    cursor = end;
  });
  if (cursor < text.length) nodes.push(text.slice(cursor));
  return <>{nodes}</>;
}

/** How many of the quotes appear word for word in the text (used to decide whether to show the legend). */
export function countHighlights(text: string, quotes: string[]): number {
  return quotes.filter(q => locate(text, q) !== null).length;
}
