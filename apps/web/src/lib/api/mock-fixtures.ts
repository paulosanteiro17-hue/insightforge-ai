import type {
  AcquisitionPoint,
  AnalyticsPerformance,
  AnalyticsRange,
  CategoryRevenue,
  CustomerDetail,
  CustomerListItem,
  DashboardOverview,
  KpiMetric,
  OrderDetail,
  OrderLineItem,
  OrderListItem,
  OrderStatus,
  OrderStatusDatum,
  OrganizationSummary,
  ProductDetail,
  ProductListItem,
  ProductPerformance,
  RecentTransaction,
  SessionView,
  WeeklySummary
} from "@/lib/api/contracts";

export const mockOrganizations: OrganizationSummary[] = [
  {
    id: "01914d2e-50a3-7c44-a9bc-5f98cf7bf803",
    name: "Northstar Commerce",
    slug: "northstar-commerce",
    role: "owner",
    status: "active",
    onboarding_state: "complete",
    reporting_currency: "USD",
    timezone: "America/New_York",
    is_demo: true,
    demo_expires_at: "2026-08-11T21:30:00Z"
  },
  {
    id: "01914d2e-50a3-7c44-a9bc-5f98cf7bf804",
    name: "Harbor & Pine",
    slug: "harbor-and-pine",
    role: "admin",
    status: "active",
    onboarding_state: "complete",
    reporting_currency: "USD",
    timezone: "America/Chicago",
    is_demo: true,
    demo_expires_at: "2026-08-11T21:30:00Z"
  }
];

export const mockSession: SessionView = {
  user: {
    id: "01914d2e-50a3-7c44-a9bc-5f98cf7bf810",
    display_name: "Jordan Blake",
    email: "jordan@northstar.example",
    status: "active",
    email_verified_at: "2026-07-01T12:00:00Z",
    locale: "en-US",
    time_zone: "America/New_York",
    created_at: "2026-07-01T12:00:00Z"
  },
  session: {
    id: "01914d2e-50a3-7c44-a9bc-5f98cf7bf811",
    is_demo: true,
    idle_expires_at: "2026-08-10T21:30:00Z",
    absolute_expires_at: "2026-08-11T21:30:00Z"
  },
  organizations: mockOrganizations
};

const categories: CategoryRevenue[] = [
  {
    name: "Software",
    revenue_minor: 3124000,
    share_ratio: 0.382,
    color: "#0f9f8f"
  },
  {
    name: "Services",
    revenue_minor: 2216000,
    share_ratio: 0.271,
    color: "#334766"
  },
  {
    name: "Education",
    revenue_minor: 1643000,
    share_ratio: 0.201,
    color: "#ef765f"
  },
  {
    name: "Add-ons",
    revenue_minor: 1197000,
    share_ratio: 0.146,
    color: "#93a4b8"
  }
];

const products: ProductPerformance[] = [
  {
    name: "Atlas Operations Suite",
    category: "Software",
    revenue_minor: 1842000,
    units_sold: 96,
    change_ratio: 0.214,
    relative_ratio: 1
  },
  {
    name: "Growth Advisory Retainer",
    category: "Services",
    revenue_minor: 1468000,
    units_sold: 28,
    change_ratio: 0.123,
    relative_ratio: 0.797
  },
  {
    name: "Momentum Analytics Lab",
    category: "Education",
    revenue_minor: 1126000,
    units_sold: 74,
    change_ratio: 0.087,
    relative_ratio: 0.611
  },
  {
    name: "Workflow Automation Pack",
    category: "Add-ons",
    revenue_minor: 924000,
    units_sold: 121,
    change_ratio: -0.032,
    relative_ratio: 0.502
  },
  {
    name: "Signal Customer Hub",
    category: "Software",
    revenue_minor: 758000,
    units_sold: 43,
    change_ratio: 0.164,
    relative_ratio: 0.412
  }
];

const orderStatuses: OrderStatusDatum[] = [
  { status: "completed", count: 184, share_ratio: 0.605, color: "#0f9f8f" },
  { status: "processing", count: 52, share_ratio: 0.171, color: "#334766" },
  { status: "paid", count: 38, share_ratio: 0.125, color: "#65809f" },
  { status: "pending", count: 21, share_ratio: 0.069, color: "#f2a36f" },
  { status: "refunded", count: 9, share_ratio: 0.03, color: "#e56262" }
];

const orderCountsByRange: Record<AnalyticsRange, number[]> = {
  "7d": [52, 14, 11, 6, 3],
  "30d": [184, 52, 38, 21, 9],
  "90d": [412, 116, 84, 48, 21],
  year_to_date: [1158, 323, 237, 132, 64]
};

const rangeScale: Record<AnalyticsRange, number> = {
  "7d": 2338000 / 8180000,
  "30d": 1,
  "90d": 18724000 / 8180000,
  year_to_date: 49286000 / 8180000
};

