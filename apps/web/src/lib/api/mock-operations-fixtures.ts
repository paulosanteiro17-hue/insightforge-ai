import type {
  AiInsight,
  AnalyticsRange,
  AskAnswer,
  AskCapabilities,
  ImportHistoryRecord,
  ImportTemplate,
  ReportRecord,
  ReportTemplate
} from "@/lib/api/contracts";

const periodLabels: Record<AnalyticsRange, string> = {
  "7d": "Last 7 days",
  "30d": "Last 30 days",
  "90d": "Last 90 days",
  year_to_date: "Year to date"
};

export function createMockInsights(
  range: AnalyticsRange,
  generatedAt = "2026-08-10T15:30:00Z"
): AiInsight[] {
  const periodLabel = periodLabels[range];
  return [
    {
      id: "insight-revenue-acceleration",
      title: "Revenue is accelerating above the prior period",
      description:
        "Net revenue increased as Atlas Operations Suite and advisory services outperformed their comparison baselines. The mix suggests durable demand rather than a single large-order spike.",
      category: "growth",
      severity: "medium",
      supporting_metrics: [
        {
          id: "total_revenue",
          label: "Net revenue",
          formatted_value: "$81,800",
          comparison: "+18.4% vs previous period",
          source: "Analytics overview · metric v1"
        },
        {
          id: "completed_orders",
          label: "Completed orders",
          formatted_value: "184",
          comparison: "+7.6% vs previous period",
          source: "Orders aggregate · metric v1"
        }
      ],
      generated_at: generatedAt,
      period_label: periodLabel,
      provider: "deterministic"
    },
    {
      id: "insight-aov-pressure",
      title: "Discount mix is putting pressure on order value",
      description:
        "Average order value softened while order volume grew. Sales-assisted service bundles account for most of the change, making pricing discipline the clearest near-term lever.",
      category: "warning",
      severity: "high",
      supporting_metrics: [
        {
          id: "average_order_value",
          label: "Average order value",
          formatted_value: "$269",
          comparison: "−2.4% vs previous period",
          source: "Eligible orders · metric v1"
        },
        {
          id: "discounted_order_share",
          label: "Discounted order share",
          formatted_value: "14.8%",
          comparison: "+3.1 pts vs previous period",
          source: "Order pricing aggregate · metric v1"
        }
      ],
      generated_at: generatedAt,
      period_label: periodLabel,
      provider: "deterministic"
    },
    {
      id: "insight-retention-opportunity",
      title: "At-risk customers represent a recoverable revenue opportunity",
      description:
        "Two established accounts have moved beyond their normal purchase interval. A focused follow-up could protect recurring revenue without increasing acquisition spend.",
      category: "opportunity",
      severity: "medium",
      supporting_metrics: [
        {
          id: "at_risk_customers",
          label: "At-risk customers",
          formatted_value: "2",
          comparison: "$1,210 lifetime value",
          source: "Customer recency model · rule v1"
        }
      ],
      generated_at: generatedAt,
      period_label: periodLabel,
      provider: "deterministic"
    },
    {
      id: "insight-atlas-performance",
      title: "Atlas Operations Suite remains the strongest product signal",
      description:
        "Atlas leads the catalog in revenue and continues to gain share. Its conversion and low return rate support keeping it prominent in acquisition campaigns.",
      category: "performance",
      severity: "low",
      supporting_metrics: [
        {
          id: "atlas_revenue",
          label: "Atlas revenue",
          formatted_value: "$18,420",
          comparison: "+21.4% vs previous period",
          source: "Product performance · metric v1"
        },
        {
          id: "atlas_rank",
          label: "Revenue rank",
          formatted_value: "#1",
          comparison: "96 units sold",
          source: "Product ranking · metric v1"
        }
      ],
      generated_at: generatedAt,
      period_label: periodLabel,
      provider: "deterministic"
    },
    {
      id: "insight-refund-anomaly",
      title: "Refund activity is above its four-week baseline",
      description:
        "Refunds remain a small share of orders, but the latest interval is unusually high. Momentum Analytics Lab appears in the most recent refunded order and deserves a content review.",
      category: "anomaly",
      severity: "medium",
      supporting_metrics: [
        {
          id: "refund_rate",
          label: "Refund rate",
          formatted_value: "3.0%",
          comparison: "+1.2 pts vs four-week baseline",
          source: "Order status aggregate · metric v1"
        }
      ],
      generated_at: generatedAt,
      period_label: periodLabel,
      provider: "deterministic"
    }
  ];
}

