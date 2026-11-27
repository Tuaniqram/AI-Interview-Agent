import { Plus, X } from 'lucide-react';
import { Select } from '../shared/Select';
import type { CompetencyDef } from '../../types/scorecard';

const numCls = 'h-8 w-full px-2 text-[13px] text-right tabular bg-input text-primary rounded-md border border-[var(--border-strong)] shadow-sm focus:border-[var(--action-primary)] focus:outline-none focus:ring-[3px] focus:ring-[var(--focus-ring)] [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none';

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

interface CompetencyRowsProps {
  rows: CompetencyDef[];
  onChange: (rows: CompetencyDef[]) => void;
  categories: string[];
  /** Weight range: each page keeps the range its backend expects. */
  weight: { min: number; max: number; step: number };
  /** Show the highest achievable score column (scorecards). */
  maxScore?: { min: number; max: number };
  blank: CompetencyDef;
}

/** Competencies as an editable table: name, category, weight and (optionally) top score per row. */
export function CompetencyRows({ rows, onChange, categories, weight, maxScore, blank }: CompetencyRowsProps) {
  const cols = maxScore
    ? 'grid-cols-[minmax(0,1fr)_8.5rem_4.5rem_4.5rem_2rem]'
    : 'grid-cols-[minmax(0,1fr)_8.5rem_4.5rem_2rem]';

  const update = (i: number, field: keyof CompetencyDef, value: string | number) => {
    const next = rows.map((c, idx) => (idx === i ? { ...c, [field]: value } : c));
    // A new competency's id follows its name until it is saved.
    if (field === 'name' && !rows[i].id) next[i] = { ...next[i], id: String(value).toLowerCase().trim().replace(/\s+/g, '_') };
    onChange(next);
  };

  return (
    <div>
      {rows.length > 0 && (
        <div className={`grid ${cols} gap-2 px-0.5 pb-1.5 text-xs text-tertiary`} aria-hidden>
          <span>Competency</span>
          <span>Category</span>
          <span className="text-right">Weight</span>
          {maxScore && <span className="text-right">Top score</span>}
          <span />
        </div>
      )}
      <ul className="space-y-2">
        {rows.map((c, i) => (
          <li key={i} className={`grid ${cols} gap-2 items-center`}>
            <input
              type="text"
              value={c.name}
              onChange={e => update(i, 'name', e.target.value)}
              placeholder="e.g. System design"
              aria-label={`Competency ${i + 1} name`}
              className="h-8 w-full px-3 text-[13px] bg-input text-primary rounded-md border border-[var(--border-strong)] shadow-sm focus:border-[var(--action-primary)] focus:outline-none focus:ring-[3px] focus:ring-[var(--focus-ring)] placeholder:text-tertiary"
            />
            <Select value={c.category} onChange={v => update(i, 'category', v)} options={categories.map(cat => ({ value: cat, label: cap(cat) }))} />
            <input
              type="number" min={weight.min} max={weight.max} step={weight.step}
              value={c.weight}
              onChange={e => update(i, 'weight', Number(e.target.value))}
              aria-label={`Competency ${i + 1} weight`}
              className={numCls}
            />
            {maxScore && (
              <input
                type="number" min={maxScore.min} max={maxScore.max} step={1}
                value={c.max_score}
                onChange={e => update(i, 'max_score', Number(e.target.value))}
                aria-label={`Competency ${i + 1} top score`}
                className={numCls}
              />
            )}
            <button
              type="button"
              onClick={() => onChange(rows.filter((_, idx) => idx !== i))}
              className="h-8 w-8 flex items-center justify-center rounded-md text-tertiary hover:text-error-text hover:bg-hover"
              aria-label={`Remove ${c.name || `competency ${i + 1}`}`}
            >
              <X className="w-4 h-4" />
            </button>
          </li>
        ))}
      </ul>
      <button
        type="button"
        onClick={() => onChange([...rows, { ...blank }])}
        className="mt-3 inline-flex items-center gap-1.5 h-8 px-2.5 -ml-2.5 rounded-md text-[13px] font-medium text-action-primary hover:bg-hover"
      >
        <Plus className="w-4 h-4" /> Add competency
      </button>
    </div>
  );
}