const transactions: RecentTransaction[] = [
  {
    id: "txn-1001",
    order_number: "NS-84291",
    customer_name: "Cedar & Coast Studio",
    customer_initials: "CC",
    status: "completed",
    total_minor: 248000,
    ordered_at: "2026-08-10T14:18:00Z"
  },
  {
    id: "txn-1002",
    order_number: "NS-84290",
    customer_name: "Marlow Fieldworks",
    customer_initials: "MF",
    status: "processing",
    total_minor: 185000,
    ordered_at: "2026-08-10T12:42:00Z"
  },
  {
    id: "txn-1003",
    order_number: "NS-84289",
    customer_name: "Aperture Goods",
    customer_initials: "AG",
    status: "paid",
    total_minor: 124000,
    ordered_at: "2026-08-10T10:05:00Z"
  },
  {
    id: "txn-1004",
    order_number: "NS-84288",
    customer_name: "Willow Peak Market",
    customer_initials: "WP",
    status: "pending",
    total_minor: 96800,
    ordered_at: "2026-08-09T19:26:00Z"
  },
  {
    id: "txn-1005",
    order_number: "NS-84287",
    customer_name: "Threadline Collective",
    customer_initials: "TC",
    status: "completed",
    total_minor: 87500,
    ordered_at: "2026-08-09T16:11:00Z"
  }
];

const weeklySummary: WeeklySummary = {
  eyebrow: "Weekly business summary",
  title: "Healthy momentum, with one margin signal to watch.",
  body: "Revenue accelerated as Atlas Operations Suite and advisory services outperformed their four-week baseline. Customer acquisition remained strong, while a small rise in discounted orders lowered average order value. Protecting pricing on service bundles is the clearest opportunity for the coming week.",
  highlights: [
    { label: "Revenue", value: "+12.3%", tone: "teal" },
    { label: "New customers", value: "+8.1%", tone: "ink" },
    { label: "Average order value", value: "-2.4%", tone: "coral" }
  ],
  generated_at: "2026-08-10T15:00:00Z",
  provider: "deterministic"
};

const acquisitionByRange: Record<AnalyticsRange, AcquisitionPoint[]> = {
  "7d": [
    { label: "Mon", customers: 5 },
    { label: "Tue", customers: 8 },
    { label: "Wed", customers: 7 },
    { label: "Thu", customers: 11 },
    { label: "Fri", customers: 13 },
    { label: "Sat", customers: 9 },
    { label: "Sun", customers: 12 }
  ],
  "30d": [
    { label: "Week 1", customers: 28 },
    { label: "Week 2", customers: 34 },
    { label: "Week 3", customers: 31 },
    { label: "Week 4", customers: 42 }
  ],
  "90d": [
    { label: "May", customers: 96 },
    { label: "Jun", customers: 112 },
    { label: "Jul", customers: 127 },
    { label: "Aug", customers: 142 }
  ],
  year_to_date: [
    { label: "Jan", customers: 72 },
    { label: "Feb", customers: 78 },
    { label: "Mar", customers: 89 },
    { label: "Apr", customers: 94 },
    { label: "May", customers: 96 },
    { label: "Jun", customers: 112 },
    { label: "Jul", customers: 127 },
    { label: "Aug", customers: 142 }
  ]
};

const revenueByRange: Record<AnalyticsRange, DashboardOverview["revenue"]> = {
  "7d": [
    {
      label: "Mon",
      date: "2026-08-04",
      revenue_minor: 214000,
      comparison_minor: 196000
    },
    {
      label: "Tue",
      date: "2026-08-05",
      revenue_minor: 286000,
      comparison_minor: 231000
    },
    {
      label: "Wed",
      date: "2026-08-06",
      revenue_minor: 254000,
      comparison_minor: 242000
    },
    {
      label: "Thu",
      date: "2026-08-07",
      revenue_minor: 338000,
      comparison_minor: 275000
    },
    {
      label: "Fri",
      date: "2026-08-08",
      revenue_minor: 416000,
      comparison_minor: 362000
    },
    {
      label: "Sat",
      date: "2026-08-09",
      revenue_minor: 372000,
      comparison_minor: 308000
    },
    {
      label: "Sun",
      date: "2026-08-10",
      revenue_minor: 458000,
      comparison_minor: 381000
    }
  ],
  "30d": [
    {
      label: "Jul 12",
      date: "2026-07-12",
      revenue_minor: 680000,
      comparison_minor: 572000
    },
    {
      label: "Jul 16",
      date: "2026-07-16",
      revenue_minor: 820000,
      comparison_minor: 684000
    },
    {
      label: "Jul 20",
      date: "2026-07-20",
      revenue_minor: 760000,
      comparison_minor: 718000
    },
    {
      label: "Jul 24",
      date: "2026-07-24",
      revenue_minor: 990000,
      comparison_minor: 786000
    },
    {
      label: "Jul 28",
      date: "2026-07-28",
      revenue_minor: 930000,
      comparison_minor: 824000
    },
    {
      label: "Aug 1",
      date: "2026-08-01",
      revenue_minor: 1120000,
      comparison_minor: 896000
    },
    {
      label: "Aug 5",
      date: "2026-08-05",
      revenue_minor: 1280000,
      comparison_minor: 968000
    },
    {
      label: "Aug 10",
      date: "2026-08-10",
      revenue_minor: 1600000,
      comparison_minor: 1060000
    }
  ],
  "90d": [
    {
      label: "May 12",
      date: "2026-05-12",
      revenue_minor: 1824000,
      comparison_minor: 1668000
    },
    {
      label: "May 26",
      date: "2026-05-26",
      revenue_minor: 2068000,
      comparison_minor: 1784000
    },
    {
      label: "Jun 9",
      date: "2026-06-09",
      revenue_minor: 1926000,
      comparison_minor: 1872000
    },
    {
      label: "Jun 23",
      date: "2026-06-23",
      revenue_minor: 2284000,
      comparison_minor: 1936000
    },
    {
      label: "Jul 7",
      date: "2026-07-07",
      revenue_minor: 2478000,
      comparison_minor: 2148000
    },
    {
      label: "Jul 21",
      date: "2026-07-21",
      revenue_minor: 2362000,
      comparison_minor: 2254000
    },
    {
      label: "Aug 4",
      date: "2026-08-04",
      revenue_minor: 2764000,
      comparison_minor: 2398000
    },
    {
      label: "Aug 10",
      date: "2026-08-10",
      revenue_minor: 3018000,
      comparison_minor: 2472000
    }
  ],
  year_to_date: [
    {
      label: "Jan",
      date: "2026-01-31",
      revenue_minor: 4684000,
      comparison_minor: 3986000
    },
    {
      label: "Feb",
      date: "2026-02-28",
      revenue_minor: 4928000,
      comparison_minor: 4214000
    },
    {
      label: "Mar",
      date: "2026-03-31",
      revenue_minor: 5364000,
      comparison_minor: 4478000
    },
    {
      label: "Apr",
      date: "2026-04-30",
      revenue_minor: 5826000,
      comparison_minor: 4920000
    },
    {
      label: "May",
      date: "2026-05-31",
      revenue_minor: 6288000,
      comparison_minor: 5166000
    },
    {
      label: "Jun",
      date: "2026-06-30",
      revenue_minor: 6674000,
      comparison_minor: 5482000
    },
    {
      label: "Jul",
      date: "2026-07-31",
      revenue_minor: 7342000,
      comparison_minor: 6016000
    },
    {
      label: "Aug",
      date: "2026-08-10",
      revenue_minor: 8180000,
      comparison_minor: 6584000
    }
  ]
};

