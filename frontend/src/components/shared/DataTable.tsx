import { ReactNode } from 'react';

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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function DataTable<T extends Record<string, any>>({ columns, data, keyField, onRowClick, emptyMessage = 'No data', className = '' }: DataTableProps<T>) {
  if (data.length === 0) {
    return <p className="text-sm text-muted py-8 text-center">{emptyMessage}</p>;
  }

  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full text-sm">
        <thead>
          <tr>
            {columns.map(col => (
              <th key={col.key} className={`text-left text-xs font-medium text-secondary uppercase tracking-wider pb-3 ${col.className || ''}`}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map(row => (
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
