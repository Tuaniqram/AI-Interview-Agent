import { ReactNode, useState, useMemo } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';

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
    return <p className="text-sm text-muted py-8 text-center">{emptyMessage}</p>;
  }

  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full text-sm">
        <thead>
          <tr>
            {columns.map(col => (
              <th
                key={col.key}
                onClick={() => col.sortable !== false && handleSort(col.key)}
                className={`text-left text-xs font-medium text-secondary uppercase tracking-wider pb-3 ${col.className || ''} ${col.sortable !== false ? 'cursor-pointer select-none hover:text-primary' : ''}`}
              >
                <span className="inline-flex items-center gap-1">
                  {col.header}
                  {sortKey === col.key && (
                    sortDir === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map(row => (
            <tr
              key={String(row[keyField])}
              onClick={() => onRowClick?.(row)}
              className={`even:bg-hover/30 ${onRowClick ? 'cursor-pointer hover:bg-hover' : ''}`}
            >
              {columns.map(col => (
                <td key={col.key} className={`py-3 text-primary ${col.className || ''}`}>
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