export const mockAskCapabilities: AskCapabilities = {
  supported_ranges: ["7d", "30d", "90d", "year_to_date"],
  provider: "deterministic",
  capabilities: [
    {
      intent: "sales_status",
      label: "Sales status",
      description:
        "Order status counts and sales totals for a supported period.",
      example_question: "How many completed orders are there?"
    },
    {
      intent: "top_product",
      label: "Top product",
      description:
        "The leading product by eligible revenue and its supporting unit signal.",
      example_question: "Which product generated the most revenue?"
    },
    {
      intent: "revenue_decline",
      label: "Revenue decline",
      description:
        "A controlled comparison with the previous reporting period.",
      example_question: "Did revenue decline from the previous period?"
    },
    {
      intent: "top_customers",
      label: "Top customers",
      description:
        "Highest-value customer relationships from aggregated spend metrics.",
      example_question: "Who are the top 5 customers?"
    },
    {
      intent: "business_summary",
      label: "Business summary",
      description:
        "A grounded summary of revenue, customers, orders, and product momentum.",
      example_question: "Give me a business performance summary."
    }
  ],
  safety_note:
    "Questions map to allowlisted analytics functions. The assistant cannot execute SQL, inspect raw rows, reveal prompts, or access another workspace."
};

export const mockAskHistory: AskAnswer[] = [
  {
    id: "ask-history-1",
    question: "Which product generated the most revenue?",
    intent: "top_product",
    status: "answered",
    answer:
      "Atlas Operations Suite is the top product by eligible revenue, generating $18,420 from 96 units in the selected period.",
    citations: [
      {
        id: "citation-atlas-revenue",
        metric_label: "Atlas revenue",
        formatted_value: "$18,420",
        comparison: "+21.4% vs previous period",
        source: "Product performance · metric v1",
        period_label: "Last 30 days"
      }
    ],
    suggested_follow_ups: [
      "Did revenue decline from the previous period?",
      "Give me a business performance summary."
    ],
    applied_range: "30d",
    confidence: "high",
    created_at: "2026-08-10T14:45:00Z"
  }
];

export const mockReportTemplates: ReportTemplate[] = [
  {
    type: "monthly_performance",
    name: "Monthly Performance",
    label: "Monthly Performance",
    default_name: "Monthly Performance",
    supported_formats: ["csv", "json"],
    description:
      "Executive KPIs, period comparisons, and category contribution.",
    included_sections: ["KPI summary", "Revenue trend", "Category mix"]
  },
  {
    type: "sales",
    name: "Sales Report",
    label: "Sales Report",
    default_name: "Sales Report",
    supported_formats: ["csv", "json"],
    description:
      "Order volume, net revenue, status mix, and transaction detail.",
    included_sections: ["Sales summary", "Order status", "Order ledger"]
  },
  {
    type: "customer",
    name: "Customer Report",
    label: "Customer Report",
    default_name: "Customer Report",
    supported_formats: ["csv", "json"],
    description: "Acquisition, repeat behavior, segments, and lifetime value.",
    included_sections: ["Growth summary", "Segment mix", "Customer table"]
  },
  {
    type: "product_performance",
    name: "Product Performance",
    label: "Product Performance",
    default_name: "Product Performance",
    supported_formats: ["csv", "json"],
    description:
      "Product revenue, units, price realization, and trend ranking.",
    included_sections: ["Portfolio summary", "Product ranking", "Trend table"]
  }
];