const kpiByRange: Record<AnalyticsRange, KpiMetric[]> = {
  "7d": createKpis(2338000, 8180000, 86, 65, 27186, 0.042, 0.086, 1860000),
  "30d": createKpis(8180000, 8180000, 304, 142, 26908, 0.048, 0.081, 1860000),
  "90d": createKpis(18724000, 8180000, 681, 337, 27495, 0.046, 0.124, 1860000),
  year_to_date: createKpis(
    49286000,
    8180000,
    1914,
    862,
    25750,
    0.045,
    0.187,
    1860000
  )
};

function createKpis(
  totalRevenue: number,
  monthlyRevenue: number,
  orders: number,
  customers: number,
  averageOrderValue: number,
  conversionRate: number,
  customerGrowth: number,
  mrr: number
): KpiMetric[] {
  return [
    {
      id: "total_revenue",
      label: "Total revenue",
      value: { kind: "money", amount_minor: totalRevenue, currency: "USD" },
      comparison: {
        ratio: 0.184,
        label: "18.4% vs previous period",
        direction: "up",
        sentiment: "positive"
      },
      supporting_label: "Net revenue from eligible orders"
    },
    {
      id: "monthly_revenue",
      label: "Monthly revenue",
      value: { kind: "money", amount_minor: monthlyRevenue, currency: "USD" },
      comparison: {
        ratio: 0.123,
        label: "12.3% vs previous month",
        direction: "up",
        sentiment: "positive"
      },
      supporting_label: "August performance to date"
    },
    {
      id: "orders",
      label: "Orders",
      value: { kind: "integer", value: orders },
      comparison: {
        ratio: 0.054,
        label: "5.4% vs previous period",
        direction: "up",
        sentiment: "positive"
      },
      supporting_label: "Paid, processing, and completed"
    },
    {
      id: "customers",
      label: "Customers",
      value: { kind: "integer", value: customers },
      comparison: {
        ratio: 0.081,
        label: "8.1% acquisition growth",
        direction: "up",
        sentiment: "positive"
      },
      supporting_label: "Revenue-generating customers"
    },
    {
      id: "average_order_value",
      label: "Average order value",
      value: {
        kind: "money",
        amount_minor: averageOrderValue,
        currency: "USD"
      },
      comparison: {
        ratio: -0.024,
        label: "2.4% vs previous period",
        direction: "down",
        sentiment: "negative"
      },
      supporting_label: "Monitor bundle discounting"
    },
    {
      id: "conversion_rate",
      label: "Conversion rate",
      value: { kind: "percentage", ratio: conversionRate },
      comparison: {
        ratio: 0.006,
        label: "0.6 pts above baseline",
        direction: "up",
        sentiment: "positive"
      },
      supporting_label: "Order observations per session"
    },
    {
      id: "customer_growth",
      label: "Customer growth",
      value: { kind: "percentage", ratio: customerGrowth },
      comparison: {
        ratio: 0.019,
        label: "1.9 pts vs previous period",
        direction: "up",
        sentiment: "positive"
      },
      supporting_label: "New revenue-generating customers"
    },
    {
      id: "mrr",
      label: "Monthly recurring revenue",
      value: { kind: "money", amount_minor: mrr, currency: "USD" },
      comparison: {
        ratio: 0.071,
        label: "7.1% vs previous month",
        direction: "up",
        sentiment: "positive"
      },
      supporting_label: "Imported recurring revenue signal"
    }
  ];
}

