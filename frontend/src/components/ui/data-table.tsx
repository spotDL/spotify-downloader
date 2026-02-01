import { useState, useMemo } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

// Sort icons
const SortIcon = ({ direction }: { direction: "asc" | "desc" | null }) => (
  <svg className="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    {direction === "asc" ? (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
    ) : direction === "desc" ? (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    ) : (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
    )}
  </svg>
);

// Checkbox component
const Checkbox = ({
  checked,
  indeterminate,
  onChange,
}: {
  checked: boolean;
  indeterminate?: boolean;
  onChange: (checked: boolean) => void;
}) => (
  <input
    type="checkbox"
    checked={checked}
    ref={(el) => {
      if (el) el.indeterminate = indeterminate ?? false;
    }}
    onChange={(e) => onChange(e.target.checked)}
    className={clsx(
      "w-4 h-4 rounded",
      "border-2 border-[var(--color-border)]",
      "text-[var(--accent-safe)]",
      "focus:ring-2 focus:ring-[var(--accent-safe)] focus:ring-offset-2 focus:ring-offset-[var(--bg-panel)]",
      "bg-transparent"
    )}
  />
);

export interface Column<T> {
  /** Unique key for the column */
  key: string;
  /** Header label */
  header: string;
  /** Accessor function or key path */
  accessor: keyof T | ((row: T) => React.ReactNode);
  /** Whether the column is sortable */
  sortable?: boolean;
  /** Custom cell renderer */
  render?: (value: unknown, row: T) => React.ReactNode;
  /** Column width (Tailwind class) */
  width?: string;
  /** Text alignment */
  align?: "left" | "center" | "right";
}

export interface DataTableProps<T> {
  /** Data rows */
  data: T[];
  /** Column definitions */
  columns: Column<T>[];
  /** Unique key for each row */
  rowKey: keyof T | ((row: T) => string);
  /** Enable row selection */
  selectable?: boolean;
  /** Selected row keys */
  selectedKeys?: Set<string>;
  /** Selection change callback */
  onSelectionChange?: (selectedKeys: Set<string>) => void;
  /** Row click handler */
  onRowClick?: (row: T) => void;
  /** Loading state */
  isLoading?: boolean;
  /** Empty state message */
  emptyMessage?: string;
  /** Additional class names */
  className?: string;
  /** Sticky header */
  stickyHeader?: boolean;
}

