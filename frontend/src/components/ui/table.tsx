import { forwardRef, type HTMLAttributes, type TdHTMLAttributes, type ThHTMLAttributes } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export const Table = forwardRef<
  HTMLTableElement,
  HTMLAttributes<HTMLTableElement>
>(({ className, ...props }, ref) => (
  <div className="w-full overflow-auto">
    <table
      ref={ref}
      className={twMerge(clsx("w-full caption-bottom text-sm", className))}
      {...props}
    />
  </div>
));

Table.displayName = "Table";

export const TableHeader = forwardRef<
  HTMLTableSectionElement,
  HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <thead
    ref={ref}
    className={twMerge(clsx("[&_tr]:border-b border-gray-700", className))}
    {...props}
  />
));

TableHeader.displayName = "TableHeader";

export const TableBody = forwardRef<
  HTMLTableSectionElement,
  HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tbody
    ref={ref}
    className={twMerge(clsx("[&_tr:last-child]:border-0", className))}
    {...props}
  />
));

TableBody.displayName = "TableBody";

export const TableFooter = forwardRef<
  HTMLTableSectionElement,
  HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tfoot
    ref={ref}
    className={twMerge(
      clsx("bg-gray-800 font-medium text-gray-300", className)
    )}
    {...props}
  />
));

TableFooter.displayName = "TableFooter";

export const TableRow = forwardRef<
  HTMLTableRowElement,
  HTMLAttributes<HTMLTableRowElement>
>(({ className, ...props }, ref) => (
  <tr
    ref={ref}
    className={twMerge(
      clsx(
        "border-b border-gray-700 transition-colors",
        "hover:bg-gray-800/50 data-[state=selected]:bg-gray-800",
        className
      )
    )}
    {...props}
  />
));

TableRow.displayName = "TableRow";

export const TableHead = forwardRef<
  HTMLTableCellElement,
  ThHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <th
    ref={ref}
    className={twMerge(
      clsx(
        "h-10 px-4 text-left align-middle font-medium text-gray-400",
        "[&:has([role=checkbox])]:pr-0",
        className
      )
    )}
    {...props}
  />
));

TableHead.displayName = "TableHead";

export const TableCell = forwardRef<
  HTMLTableCellElement,
  TdHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <td
    ref={ref}
    className={twMerge(
      clsx(
        "p-4 align-middle text-gray-300 [&:has([role=checkbox])]:pr-0",
        className
      )
    )}
    {...props}
  />
));

TableCell.displayName = "TableCell";

export const TableCaption = forwardRef<
  HTMLTableCaptionElement,
  HTMLAttributes<HTMLTableCaptionElement>
>(({ className, ...props }, ref) => (
  <caption
    ref={ref}
    className={twMerge(clsx("mt-4 text-sm text-gray-400", className))}
    {...props}
  />
));

TableCaption.displayName = "TableCaption";