export function createMockOverview(
  organizationId: string,
  range: AnalyticsRange
): DashboardOverview {
  const scale = rangeScale[range];
  const orderCounts = orderCountsByRange[range];
  const orderStatusTotal = orderCounts.reduce(
    (total, count) => total + count,
    0
  );
  const scaledStatuses = orderStatuses.map((status, index) => ({
    ...status,
    count: orderCounts[index] ?? status.count,
    share_ratio: (orderCounts[index] ?? status.count) / orderStatusTotal
  }));

  return {
    organization_id: organizationId,
    data_availability: "available",
    range,
    comparison_range: "Previous equivalent period",
    granularity:
      range === "7d" ? "day" : range === "year_to_date" ? "month" : "week",
    time_zone: "America/New_York",
    currency: "USD",
    metric_version: "overview-v1",
    source_revision: "demo-seed-2026-08",
    generated_at: "2026-08-10T15:20:00Z",
    kpis: kpiByRange[range],
    revenue: revenueByRange[range],
    acquisition: acquisitionByRange[range],
    category_revenue: categories.map((category) => ({
      ...category,
      revenue_minor: Math.round(category.revenue_minor * scale)
    })),
    top_products: products.map((product) => ({
      ...product,
      revenue_minor: Math.round(product.revenue_minor * scale),
      units_sold: Math.max(1, Math.round(product.units_sold * scale))
    })),
    order_statuses: scaledStatuses,
    order_status_total: orderStatusTotal,
    recent_transactions: transactions,
    weekly_summary: weeklySummary
  };
}

const mockCustomerSeeds = [
  {
    id: "cust-cedar-coast",
    name: "Avery Morgan",
    initials: "AM",
    email: "avery@cedarcoast.example",
    company: "Cedar & Coast Studio",
    status: "active",
    segment: "high_value",
    total_spent_minor: 1846000,
    order_count: 12,
    average_order_value_minor: 153833,
    last_order_at: "2026-08-10T14:18:00Z",
    created_at: "2025-09-18T13:20:00Z"
  },
  {
    id: "cust-marlow",
    name: "Noah Williams",
    initials: "NW",
    email: "noah@marlowfieldworks.example",
    company: "Marlow Fieldworks",
    status: "active",
    segment: "repeat",
    total_spent_minor: 1328000,
    order_count: 9,
    average_order_value_minor: 147556,
    last_order_at: "2026-08-10T12:42:00Z",
    created_at: "2025-11-04T16:45:00Z"
  },
  {
    id: "cust-aperture",
    name: "Maya Chen",
    initials: "MC",
    email: "maya@aperturegoods.example",
    company: "Aperture Goods",
    status: "active",
    segment: "repeat",
    total_spent_minor: 1174000,
    order_count: 8,
    average_order_value_minor: 146750,
    last_order_at: "2026-08-10T10:05:00Z",
    created_at: "2025-12-12T11:10:00Z"
  },
  {
    id: "cust-willow-peak",
    name: "Elias Brooks",
    initials: "EB",
    email: "elias@willowpeak.example",
    company: "Willow Peak Market",
    status: "at_risk",
    segment: "new",
    total_spent_minor: 784000,
    order_count: 7,
    average_order_value_minor: 112000,
    last_order_at: "2026-08-09T19:26:00Z",
    created_at: "2026-01-08T09:30:00Z"
  },
  {
    id: "cust-threadline",
    name: "Sofia Rivera",
    initials: "SR",
    email: "sofia@threadline.example",
    company: "Threadline Collective",
    status: "active",
    segment: "loyal",
    total_spent_minor: 968500,
    order_count: 10,
    average_order_value_minor: 96850,
    last_order_at: "2026-08-09T16:11:00Z",
    created_at: "2025-10-22T15:05:00Z"
  },
  {
    id: "cust-northwood",
    name: "James Okafor",
    initials: "JO",
    email: "james@northwoodlabs.example",
    company: "Northwood Labs",
    status: "active",
    segment: "high_value",
    total_spent_minor: 2212000,
    order_count: 14,
    average_order_value_minor: 158000,
    last_order_at: "2026-08-07T17:35:00Z",
    created_at: "2025-07-14T12:00:00Z"
  },
  {
    id: "cust-lumen",
    name: "Priya Shah",
    initials: "PS",
    email: "priya@lumenworks.example",
    company: "Lumen Works",
    status: "active",
    segment: "repeat",
    total_spent_minor: 854000,
    order_count: 6,
    average_order_value_minor: 142333,
    last_order_at: "2026-08-04T13:10:00Z",
    created_at: "2026-02-03T10:25:00Z"
  },
  {
    id: "cust-finch",
    name: "Oliver Grant",
    initials: "OG",
    email: "oliver@finchandform.example",
    company: "Finch & Form",
    status: "at_risk",
    segment: "at_risk",
    total_spent_minor: 426000,
    order_count: 4,
    average_order_value_minor: 106500,
    last_order_at: "2026-07-28T18:22:00Z",
    created_at: "2026-02-20T14:40:00Z"
  },
  {
    id: "cust-rivermark",
    name: "Amara Lewis",
    initials: "AL",
    email: "amara@rivermark.example",
    company: "Rivermark Supply",
    status: "active",
    segment: "high_value",
    total_spent_minor: 1648000,
    order_count: 11,
    average_order_value_minor: 149818,
    last_order_at: "2026-07-19T09:44:00Z",
    created_at: "2025-08-06T08:15:00Z"
  },
  {
    id: "cust-brightpath",
    name: "Henry Adams",
    initials: "HA",
    email: "henry@brightpath.example",
    company: "Brightpath Advisory",
    status: "inactive",
    segment: "inactive",
    total_spent_minor: 238000,
    order_count: 2,
    average_order_value_minor: 119000,
    last_order_at: "2026-06-24T15:18:00Z",
    created_at: "2026-03-11T17:30:00Z"
  },
  {
    id: "cust-oakwave",
    name: "Lena Foster",
    initials: "LF",
    email: "lena@oakwave.example",
    company: "Oakwave Partners",
    status: "active",
    segment: "loyal",
    total_spent_minor: 742000,
    order_count: 5,
    average_order_value_minor: 148400,
    last_order_at: "2026-05-29T11:50:00Z",
    created_at: "2025-12-01T13:45:00Z"
  },
  {
    id: "cust-quartz",
    name: "Theo Martin",
    initials: "TM",
    email: "theo@quartzretail.example",
    company: "Quartz Retail Co.",
    status: "inactive",
    segment: "inactive",
    total_spent_minor: 186000,
    order_count: 2,
    average_order_value_minor: 93000,
    last_order_at: "2026-03-18T16:05:00Z",
    created_at: "2026-01-19T12:10:00Z"
  }
] as const;

