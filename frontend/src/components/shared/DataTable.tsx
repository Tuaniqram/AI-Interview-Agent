import { ReactNode, useState, useMemo, KeyboardEvent } from 'react';
import { ArrowUp, ArrowDown, ChevronsUpDown } from 'lucide-react';

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  className?: string;
  sortable?: boolean;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyField: string;
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
  className?: string;
}

type SortDir = 'asc' | 'desc';

/**
 * A dense, scannable table: a quiet header band, hairline row dividers, figures in tabular numerals.
 * Rows that open something are keyboard-reachable (Tab, then Enter).
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function DataTable<T extends Record<string, any>>({ columns, data, keyField, onRowClick, emptyMessage = 'No data', className = '' }: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  const sorted = useMemo(() => {
    if (!sortKey) return data;
    const col = columns.find(c => c.key === sortKey);
    if (!col) return data;

    return [...data].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];

      if (aVal == null) return 1;
      if (bVal == null) return -1;

      let cmp = 0;
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        cmp = aVal - bVal;
      } else if (typeof aVal === 'string' && typeof bVal === 'string') {
        cmp = aVal.localeCompare(bVal);
      } else {
        cmp = String(aVal).localeCompare(String(bVal));
      }

      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir, columns]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  if (data.length === 0) {
    return <p className="text-sm text-tertiary py-10 text-center">{emptyMessage}</p>;
  }

  const rowKey = (row: T) => (e: KeyboardEvent) => {
    if (e.key === 'Enter') { e.preventDefault(); onRowClick?.(row); }
  };

  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full text-[13px]">
        <thead>
          <tr className="border-b border-border">
            {columns.map(col => {
              const sortable = col.sortable !== false;
              const active = sortKey === col.key;
              return (
                <th
                  key={col.key}
                  scope="col"
                  aria-sort={active ? (sortDir === 'asc' ? 'ascending' : 'descending') : undefined}
                  className={`text-left font-medium text-tertiary h-9 px-3 first:pl-4 last:pr-4 whitespace-nowrap bg-subtle ${col.className || ''}`}
                >
                  {sortable ? (
                    <button
                      type="button"
                      onClick={() => handleSort(col.key)}
                      className={`group inline-flex items-center gap-1 -mx-1 px-1 rounded hover:text-primary ${active ? 'text-primary' : ''}`}
                    >
                      {col.header}
                      {active
                        ? (sortDir === 'asc' ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />)
                        : <ChevronsUpDown className="w-3 h-3 opacity-0 group-hover:opacity-60" />}
                    </button>
                  ) : col.header}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--divider)]">
          {sorted.map(row => (
            <tr
              key={String(row[keyField])}
              onClick={() => onRowClick?.(row)}
              onKeyDown={onRowClick ? rowKey(row) : undefined}
              tabIndex={onRowClick ? 0 : undefined}
              className={`${onRowClick ? 'cursor-pointer hover:bg-subtle focus-visible:bg-subtle focus-visible:outline-none' : ''}`}
            >
              {columns.map(col => (
                <td key={col.key} className={`h-11 px-3 first:pl-4 last:pr-4 text-primary ${col.className || ''}`}>
                  {col.render ? col.render(row) : String(row[col.key] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
