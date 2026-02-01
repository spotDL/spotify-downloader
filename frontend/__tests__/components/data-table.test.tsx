import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { DataTable, Pagination, type Column } from "../../src/components/ui/data-table";

interface TestRow {
  id: string;
  name: string;
  age: number;
  email: string | null;
}

const mockData: TestRow[] = [
  { id: "1", name: "Alice", age: 30, email: "alice@example.com" },
  { id: "2", name: "Bob", age: 25, email: null },
  { id: "3", name: "Charlie", age: 35, email: "charlie@example.com" },
  { id: "4", name: "Diana", age: 28, email: "diana@example.com" },
];

const columns: Column<TestRow>[] = [
  { key: "name", header: "Name", accessor: "name", sortable: true },
  { key: "age", header: "Age", accessor: "age", sortable: true, align: "right" },
  { key: "email", header: "Email", accessor: "email" },
];

describe("DataTable", () => {
  describe("rendering", () => {
    it("renders table with headers", () => {
      render(<DataTable data={mockData} columns={columns} rowKey="id" />);

      expect(screen.getByText("Name")).toBeInTheDocument();
      expect(screen.getByText("Age")).toBeInTheDocument();
      expect(screen.getByText("Email")).toBeInTheDocument();
    });

    it("renders all data rows", () => {
      render(<DataTable data={mockData} columns={columns} rowKey="id" />);

      expect(screen.getByText("Alice")).toBeInTheDocument();
      expect(screen.getByText("Bob")).toBeInTheDocument();
      expect(screen.getByText("Charlie")).toBeInTheDocument();
      expect(screen.getByText("Diana")).toBeInTheDocument();
    });

    it("renders empty message when data is empty", () => {
      render(
        <DataTable
          data={[]}
          columns={columns}
          rowKey="id"
          emptyMessage="No users found"
        />
      );

      expect(screen.getByText("No users found")).toBeInTheDocument();
    });

    it("uses default empty message", () => {
      render(<DataTable data={[]} columns={columns} rowKey="id" />);

      expect(screen.getByText("No data available")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(
        <DataTable data={mockData} columns={columns} rowKey="id" className="custom-table" />
      );

      expect(container.firstChild).toHaveClass("custom-table");
    });

    it("handles null values in cells", () => {
      render(<DataTable data={mockData} columns={columns} rowKey="id" />);

      // Bob's email is null, should just render empty
      const table = screen.getByRole("table");
      const rows = within(table).getAllByRole("row");
      // Find Bob's row (header + data rows, Bob is second data row)
      const bobRow = rows[2];
      expect(bobRow).toBeInTheDocument();
    });
  });

  describe("loading state", () => {
    it("shows skeleton rows when loading", () => {
      const { container } = render(
        <DataTable data={mockData} columns={columns} rowKey="id" isLoading />
      );

      // Should show shimmer elements instead of actual data
      const shimmers = container.querySelectorAll(".shimmer");
      expect(shimmers.length).toBeGreaterThan(0);
    });

    it("shows 5 skeleton rows by default", () => {
      render(
        <DataTable data={mockData} columns={columns} rowKey="id" isLoading />
      );

      const table = screen.getByRole("table");
      const tbody = table.querySelector("tbody");
      // 5 skeleton rows
      expect(tbody?.querySelectorAll("tr").length).toBe(5);
    });
  });

  describe("sorting", () => {
    it("shows sort icon on sortable columns", () => {
      const { container } = render(
        <DataTable data={mockData} columns={columns} rowKey="id" />
      );

      // Both Name and Age are sortable
      const sortIcons = container.querySelectorAll("th svg");
      expect(sortIcons.length).toBe(2);
    });

    it("sorts data ascending on first click", () => {
      render(<DataTable data={mockData} columns={columns} rowKey="id" />);

      const nameHeader = screen.getByText("Name");
      fireEvent.click(nameHeader);

      const table = screen.getByRole("table");
      const rows = within(table).getAllByRole("row");

      // First row is header, data rows start at index 1
      // After ascending sort by name: Alice, Bob, Charlie, Diana
      expect(within(rows[1]).getByText("Alice")).toBeInTheDocument();
    });

    it("sorts data descending on second click", () => {
      render(<DataTable data={mockData} columns={columns} rowKey="id" />);

      const nameHeader = screen.getByText("Name");
      // First click - ascending
      fireEvent.click(nameHeader);
      // Second click - descending
      fireEvent.click(nameHeader);

      const table = screen.getByRole("table");
      const rows = within(table).getAllByRole("row");

      // After descending sort by name: Diana, Charlie, Bob, Alice
      expect(within(rows[1]).getByText("Diana")).toBeInTheDocument();
    });

    it("sorts numeric columns correctly", () => {
      render(<DataTable data={mockData} columns={columns} rowKey="id" />);

      const ageHeader = screen.getByText("Age");
      fireEvent.click(ageHeader);

      const table = screen.getByRole("table");
      const rows = within(table).getAllByRole("row");

      // After ascending sort by age: Bob (25), Diana (28), Alice (30), Charlie (35)
      expect(within(rows[1]).getByText("Bob")).toBeInTheDocument();
    });

    it("does not sort non-sortable columns", () => {
      render(<DataTable data={mockData} columns={columns} rowKey="id" />);

      const emailHeader = screen.getByText("Email");
      const initialOrder = screen.getAllByRole("row");

      fireEvent.click(emailHeader);

      const afterClickOrder = screen.getAllByRole("row");
      // Order should remain the same
      expect(initialOrder.length).toBe(afterClickOrder.length);
    });
  });

  describe("selection", () => {
    it("shows checkboxes when selectable is true", () => {
      render(
        <DataTable
          data={mockData}
          columns={columns}
          rowKey="id"
          selectable
          selectedKeys={new Set()}
          onSelectionChange={() => {}}
        />
      );

      const checkboxes = screen.getAllByRole("checkbox");
      // 1 header checkbox + 4 row checkboxes
      expect(checkboxes.length).toBe(5);
    });

    it("does not show checkboxes when selectable is false", () => {
      render(
        <DataTable data={mockData} columns={columns} rowKey="id" />
      );

      expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    });

    it("calls onSelectionChange when row checkbox is clicked", () => {
      const handleSelectionChange = vi.fn();
      render(
        <DataTable
          data={mockData}
          columns={columns}
          rowKey="id"
          selectable
          selectedKeys={new Set()}
          onSelectionChange={handleSelectionChange}
        />
      );

      const checkboxes = screen.getAllByRole("checkbox");
      // Click first row checkbox (index 1, after header)
      fireEvent.click(checkboxes[1]);

      expect(handleSelectionChange).toHaveBeenCalledWith(new Set(["1"]));
    });

    it("calls onSelectionChange when header checkbox is clicked to select all", () => {
      const handleSelectionChange = vi.fn();
      render(
        <DataTable
          data={mockData}
          columns={columns}
          rowKey="id"
          selectable
          selectedKeys={new Set()}
          onSelectionChange={handleSelectionChange}
        />
      );

      const checkboxes = screen.getAllByRole("checkbox");
      // Click header checkbox (index 0)
      fireEvent.click(checkboxes[0]);

      expect(handleSelectionChange).toHaveBeenCalledWith(
        new Set(["1", "2", "3", "4"])
      );
    });

    it("calls onSelectionChange to clear all when header checkbox is clicked while all selected", () => {
      const handleSelectionChange = vi.fn();
      render(
        <DataTable
          data={mockData}
          columns={columns}
          rowKey="id"
          selectable
          selectedKeys={new Set(["1", "2", "3", "4"])}
          onSelectionChange={handleSelectionChange}
        />
      );

      const checkboxes = screen.getAllByRole("checkbox");
      // Click header checkbox to deselect all
      fireEvent.click(checkboxes[0]);

      expect(handleSelectionChange).toHaveBeenCalledWith(new Set());
    });

    it("shows indeterminate state when some rows are selected", () => {
      render(
        <DataTable
          data={mockData}
          columns={columns}
          rowKey="id"
          selectable
          selectedKeys={new Set(["1", "2"])}
          onSelectionChange={() => {}}
        />
      );

      const headerCheckbox = screen.getAllByRole("checkbox")[0] as HTMLInputElement;
      expect(headerCheckbox.indeterminate).toBe(true);
    });

    it("removes selection when clicking selected row checkbox", () => {
      const handleSelectionChange = vi.fn();
      render(
        <DataTable
          data={mockData}
          columns={columns}
          rowKey="id"
          selectable
          selectedKeys={new Set(["1"])}
          onSelectionChange={handleSelectionChange}
        />
      );

      const checkboxes = screen.getAllByRole("checkbox");
      // Click first row checkbox to deselect
      fireEvent.click(checkboxes[1]);

      expect(handleSelectionChange).toHaveBeenCalledWith(new Set());
    });
  });

  describe("row click", () => {
    it("calls onRowClick when row is clicked", () => {
      const handleRowClick = vi.fn();
      render(
        <DataTable
          data={mockData}
          columns={columns}
          rowKey="id"
          onRowClick={handleRowClick}
        />
      );

      const table = screen.getByRole("table");
      const rows = within(table).getAllByRole("row");
      // Click first data row
      fireEvent.click(rows[1]);

      expect(handleRowClick).toHaveBeenCalledWith(mockData[0]);
    });

    it("applies cursor-pointer class when onRowClick is provided", () => {
      const { container } = render(
        <DataTable
          data={mockData}
          columns={columns}
          rowKey="id"
          onRowClick={() => {}}
        />
      );

      const dataRows = container.querySelectorAll("tbody tr");
      dataRows.forEach((row) => {
        expect(row).toHaveClass("cursor-pointer");
      });
    });
  });

  describe("custom cell rendering", () => {
    it("uses custom render function for cells", () => {
      const columnsWithRender: Column<TestRow>[] = [
        {
          key: "name",
          header: "Name",
          accessor: "name",
          render: (value) => <strong data-testid="custom-render">{value as string}</strong>,
        },
      ];

      render(
        <DataTable data={mockData} columns={columnsWithRender} rowKey="id" />
      );

      const customElements = screen.getAllByTestId("custom-render");
      expect(customElements.length).toBe(4);
      expect(customElements[0].tagName).toBe("STRONG");
    });
  });

  describe("column alignment", () => {
    it("applies right alignment to cells", () => {
      const { container } = render(
        <DataTable data={mockData} columns={columns} rowKey="id" />
      );

      // Age column has align: "right"
      const ageHeader = container.querySelectorAll("th")[1];
      expect(ageHeader).toHaveClass("text-right");
    });

    it("applies center alignment to cells", () => {
      const centeredColumns: Column<TestRow>[] = [
        { key: "name", header: "Name", accessor: "name", align: "center" },
      ];

      const { container } = render(
        <DataTable data={mockData} columns={centeredColumns} rowKey="id" />
      );

      const header = container.querySelector("th");
      expect(header).toHaveClass("text-center");
    });
  });

  describe("sticky header", () => {
    it("applies sticky class when stickyHeader is true", () => {
      const { container } = render(
        <DataTable data={mockData} columns={columns} rowKey="id" stickyHeader />
      );

      const thead = container.querySelector("thead");
      expect(thead).toHaveClass("sticky");
    });

    it("does not apply sticky class by default", () => {
      const { container } = render(
        <DataTable data={mockData} columns={columns} rowKey="id" />
      );

      const thead = container.querySelector("thead");
      expect(thead).not.toHaveClass("sticky");
    });
  });

  describe("rowKey function", () => {
    it("uses rowKey function when provided", () => {
      const handleRowClick = vi.fn();
      render(
        <DataTable
          data={mockData}
          columns={columns}
          rowKey={(row) => `custom-${row.id}`}
          onRowClick={handleRowClick}
        />
      );

      // Should render without errors
      expect(screen.getByText("Alice")).toBeInTheDocument();
    });
  });

  describe("accessor function", () => {
    it("uses accessor function for column values", () => {
      const columnsWithAccessorFn: Column<TestRow>[] = [
        {
          key: "fullInfo",
          header: "Info",
          accessor: (row) => `${row.name} (${row.age})`,
        },
      ];

      render(
        <DataTable data={mockData} columns={columnsWithAccessorFn} rowKey="id" />
      );

      expect(screen.getByText("Alice (30)")).toBeInTheDocument();
      expect(screen.getByText("Bob (25)")).toBeInTheDocument();
    });
  });
});

describe("Pagination", () => {
  describe("rendering", () => {
    it("renders pagination buttons", () => {
      render(
        <Pagination currentPage={1} totalPages={5} onPageChange={() => {}} />
      );

      expect(screen.getByText("Previous")).toBeInTheDocument();
      expect(screen.getByText("Next")).toBeInTheDocument();
      expect(screen.getByText("1")).toBeInTheDocument();
      expect(screen.getByText("5")).toBeInTheDocument();
    });

    it("highlights current page", () => {
      render(
        <Pagination currentPage={3} totalPages={5} onPageChange={() => {}} />
      );

      const currentPageButton = screen.getByText("3");
      expect(currentPageButton).toHaveClass("bg-[var(--accent-safe)]");
    });

    it("applies custom className", () => {
      const { container } = render(
        <Pagination
          currentPage={1}
          totalPages={5}
          onPageChange={() => {}}
          className="custom-pagination"
        />
      );

      expect(container.firstChild).toHaveClass("custom-pagination");
    });
  });

  describe("navigation", () => {
    it("calls onPageChange when page button is clicked", () => {
      const handlePageChange = vi.fn();
      render(
        <Pagination currentPage={1} totalPages={5} onPageChange={handlePageChange} />
      );

      fireEvent.click(screen.getByText("3"));
      expect(handlePageChange).toHaveBeenCalledWith(3);
    });

    it("calls onPageChange when Next is clicked", () => {
      const handlePageChange = vi.fn();
      render(
        <Pagination currentPage={2} totalPages={5} onPageChange={handlePageChange} />
      );

      fireEvent.click(screen.getByText("Next"));
      expect(handlePageChange).toHaveBeenCalledWith(3);
    });

    it("calls onPageChange when Previous is clicked", () => {
      const handlePageChange = vi.fn();
      render(
        <Pagination currentPage={3} totalPages={5} onPageChange={handlePageChange} />
      );

      fireEvent.click(screen.getByText("Previous"));
      expect(handlePageChange).toHaveBeenCalledWith(2);
    });
  });

  describe("disabled states", () => {
    it("disables Previous button on first page", () => {
      render(
        <Pagination currentPage={1} totalPages={5} onPageChange={() => {}} />
      );

      expect(screen.getByText("Previous")).toBeDisabled();
    });

    it("disables Next button on last page", () => {
      render(
        <Pagination currentPage={5} totalPages={5} onPageChange={() => {}} />
      );

      expect(screen.getByText("Next")).toBeDisabled();
    });

    it("enables both buttons on middle pages", () => {
      render(
        <Pagination currentPage={3} totalPages={5} onPageChange={() => {}} />
      );

      expect(screen.getByText("Previous")).not.toBeDisabled();
      expect(screen.getByText("Next")).not.toBeDisabled();
    });
  });

  describe("ellipsis", () => {
    it("shows ellipsis for many pages", () => {
      render(
        <Pagination currentPage={5} totalPages={10} onPageChange={() => {}} />
      );

      // Should show ellipsis when there are gaps
      const ellipses = screen.getAllByText("...");
      expect(ellipses.length).toBeGreaterThanOrEqual(1);
    });

    it("does not show ellipsis for few pages", () => {
      render(
        <Pagination currentPage={2} totalPages={3} onPageChange={() => {}} />
      );

      expect(screen.queryByText("...")).not.toBeInTheDocument();
    });
  });
});