export const mockCustomers: CustomerListItem[] = mockCustomerSeeds.map(
  (customer, index) => ({
    ...customer,
    external_id: `CUS-${String(index + 1).padStart(3, "0")}`,
    acquired_at: customer.created_at,
    version: 1,
    updated_at: customer.created_at,
    archived_at: null
  })
);

const mockProductSeeds = [
  {
    id: "prod-atlas",
    name: "Atlas Operations Suite",
    sku: "NS-ATL-001",
    category: "Software",
    status: "active",
    price_minor: 248000,
    average_selling_price_minor: 231400,
    units_sold: 96,
    revenue_minor: 1842000,
    revenue_change_ratio: 0.214,
    inventory_units: 999,
    currency: "USD",
    created_at: "2025-05-14T12:00:00Z"
  },
  {
    id: "prod-advisory",
    name: "Growth Advisory Retainer",
    sku: "NS-ADV-014",
    category: "Services",
    status: "active",
    price_minor: 185000,
    average_selling_price_minor: 181200,
    units_sold: 28,
    revenue_minor: 1468000,
    revenue_change_ratio: 0.123,
    inventory_units: 24,
    currency: "USD",
    created_at: "2025-06-02T12:00:00Z"
  },
  {
    id: "prod-momentum",
    name: "Momentum Analytics Lab",
    sku: "NS-LAB-008",
    category: "Education",
    status: "active",
    price_minor: 124000,
    average_selling_price_minor: 118900,
    units_sold: 74,
    revenue_minor: 1126000,
    revenue_change_ratio: 0.087,
    inventory_units: 48,
    currency: "USD",
    created_at: "2025-08-19T12:00:00Z"
  },
  {
    id: "prod-workflow",
    name: "Workflow Automation Pack",
    sku: "NS-AUT-022",
    category: "Add-ons",
    status: "active",
    price_minor: 96800,
    average_selling_price_minor: 91400,
    units_sold: 121,
    revenue_minor: 924000,
    revenue_change_ratio: -0.032,
    inventory_units: 152,
    currency: "USD",
    created_at: "2025-09-11T12:00:00Z"
  },
  {
    id: "prod-signal",
    name: "Signal Customer Hub",
    sku: "NS-SIG-019",
    category: "Software",
    status: "active",
    price_minor: 87500,
    average_selling_price_minor: 84200,
    units_sold: 43,
    revenue_minor: 758000,
    revenue_change_ratio: 0.164,
    inventory_units: 999,
    currency: "USD",
    created_at: "2025-10-07T12:00:00Z"
  },
  {
    id: "prod-forecast",
    name: "Forecast Planning Module",
    sku: "NS-FOR-031",
    category: "Add-ons",
    status: "active",
    price_minor: 72000,
    average_selling_price_minor: 69600,
    units_sold: 38,
    revenue_minor: 564000,
    revenue_change_ratio: 0.052,
    inventory_units: 7,
    currency: "USD",
    created_at: "2026-01-12T12:00:00Z"
  },
  {
    id: "prod-playbook",
    name: "Revenue Operations Playbook",
    sku: "NS-EDU-025",
    category: "Education",
    status: "active",
    price_minor: 46000,
    average_selling_price_minor: 43800,
    units_sold: 62,
    revenue_minor: 438000,
    revenue_change_ratio: 0.118,
    inventory_units: 85,
    currency: "USD",
    created_at: "2025-11-16T12:00:00Z"
  },
  {
    id: "prod-audit",
    name: "Data Quality Audit",
    sku: "NS-SVC-017",
    category: "Services",
    status: "active",
    price_minor: 210000,
    average_selling_price_minor: 205000,
    units_sold: 14,
    revenue_minor: 412000,
    revenue_change_ratio: -0.046,
    inventory_units: 9,
    currency: "USD",
    created_at: "2025-07-24T12:00:00Z"
  },
  {
    id: "prod-launchpad",
    name: "Launchpad Implementation",
    sku: "NS-SVC-040",
    category: "Services",
    status: "active",
    price_minor: 325000,
    average_selling_price_minor: 318000,
    units_sold: 9,
    revenue_minor: 356000,
    revenue_change_ratio: 0.238,
    inventory_units: 3,
    currency: "USD",
    created_at: "2026-03-06T12:00:00Z"
  },
  {
    id: "prod-legacy",
    name: "Legacy Metrics Connector",
    sku: "NS-CON-004",
    category: "Add-ons",
    status: "archived",
    price_minor: 38000,
    average_selling_price_minor: 36100,
    units_sold: 11,
    revenue_minor: 146000,
    revenue_change_ratio: -0.181,
    inventory_units: 0,
    currency: "USD",
    created_at: "2024-12-10T12:00:00Z"
  }
] as const;

