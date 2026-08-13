import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { OrdersTable } from "@/components/sales/orders-table";
import { mockOrders } from "@/lib/api/mock-fixtures";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/app/northstar-commerce/sales",
  useSearchParams: () => new URLSearchParams()
}));

describe("OrdersTable", () => {
  it("exposes table and mobile-card links to the same order detail", () => {
    const order = mockOrders[0];
    expect(order).toBeDefined();
    render(
      <OrdersTable
        orders={[order!]}
        pagination={{ page: 1, page_size: 6, total_items: 1, total_pages: 1 }}
        organizationSlug="northstar-commerce"
      />
    );

    expect(
      screen.getByRole("table", {
        name: "Orders matching the selected filters"
      })
    ).toBeInTheDocument();
    const detailLinks = screen.getAllByRole("link", {
      name: order!.order_number
    });
    expect(detailLinks).toHaveLength(2);
    detailLinks.forEach((link) =>
      expect(link).toHaveAttribute(
        "href",
        `/app/northstar-commerce/sales/orders/${order!.id}`
      )
    );
    expect(screen.getAllByText("Completed").length).toBeGreaterThan(0);
  });
});