export function DataTable<T>({
  data,
  columns,
  rowKey,
  selectable = false,
  selectedKeys = new Set(),
  onSelectionChange,
  onRowClick,
  isLoading = false,
  emptyMessage = "No data available",
  className,
  stickyHeader = false,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  // Get row key
  const getRowKey = (row: T): string => {
    if (typeof rowKey === "function") {
      return rowKey(row);
    }
    return String(row[rowKey]);
  };

  // Get cell value
  const getCellValue = (row: T, column: Column<T>): unknown => {
    if (typeof column.accessor === "function") {
      return column.accessor(row);
    }
    return row[column.accessor];
  };

  // Sorted data
  const sortedData = useMemo(() => {
    if (!sortKey) return data;

    const column = columns.find((c) => c.key === sortKey);
    if (!column) return data;

    return [...data].sort((a, b) => {
      const aVal = getCellValue(a, column);
      const bVal = getCellValue(b, column);

      if (aVal === bVal) return 0;
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;

      const comparison = aVal < bVal ? -1 : 1;
      return sortDirection === "asc" ? comparison : -comparison;
    });
  }, [data, columns, sortKey, sortDirection]);

  // Handle sort
  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDirection((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDirection("asc");
    }
  };

  // Handle select all
  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      onSelectionChange?.(new Set(data.map((row) => getRowKey(row))));
    } else {
      onSelectionChange?.(new Set());
    }
  };

  // Handle row select
  const handleRowSelect = (key: string, checked: boolean) => {
    const newSelection = new Set(selectedKeys);
    if (checked) {
      newSelection.add(key);
    } else {
      newSelection.delete(key);
    }
    onSelectionChange?.(newSelection);
  };

  const allSelected = data.length > 0 && selectedKeys.size === data.length;
  const someSelected = selectedKeys.size > 0 && selectedKeys.size < data.length;

  return (
    <div className={twMerge("overflow-auto", className)}>
      <table className="data-table w-full">
        <thead className={clsx(stickyHeader && "sticky top-0 z-10 bg-[var(--bg-panel)]")}>
          <tr>
            {selectable && (
              <th className="w-12 px-4 py-3">
                <Checkbox
                  checked={allSelected}
                  indeterminate={someSelected}
                  onChange={handleSelectAll}
                />
              </th>
            )}
            {columns.map((column) => (
              <th
                key={column.key}
                className={clsx(
                  "px-4 py-3 text-xs font-semibold uppercase tracking-wider",
                  "text-[var(--color-text-muted)]",
                  "border-b border-[var(--color-border)]",
                  column.width,
                  column.align === "center" && "text-center",
                  column.align === "right" && "text-right",
                  column.sortable && "cursor-pointer select-none hover:text-[var(--color-text-primary)]"
                )}
                onClick={() => column.sortable && handleSort(column.key)}
              >
                <div
                  className={clsx(
                    "inline-flex items-center",
                    column.align === "center" && "justify-center",
                    column.align === "right" && "justify-end"
                  )}
                >
                  {column.header}
                  {column.sortable && (
                    <SortIcon
                      direction={sortKey === column.key ? sortDirection : null}
                    />
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            // Loading skeleton rows
            Array.from({ length: 5 }).map((_, i) => (
              <tr key={`skeleton-${i}`}>
                {selectable && (
                  <td className="px-4 py-4">
                    <div className="w-4 h-4 rounded shimmer" />
                  </td>
                )}
                {columns.map((column) => (
                  <td key={column.key} className="px-4 py-4">
                    <div className="h-4 rounded shimmer" style={{ width: "60%" }} />
                  </td>
                ))}
              </tr>
            ))
          ) : sortedData.length === 0 ? (
            // Empty state
            <tr>
              <td
                colSpan={columns.length + (selectable ? 1 : 0)}
                className="px-4 py-12 text-center text-[var(--color-text-muted)]"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            // Data rows
            sortedData.map((row) => {
              const key = getRowKey(row);
              const isSelected = selectedKeys.has(key);

              return (
                <tr
                  key={key}
                  className={clsx(
                    "transition-colors duration-150",
                    isSelected && "bg-[var(--accent-safe)]/5",
                    onRowClick && "cursor-pointer",
                    "hover:bg-[var(--bg-hover)]"
                  )}
                  onClick={() => onRowClick?.(row)}
                >
                  {selectable && (
                    <td
                      className="px-4 py-4"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Checkbox
                        checked={isSelected}
                        onChange={(checked) => handleRowSelect(key, checked)}
                      />
                    </td>
                  )}
                  {columns.map((column) => {
                    const value = getCellValue(row, column);
                    const rendered = column.render
                      ? column.render(value, row)
                      : (value as React.ReactNode);

                    return (
                      <td
                        key={column.key}
                        className={clsx(
                          "px-4 py-4 border-b border-[var(--color-border-subtle)]",
                          column.align === "center" && "text-center",
                          column.align === "right" && "text-right"
                        )}
                      >
                        {rendered}
                      </td>
                    );
                  })}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Pagination component for DataTable
 */
export interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  className?: string;
}

export function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  className,
}: PaginationProps) {
  const pages = useMemo(() => {
    const result: (number | "...")[] = [];
    const delta = 2;

    for (let i = 1; i <= totalPages; i++) {
      if (
        i === 1 ||
        i === totalPages ||
        (i >= currentPage - delta && i <= currentPage + delta)
      ) {
        result.push(i);
      } else if (result[result.length - 1] !== "...") {
        result.push("...");
      }
    }

    return result;
  }, [currentPage, totalPages]);

  return (
    <div className={twMerge("flex items-center justify-center gap-1", className)}>
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className={clsx(
          "px-3 py-1.5 rounded-lg text-sm",
          "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]",
          "hover:bg-[var(--bg-hover)]",
          "disabled:opacity-50 disabled:cursor-not-allowed"
        )}
      >
        Previous
      </button>

      {pages.map((page, i) =>
        page === "..." ? (
          <span key={`ellipsis-${i}`} className="px-2 text-[var(--color-text-muted)]">
            ...
          </span>
        ) : (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            className={clsx(
              "w-8 h-8 rounded-lg text-sm font-medium",
              "transition-colors duration-150",
              page === currentPage
                ? "bg-[var(--accent-safe)] text-white"
                : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--bg-hover)]"
            )}
          >
            {page}
          </button>
        )
      )}

      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className={clsx(
          "px-3 py-1.5 rounded-lg text-sm",
          "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]",
          "hover:bg-[var(--bg-hover)]",
          "disabled:opacity-50 disabled:cursor-not-allowed"
        )}
      >
        Next
      </button>
    </div>
  );
}

export default DataTable;
