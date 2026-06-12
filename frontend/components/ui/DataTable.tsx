import type { ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: ReactNode;
  /** Numeric columns are right-aligned and use tabular figures. */
  numeric?: boolean;
  render: (row: T, index: number) => ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey?: (row: T, index: number) => string | number;
  /** Optional extra classes per row (e.g. to highlight a pinned row). */
  rowClassName?: (row: T, index: number) => string;
  className?: string;
}

export default function DataTable<T>({
  columns,
  rows,
  rowKey,
  rowClassName,
  className = "",
}: DataTableProps<T>) {
  return (
    <div className={`scroll-x ${className}`}>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-line">
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                className={`px-3 py-2 text-xs font-medium text-ink-muted ${
                  col.numeric ? "text-right" : "text-left"
                }`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr
              key={rowKey ? rowKey(row, index) : index}
              className={`border-b border-line transition-colors duration-150 last:border-b-0 hover:bg-brand-soft ${
                rowClassName ? rowClassName(row, index) : ""
              }`}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={`px-3 py-2 ${
                    col.numeric ? "text-right tabular-nums" : "text-left"
                  }`}
                >
                  {col.render(row, index)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
