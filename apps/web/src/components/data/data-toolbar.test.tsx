import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DataToolbar } from "@/components/data/data-toolbar";

const navigation = vi.hoisted(() => ({
  replace: vi.fn(),
  params: new URLSearchParams("status=paid&page=3")
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: navigation.replace }),
  usePathname: () => "/app/northstar-commerce/sales",
  useSearchParams: () => navigation.params
}));

describe("DataToolbar", () => {
  beforeEach(() => navigation.replace.mockReset());

  it("writes search and filter state to canonical URL parameters", async () => {
    const user = userEvent.setup();
    render(
      <DataToolbar
        searchLabel="Search orders"
        searchPlaceholder="Search order number or customer"
        filters={[
          {
            param: "status",
            label: "Order status",
            allLabel: "All statuses",
            options: [
              { value: "paid", label: "Paid" },
              { value: "completed", label: "Completed" }
            ]
          }
        ]}
        sortOptions={[
          { value: "ordered_at_desc", label: "Newest first" },
          { value: "total_desc", label: "Highest total" }
        ]}
      />
    );

    await user.type(
      screen.getByRole("searchbox", { name: "Search orders" }),
      "NS-84291"
    );
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(navigation.replace).toHaveBeenCalledWith(
      "/app/northstar-commerce/sales?status=paid&page=1&q=NS-84291",
      { scroll: false }
    );

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Order status" }),
      "completed"
    );
    expect(navigation.replace).toHaveBeenLastCalledWith(
      "/app/northstar-commerce/sales?status=completed&page=1",
      { scroll: false }
    );
  });
});