export const mockProducts: ProductListItem[] = mockProductSeeds.map(
  (product, index) => ({
    ...product,
    external_id: `PRD-${String(index + 1).padStart(3, "0")}`,
    unit_price_minor: product.price_minor,
    average_price_minor: product.average_selling_price_minor,
    version: 1,
    updated_at: product.created_at,
    archived_at: product.status === "archived" ? product.created_at : null
  })
);

interface OrderSeed {
  id: string;
  order_number: string;
  customer_id: string;
  status: OrderStatus;
  ordered_at: string;
  source: OrderDetail["source"];
  items: Array<{ product_id: string; quantity: number }>;
}

function createOrder(seed: OrderSeed): OrderDetail {
  const customer = mockCustomers.find((item) => item.id === seed.customer_id);
  if (!customer) throw new Error(`Unknown mock customer: ${seed.customer_id}`);

  const items: OrderLineItem[] = seed.items.map((seedItem, index) => {
    const product = mockProducts.find(
      (item) => item.id === seedItem.product_id
    );
    if (!product)
      throw new Error(`Unknown mock product: ${seedItem.product_id}`);
    return {
      id: `${seed.id}-item-${index + 1}`,
      product_id: product.id,
      product_name: product.name,
      sku: product.sku,
      quantity: seedItem.quantity,
      unit_price_minor: product.unit_price_minor,
      discount_minor: 0,
      line_total_minor: product.unit_price_minor * seedItem.quantity
    };
  });
  const subtotal = items.reduce(
    (total, item) => total + item.line_total_minor,
    0
  );
  const discount =
    seed.source === "Sales-assisted" ? Math.round(subtotal * 0.05) : 0;
  const tax = Math.round((subtotal - discount) * 0.0725);
  const total = subtotal - discount + tax;
  const baseTime = new Date(seed.ordered_at).getTime();
  const statusPath: OrderStatus[] =
    seed.status === "pending"
      ? ["pending"]
      : seed.status === "cancelled"
        ? ["pending", "cancelled"]
        : seed.status === "paid"
          ? ["pending", "paid"]
          : seed.status === "processing"
            ? ["pending", "paid", "processing"]
            : seed.status === "completed"
              ? ["pending", "paid", "processing", "completed"]
              : ["pending", "paid", "processing", "completed", "refunded"];

  return {
    id: seed.id,
    order_number: seed.order_number,
    status: seed.status,
    customer: {
      id: customer.id,
      name: customer.name,
      email: customer.email,
      initials: customer.initials
    },
    item_count: items.reduce(
      (totalItems, item) => totalItems + item.quantity,
      0
    ),
    total_minor: total,
    currency: "USD",
    ordered_at: seed.ordered_at,
    etag: '"1"',
    external_id: seed.id,
    source: seed.source,
    subtotal_minor: subtotal,
    discount_minor: discount,
    tax_minor: tax,
    items,
    status_history: statusPath.map((status, index) => ({
      id: `${seed.id}-status-${index + 1}`,
      from_status: index === 0 ? null : (statusPath[index - 1] ?? null),
      to_status: status,
      reason:
        status === "refunded"
          ? "A full refund was recorded after customer review."
          : status === "cancelled"
            ? "The order was cancelled before fulfillment."
            : null,
      changed_by_user_id: null,
      occurred_at: new Date(baseTime + index * 45 * 60 * 1000).toISOString()
    }))
  };
}

