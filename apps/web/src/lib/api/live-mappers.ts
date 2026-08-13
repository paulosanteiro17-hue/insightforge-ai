import type * as Backend from "@/lib/api/backend-contracts";
import type {
  AnalyticsMetric,
  AnalyticsPerformance,
  DashboardOverview,
  CustomerDetail,
  CustomerListItem,
  KpiMetric,
  MetricComparison,
  MetricValue,
  OrderDetail,
  OrderListItem,
  OrganizationSummary,
  PaginatedResponse,
  ProductDetail,
  ProductListItem,
  SessionView
} from "@/lib/api/contracts";

const chartColors = ["#0f9f8f", "#334766", "#ef765f", "#7d6db3", "#d29b3a"];

export function initials(value: string): string {
  return value
    .trim()
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function periodLabel(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC"
  }).format(new Date(`${value}T00:00:00Z`));
}

export function mapOrganization(
  organization: Backend.OrganizationSummaryView
): OrganizationSummary {
  return { ...organization };
}

export function mapSession(session: Backend.SessionView): SessionView {
  return {
    user: { ...session.user },
    session: { ...session.session },
    organizations: session.organizations.map(mapOrganization)
  };
}

export function mapPagination<T>(
  envelope: Backend.CollectionEnvelope<T>
): PaginatedResponse<T> {
  return {
    items: envelope.data,
    pagination: {
      page: envelope.meta.pagination.page,
      page_size: envelope.meta.pagination.page_size,
      total_items: envelope.meta.pagination.total,
      total_pages: envelope.meta.pagination.total_pages
    }
  };
}

export function mapOrder(order: Backend.OrderView): OrderListItem {
  return {
    id: order.id,
    order_number: order.order_number,
    status: order.status,
    customer: {
      ...order.customer,
      initials: initials(order.customer.name)
    },
    item_count: order.item_count,
    total_minor: order.total_minor,
    currency: order.currency,
    ordered_at: order.ordered_at
  };
}

export function mapOrderDetail(
  order: Backend.OrderView,
  etag: string
): OrderDetail {
  return {
    ...mapOrder(order),
    etag,
    external_id: order.external_id,
    source: order.source,
    subtotal_minor: order.subtotal_minor,
    discount_minor: order.discount_minor,
    tax_minor: order.tax_minor,
    items: (order.items ?? []).map((item) => ({ ...item })),
    status_history: (order.status_history ?? []).map((event) => ({ ...event }))
  };
}

export function mapCustomer(customer: Backend.CustomerView): CustomerListItem {
  return {
    ...customer,
    initials: initials(customer.name)
  };
}

export function mapCustomerDetail(
  customer: Backend.CustomerView,
  metrics: Backend.CustomerMetricsView,
  orders: Backend.CollectionEnvelope<Backend.OrderView>,
  etag: string
): CustomerDetail {
  return {
    ...mapCustomer(customer),
    etag,
    metrics: {
      spend_minor: metrics.spend_minor,
      order_count: metrics.order_count,
      average_order_value_minor: metrics.average_order_value_minor,
      last_order_at: metrics.last_order_at,
      recency_days: metrics.recency_days
    },
    recent_orders: orders.data.map(mapOrder)
  };
}

export function mapProduct(product: Backend.ProductView): ProductListItem {
  return { ...product };
}

export function mapProductDetail(
  product: Backend.ProductView,
  metrics: Backend.ProductMetricsView,
  range: ProductDetail["performance_range"],
  etag: string
): ProductDetail {
  return {
    ...mapProduct(product),
    etag,
    performance_range: range,
    currency: metrics.currency,
    comparison_range: metrics.comparison_range,
    current: metrics.current,
    previous: metrics.previous,
    units_change_percent: metrics.units_change_percent,
    revenue_change_percent: metrics.revenue_change_percent,
    performance: metrics.trend.map((point) => ({
      label: periodLabel(point.period_start),
      date: point.period_start,
      revenue_minor: point.eligible_revenue_minor,
      units_sold: point.units_sold
    }))
  };
}

function metricComparison(
  metric: Backend.ComparisonMetricView | undefined
): MetricComparison {
  const ratio = metric?.change_ratio ?? null;
  return {
    ratio,
    label: ratio === null ? "No comparable prior period" : "vs previous period",
    direction:
      metric?.change_status === "new"
        ? "new"
        : ratio === null || ratio === 0
          ? "flat"
          : ratio > 0
            ? "up"
            : "down",
    sentiment:
      ratio === null || ratio === 0
        ? "neutral"
        : ratio > 0
          ? "positive"
          : "negative"
  };
}

function valueFor(
  kind: MetricValue["kind"],
  value: number | null | undefined,
  currency: string
): MetricValue {
  if (kind === "money") {
    return { kind, amount_minor: value ?? 0, currency };
  }
  if (kind === "percentage") return { kind, ratio: value ?? 0 };
  return { kind, value: value ?? 0 };
}

function kpi(
  snapshot: Backend.AnalyticsView,
  key: string,
  id: KpiMetric["id"],
  label: string,
  kind: MetricValue["kind"],
  supportingLabel: string
): KpiMetric {
  const metric = snapshot.metrics[key];
  return {
    id,
    label,
    value: valueFor(kind, metric?.value, snapshot.currency),
    comparison: metricComparison(metric),
    supporting_label: supportingLabel
  };
}

function analyticsMetric(
  snapshot: Backend.AnalyticsView,
  key: string,
  label: string,
  kind: MetricValue["kind"],
  context: string
): AnalyticsMetric {
  const metric = snapshot.metrics[key];
  return {
    id: key,
    label,
    value: valueFor(kind, metric?.value, snapshot.currency),
    change_ratio: metric?.change_ratio ?? 0,
    context:
      metric?.change_ratio === null || metric?.change_ratio === undefined
        ? `${context} No comparable prior period is available.`
        : context
  };
}

