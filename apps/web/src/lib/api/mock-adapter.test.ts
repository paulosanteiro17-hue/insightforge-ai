import { describe, expect, it } from "vitest";
import { insightForgeApi } from "@/lib/api/mock-adapter";
import { mockOrganizations } from "@/lib/api/mock-fixtures";

describe("mock analytics adapter", () => {
  it("keeps server-shaped dashboard totals coherent across every supported range", async () => {
    const organization = mockOrganizations[0];
    expect(organization).toBeDefined();

    for (const range of ["7d", "30d", "90d", "year_to_date"] as const) {
      const overview = await insightForgeApi.analytics.getOverview(
        organization!.id,
        range
      );
      const orderMetric = overview.kpis.find(
        (metric) => metric.id === "orders"
      );
      const revenueMetric = overview.kpis.find(
        (metric) => metric.id === "total_revenue"
      );
      const categoryTotal = overview.category_revenue.reduce(
        (total, category) => total + category.revenue_minor,
        0
      );

      expect(orderMetric?.value).toEqual({
        kind: "integer",
        value: overview.order_status_total
      });
      expect(revenueMetric?.value.kind).toBe("money");
      if (revenueMetric?.value.kind === "money") {
        expect(
          Math.abs(categoryTotal - revenueMetric.value.amount_minor)
        ).toBeLessThanOrEqual(4);
      }
      expect(overview.organization_id).toBe(organization!.id);
      expect(overview.range).toBe(range);
    }
  });

  it("applies server-shaped filters, sorting, pagination, and detail lookup", async () => {
    const organization = mockOrganizations[0]!;
    const orders = await insightForgeApi.orders.list(organization.id, {
      search: "Cedar",
      status: "completed",
      sort: "total_desc",
      page: 1,
      page_size: 1,
      range: "year_to_date"
    });

    expect(orders.pagination.page_size).toBe(1);
    expect(orders.pagination.total_items).toBeGreaterThan(0);
    expect(orders.items[0]?.customer.name).toBe("Avery Morgan");

    const detail = await insightForgeApi.orders.getById(
      organization.id,
      orders.items[0]!.id
    );
    expect(detail.items.length).toBeGreaterThan(0);
    expect(detail.total_minor).toBe(
      detail.subtotal_minor - detail.discount_minor + detail.tax_minor
    );
  });
});