export const mockOrders: OrderDetail[] = [
  createOrder({
    id: "order-84291",
    order_number: "NS-84291",
    customer_id: "cust-cedar-coast",
    status: "completed",
    ordered_at: "2026-08-10T14:18:00Z",
    source: "Web checkout",
    items: [{ product_id: "prod-atlas", quantity: 1 }]
  }),
  createOrder({
    id: "order-84290",
    order_number: "NS-84290",
    customer_id: "cust-marlow",
    status: "processing",
    ordered_at: "2026-08-10T12:42:00Z",
    source: "Sales-assisted",
    items: [
      { product_id: "prod-advisory", quantity: 1 },
      { product_id: "prod-workflow", quantity: 1 }
    ]
  }),
  createOrder({
    id: "order-84289",
    order_number: "NS-84289",
    customer_id: "cust-aperture",
    status: "paid",
    ordered_at: "2026-08-10T10:05:00Z",
    source: "Web checkout",
    items: [{ product_id: "prod-momentum", quantity: 1 }]
  }),
  createOrder({
    id: "order-84288",
    order_number: "NS-84288",
    customer_id: "cust-willow-peak",
    status: "pending",
    ordered_at: "2026-08-09T19:26:00Z",
    source: "Web checkout",
    items: [{ product_id: "prod-workflow", quantity: 1 }]
  }),
  createOrder({
    id: "order-84287",
    order_number: "NS-84287",
    customer_id: "cust-threadline",
    status: "completed",
    ordered_at: "2026-08-09T16:11:00Z",
    source: "CSV import",
    items: [
      { product_id: "prod-signal", quantity: 1 },
      { product_id: "prod-playbook", quantity: 1 }
    ]
  }),
  createOrder({
    id: "order-84286",
    order_number: "NS-84286",
    customer_id: "cust-northwood",
    status: "completed",
    ordered_at: "2026-08-07T17:35:00Z",
    source: "Sales-assisted",
    items: [
      { product_id: "prod-atlas", quantity: 2 },
      { product_id: "prod-forecast", quantity: 1 }
    ]
  }),
  createOrder({
    id: "order-84285",
    order_number: "NS-84285",
    customer_id: "cust-lumen",
    status: "cancelled",
    ordered_at: "2026-08-04T13:10:00Z",
    source: "Web checkout",
    items: [{ product_id: "prod-audit", quantity: 1 }]
  }),
  createOrder({
    id: "order-84284",
    order_number: "NS-84284",
    customer_id: "cust-finch",
    status: "refunded",
    ordered_at: "2026-07-28T18:22:00Z",
    source: "Web checkout",
    items: [
      { product_id: "prod-momentum", quantity: 1 },
      { product_id: "prod-playbook", quantity: 1 }
    ]
  }),
  createOrder({
    id: "order-84283",
    order_number: "NS-84283",
    customer_id: "cust-rivermark",
    status: "completed",
    ordered_at: "2026-07-19T09:44:00Z",
    source: "Sales-assisted",
    items: [
      { product_id: "prod-launchpad", quantity: 1 },
      { product_id: "prod-atlas", quantity: 1 }
    ]
  }),
  createOrder({
    id: "order-84282",
    order_number: "NS-84282",
    customer_id: "cust-brightpath",
    status: "completed",
    ordered_at: "2026-06-24T15:18:00Z",
    source: "CSV import",
    items: [{ product_id: "prod-signal", quantity: 2 }]
  }),
  createOrder({
    id: "order-84281",
    order_number: "NS-84281",
    customer_id: "cust-oakwave",
    status: "completed",
    ordered_at: "2026-05-29T11:50:00Z",
    source: "Sales-assisted",
    items: [{ product_id: "prod-advisory", quantity: 1 }]
  }),
  createOrder({
    id: "order-84280",
    order_number: "NS-84280",
    customer_id: "cust-quartz",
    status: "completed",
    ordered_at: "2026-03-18T16:05:00Z",
    source: "CSV import",
    items: [{ product_id: "prod-legacy", quantity: 2 }]
  }),
  createOrder({
    id: "order-84279",
    order_number: "NS-84279",
    customer_id: "cust-cedar-coast",
    status: "completed",
    ordered_at: "2026-02-14T12:30:00Z",
    source: "Web checkout",
    items: [
      { product_id: "prod-forecast", quantity: 2 },
      { product_id: "prod-playbook", quantity: 1 }
    ]
  }),
  createOrder({
    id: "order-84278",
    order_number: "NS-84278",
    customer_id: "cust-marlow",
    status: "completed",
    ordered_at: "2026-01-22T10:15:00Z",
    source: "Sales-assisted",
    items: [
      { product_id: "prod-audit", quantity: 1 },
      { product_id: "prod-workflow", quantity: 1 }
    ]
  }),
  createOrder({
    id: "order-84277",
    order_number: "NS-84277",
    customer_id: "cust-northwood",
    status: "completed",
    ordered_at: "2025-12-18T09:40:00Z",
    source: "CSV import",
    items: [
      { product_id: "prod-atlas", quantity: 1 },
      { product_id: "prod-signal", quantity: 1 }
    ]
  })
];

function orderListItem(order: OrderDetail): OrderListItem {
  const {
    source: _source,
    etag: _etag,
    external_id: _externalId,
    subtotal_minor: _subtotal,
    discount_minor: _discount,
    tax_minor: _tax,
    items: _items,
    status_history: _history,
    ...summary
  } = order;
  void _source;
  void _etag;
  void _externalId;
  void _subtotal;
  void _discount;
  void _tax;
  void _items;
  void _history;
  return summary;
}

export function createMockCustomerDetail(
  customerId: string
): CustomerDetail | null {
  const customer = mockCustomers.find((item) => item.id === customerId);
  if (!customer) return null;
  const recentOrders = mockOrders
    .filter((order) => order.customer.id === customer.id)
    .slice(0, 5)
    .map(orderListItem);
  return {
    ...customer,
    etag: '"1"',
    metrics: {
      spend_minor: customer.total_spent_minor,
      order_count: customer.order_count,
      average_order_value_minor:
        customer.order_count > 0
          ? Math.round(customer.total_spent_minor / customer.order_count)
          : null,
      last_order_at: customer.last_order_at,
      recency_days: customer.last_order_at ? 1 : null
    },
    recent_orders: recentOrders
  };
}

const performanceLabels: Record<
  AnalyticsRange,
  Array<{ label: string; date: string }>
> = {
  "7d": [
    { label: "Mon", date: "2026-08-04" },
    { label: "Tue", date: "2026-08-05" },
    { label: "Wed", date: "2026-08-06" },
    { label: "Thu", date: "2026-08-07" },
    { label: "Fri", date: "2026-08-08" },
    { label: "Sat", date: "2026-08-09" },
    { label: "Sun", date: "2026-08-10" }
  ],
  "30d": [
    { label: "Week 1", date: "2026-07-12" },
    { label: "Week 2", date: "2026-07-19" },
    { label: "Week 3", date: "2026-07-26" },
    { label: "Week 4", date: "2026-08-02" },
    { label: "Current", date: "2026-08-10" }
  ],
  "90d": [
    { label: "May", date: "2026-05-12" },
    { label: "Jun", date: "2026-06-01" },
    { label: "Jul", date: "2026-07-01" },
    { label: "Aug", date: "2026-08-10" }
  ],
  year_to_date: [
    { label: "Jan", date: "2026-01-31" },
    { label: "Feb", date: "2026-02-28" },
    { label: "Mar", date: "2026-03-31" },
    { label: "Apr", date: "2026-04-30" },
    { label: "May", date: "2026-05-31" },
    { label: "Jun", date: "2026-06-30" },
    { label: "Jul", date: "2026-07-31" },
    { label: "Aug", date: "2026-08-10" }
  ]
};