export function mapDashboard(
  organizationId: string,
  range: DashboardOverview["range"],
  snapshot: Backend.AnalyticsView
): DashboardOverview {
  const maximumProductRevenue = Math.max(
    1,
    ...snapshot.products.map((product) => product.revenue_minor)
  );
  return {
    organization_id: organizationId,
    data_availability: snapshot.data_availability,
    range,
    comparison_range: snapshot.comparison_range
      ? `${snapshot.comparison_range.start}/${snapshot.comparison_range.end}`
      : "none",
    granularity: snapshot.granularity,
    time_zone: snapshot.time_zone,
    currency: snapshot.currency,
    metric_version: snapshot.metric_version,
    source_revision: String(snapshot.source_revision),
    generated_at: snapshot.generated_at,
    kpis: [
      kpi(
        snapshot,
        "revenue_minor",
        "total_revenue",
        "Revenue",
        "money",
        "Eligible order revenue"
      ),
      kpi(
        snapshot,
        "order_count",
        "orders",
        "Orders",
        "integer",
        "Eligible orders"
      ),
      kpi(
        snapshot,
        "customers",
        "customers",
        "Customers",
        "integer",
        "Customers with activity"
      ),
      kpi(
        snapshot,
        "average_order_value_minor",
        "average_order_value",
        "Average order value",
        "money",
        "Across eligible orders"
      )
    ],
    revenue: snapshot.revenue_series.map((point) => ({
      label: periodLabel(point.period_start),
      date: point.period_start,
      revenue_minor: point.revenue_minor
      // The analytics contract currently exposes only the current time series.
    })),
    acquisition: snapshot.customer_acquisition.map((point) => ({
      label: periodLabel(point.period_start),
      customers: point.new_customers
    })),
    category_revenue: snapshot.categories.map((category, index) => ({
      name: category.label,
      revenue_minor: category.revenue_minor,
      share_ratio: category.share_ratio ?? 0,
      color: chartColors[index % chartColors.length] ?? chartColors[0]!
    })),
    top_products: snapshot.products.map((product) => ({
      name: product.label,
      revenue_minor: product.revenue_minor,
      units_sold: product.units,
      change_ratio: null,
      relative_ratio: product.revenue_minor / maximumProductRevenue
    })),
    order_statuses: snapshot.order_statuses.map((status, index) => ({
      status: status.label as Backend.OrderStatus,
      count: status.count,
      share_ratio: status.share_ratio ?? 0,
      color: chartColors[index % chartColors.length] ?? chartColors[0]!
    })),
    order_status_total: snapshot.order_statuses.reduce(
      (total, status) => total + status.count,
      0
    ),
    recent_transactions: snapshot.recent_transactions.map((transaction) => ({
      ...transaction,
      customer_initials: initials(transaction.customer_name)
    })),
    weekly_summary: null
  };
}

export function mapAnalyticsPerformance(
  organizationId: string,
  range: AnalyticsPerformance["range"],
  snapshot: Backend.AnalyticsView
): AnalyticsPerformance {
  return {
    organization_id: organizationId,
    data_availability: snapshot.data_availability,
    range,
    comparison_range: snapshot.comparison_range
      ? `${snapshot.comparison_range.start}/${snapshot.comparison_range.end}`
      : "none",
    granularity: snapshot.granularity,
    time_zone: snapshot.time_zone,
    currency: snapshot.currency,
    metric_version: snapshot.metric_version,
    source_revision: String(snapshot.source_revision),
    generated_at: snapshot.generated_at,
    metrics: [
      analyticsMetric(
        snapshot,
        "revenue_minor",
        "Revenue",
        "money",
        "Eligible order revenue."
      ),
      analyticsMetric(
        snapshot,
        "order_count",
        "Orders",
        "integer",
        "Orders in the selected range."
      ),
      analyticsMetric(
        snapshot,
        "customers",
        "Customers",
        "integer",
        "Customers with activity."
      ),
      analyticsMetric(
        snapshot,
        "new_customers",
        "New customers",
        "integer",
        "Customers acquired in range."
      ),
      analyticsMetric(
        snapshot,
        "average_order_value_minor",
        "Average order value",
        "money",
        "Average across eligible orders."
      ),
      analyticsMetric(
        snapshot,
        "repeat_rate",
        "Repeat rate",
        "percentage",
        "Share of repeat customers."
      )
    ],
    sales_trend: snapshot.revenue_series.map((point) => ({
      label: periodLabel(point.period_start),
      date: point.period_start,
      revenue_minor: point.revenue_minor,
      order_count: point.order_count,
      average_order_value_minor:
        point.order_count > 0
          ? Math.round(point.revenue_minor / point.order_count)
          : 0
    })),
    customer_trend: snapshot.customer_acquisition.map((point) => ({
      label: periodLabel(point.period_start),
      date: point.period_start,
      new_customers: point.new_customers
    })),
    product_mix: snapshot.products.map((product, index) => ({
      name: product.label,
      revenue_minor: product.revenue_minor,
      share_ratio: product.share_ratio ?? 0,
      color: chartColors[index % chartColors.length] ?? chartColors[0]!
    })),
    order_statuses: snapshot.order_statuses.map((status, index) => ({
      status: status.label as Backend.OrderStatus,
      count: status.count,
      share_ratio: status.share_ratio ?? 0,
      color: chartColors[index % chartColors.length] ?? chartColors[0]!
    }))
  };
}