export const mockReports: ReportRecord[] = [
  {
    id: "report-monthly-august",
    name: "August Monthly Performance",
    type: "monthly_performance",
    status: "ready",
    format: "csv",
    range: "30d",
    source_revision: "demo-seed-2026-08",
    created_by: "Jordan Blake",
    created_at: "2026-08-10T13:20:00Z",
    generated_at: "2026-08-10T13:20:08Z",
    expires_at: "2026-09-09T13:20:08Z",
    row_count: 38,
    summary: "Revenue grew 18.4% with balanced customer and order momentum."
  },
  {
    id: "report-sales-quarter",
    name: "Quarterly Sales Review",
    type: "sales",
    status: "ready",
    format: "json",
    range: "90d",
    source_revision: "demo-seed-2026-08",
    created_by: "Jordan Blake",
    created_at: "2026-08-08T16:05:00Z",
    generated_at: "2026-08-08T16:05:11Z",
    expires_at: "2026-09-07T16:05:11Z",
    row_count: 681,
    summary: "Completed orders accounted for 60.5% of quarterly volume."
  },
  {
    id: "report-product-july",
    name: "July Product Performance",
    type: "product_performance",
    status: "expired",
    format: "csv",
    range: "30d",
    source_revision: "demo-seed-2026-07",
    created_by: "Jordan Blake",
    created_at: "2026-07-01T10:10:00Z",
    generated_at: "2026-07-01T10:10:07Z",
    expires_at: "2026-07-31T10:10:07Z",
    row_count: 10,
    summary: "Atlas Operations Suite led product revenue for the period."
  },
  {
    id: "report-customer-retry",
    name: "Customer Growth Snapshot",
    type: "customer",
    status: "failed",
    format: "csv",
    range: "year_to_date",
    source_revision: "demo-seed-2026-07",
    created_by: "Jordan Blake",
    created_at: "2026-07-28T09:15:00Z",
    generated_at: null,
    expires_at: null,
    row_count: 0,
    summary:
      "Generation stopped after the source revision changed. Run it again."
  }
];

function template(
  kind: ImportTemplate["kind"],
  name: string,
  description: string,
  filename: string,
  headers: string[],
  sampleRows: string[][]
): ImportTemplate {
  return {
    kind,
    name,
    description,
    filename,
    headers,
    sample_rows: sampleRows,
    sample_csv: [headers, ...sampleRows].map((row) => row.join(",")).join("\n")
  };
}

export const mockImportTemplates: ImportTemplate[] = [
  template(
    "customers",
    "Customer import",
    "Create or validate customer profiles using the exact v1 English schema.",
    "customers.csv",
    ["external_id", "name", "email", "company", "status", "acquired_at"],
    [
      [
        "CUS-1042",
        "Maya Bennett",
        "maya.bennett@northstarstudio.example",
        "Northstar Studio",
        "active",
        "2025-09-12T14:30:00Z"
      ]
    ]
  ),
  template(
    "products",
    "Product import",
    "Load the canonical product catalog fields with decimal pricing.",
    "products.csv",
    ["external_id", "sku", "name", "category", "unit_price", "status"],
    [
      [
        "PRD-201",
        "ANL-PRO-M",
        "Analytics Pro Monthly",
        "Subscriptions",
        "249.00",
        "active"
      ]
    ]
  ),
  template(
    "orders",
    "Order import",
    "Import order-item rows with customer and product references.",
    "orders.csv",
    [
      "external_id",
      "order_number",
      "customer_external_id",
      "status",
      "ordered_at",
      "currency",
      "product_sku",
      "quantity",
      "unit_price",
      "discount",
      "tax"
    ],
    [
      [
        "ORD-5001",
        "IF-10501",
        "CUS-1042",
        "completed",
        "2026-06-03T14:20:00Z",
        "USD",
        "REV-AUDIT",
        "1",
        "1250.00",
        "0.00",
        "0.00"
      ]
    ]
  )
];

export const mockImportHistory: ImportHistoryRecord[] = [
  {
    id: "import-orders-august",
    kind: "orders",
    filename: "august-orders.csv",
    status: "completed",
    total_rows: 304,
    imported_rows: 304,
    error_rows: 0,
    created_at: "2026-08-09T18:15:00Z",
    completed_at: "2026-08-09T18:15:19Z"
  },
  {
    id: "import-products-correction",
    kind: "products",
    filename: "catalog-correction.csv",
    status: "validation_failed",
    total_rows: 42,
    imported_rows: 0,
    error_rows: 2,
    created_at: "2026-08-03T11:20:00Z",
    completed_at: null
  },
  {
    id: "import-customers-july",
    kind: "customers",
    filename: "july-customers.csv",
    status: "import_failed",
    total_rows: 118,
    imported_rows: 0,
    error_rows: 18,
    created_at: "2026-07-29T09:05:00Z",
    completed_at: null
  }
];