export function createMockProductDetail(
  productId: string,
  range: AnalyticsRange
): ProductDetail | null {
  const product = mockProducts.find((item) => item.id === productId);
  if (!product) return null;
  const scale = rangeScale[range];
  const scaledRevenue = Math.round(product.revenue_minor * scale);
  const points = performanceLabels[range];
  const weightTotal = points.reduce(
    (total, _point, index) => total + index + 2,
    0
  );
  const performance = points.map((point, index) => ({
    ...point,
    revenue_minor: Math.round((scaledRevenue * (index + 2)) / weightTotal),
    units_sold: Math.max(
      1,
      Math.round((product.units_sold * scale * (index + 2)) / weightTotal)
    )
  }));
  const currentUnits = Math.max(1, Math.round(product.units_sold * scale));
  const previousRevenue = Math.max(0, Math.round(scaledRevenue * 0.9));
  const previousUnits = Math.max(0, Math.round(currentUnits * 0.92));
  return {
    ...product,
    units_sold: currentUnits,
    revenue_minor: scaledRevenue,
    etag: '"1"',
    performance_range: range,
    currency: "USD",
    comparison_range: {
      start: points[0]?.date ?? "2026-01-01",
      end: points.at(-1)?.date ?? "2026-01-31"
    },
    current: {
      units_sold: currentUnits,
      eligible_revenue_minor: scaledRevenue,
      average_selling_price_minor:
        currentUnits > 0 ? Math.round(scaledRevenue / currentUnits) : null,
      order_count: Math.max(1, Math.round(currentUnits * 0.7))
    },
    previous: {
      units_sold: previousUnits,
      eligible_revenue_minor: previousRevenue,
      average_selling_price_minor:
        previousUnits > 0 ? Math.round(previousRevenue / previousUnits) : null,
      order_count: Math.max(1, Math.round(previousUnits * 0.7))
    },
    units_change_percent:
      previousUnits > 0
        ? ((currentUnits - previousUnits) / previousUnits) * 100
        : null,
    revenue_change_percent:
      previousRevenue > 0
        ? ((scaledRevenue - previousRevenue) / previousRevenue) * 100
        : null,
    performance
  };
}

export function createMockAnalyticsPerformance(
  organizationId: string,
  range: AnalyticsRange
): AnalyticsPerformance {
  const overview = createMockOverview(organizationId, range);
  const findKpi = (id: KpiMetric["id"]): KpiMetric =>
    overview.kpis.find((metric) => metric.id === id) ?? overview.kpis[0]!;
  const orderMetric = findKpi("orders");
  const orderTotal =
    orderMetric.value.kind === "integer" ? orderMetric.value.value : 0;
  const salesWeightTotal = overview.revenue.reduce(
    (total, _point, index) => total + index + 3,
    0
  );
  return {
    organization_id: organizationId,
    data_availability: "available",
    range,
    comparison_range: overview.comparison_range,
    granularity: overview.granularity,
    time_zone: overview.time_zone,
    currency: overview.currency,
    metric_version: "analytics-performance-v1",
    source_revision: overview.source_revision,
    generated_at: overview.generated_at,
    metrics: [
      {
        id: "net_revenue",
        label: "Net revenue",
        value: findKpi("total_revenue").value,
        change_ratio: 0.184,
        context: "Eligible orders after refunds"
      },
      {
        id: "orders",
        label: "Orders",
        value: orderMetric.value,
        change_ratio: 0.054,
        context: "Across all active sales channels"
      },
      {
        id: "average_order_value",
        label: "Average order value",
        value: findKpi("average_order_value").value,
        change_ratio: -0.024,
        context: "Discount mix softened the period"
      },
      {
        id: "new_customers",
        label: "New customers",
        value: findKpi("customers").value,
        change_ratio: 0.081,
        context: "First revenue-generating order"
      },
      {
        id: "repeat_rate",
        label: "Repeat purchase rate",
        value: { kind: "percentage", ratio: 0.384 },
        change_ratio: 0.032,
        context: "Customers with two or more orders"
      },
      {
        id: "gross_margin",
        label: "Gross margin",
        value: { kind: "percentage", ratio: 0.682 },
        change_ratio: 0.014,
        context: "Based on imported cost data"
      }
    ],
    sales_trend: overview.revenue.map((point, index) => {
      const orderCount = Math.max(
        1,
        Math.round((orderTotal * (index + 3)) / salesWeightTotal)
      );
      return {
        label: point.label,
        date: point.date,
        revenue_minor: point.revenue_minor,
        order_count: orderCount,
        average_order_value_minor: Math.round(point.revenue_minor / orderCount)
      };
    }),
    customer_trend: overview.acquisition.map((point, index) => ({
      label: point.label,
      date:
        overview.revenue[index]?.date ??
        overview.revenue.at(-1)?.date ??
        "2026-08-10",
      new_customers: point.customers,
      repeat_customers: Math.max(1, Math.round(point.customers * 0.62))
    })),
    product_mix: overview.category_revenue,
    order_statuses: overview.order_statuses
  };
}
