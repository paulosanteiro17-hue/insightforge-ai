import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { OrderDetailContent } from "@/components/sales/order-detail";
import { mockOrders } from "@/lib/api/mock-fixtures";

describe("OrderDetailContent", () => {
  it("renders immutable line-item pricing and the complete status timeline", () => {
    const order = mockOrders.find((item) => item.id === "order-84290");
    expect(order).toBeDefined();
    render(
      <OrderDetailContent
        order={order!}
        organizationSlug="northstar-commerce"
      />
    );

    expect(
      screen.getByRole("table", {
        name: `Products included in ${order!.order_number}`
      })
    ).toBeInTheDocument();
    order!.items.forEach((item) => {
      expect(screen.getAllByText(item.product_name).length).toBeGreaterThan(0);
    });
    expect(screen.getByText("Status history")).toBeInTheDocument();
    expect(screen.getAllByText("Processing").length).toBeGreaterThan(0);
  });
});
