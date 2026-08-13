export interface DataEnvelope<T> {
  data: T;
}

export interface PaginationView {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface CollectionEnvelope<T> {
  data: T[];
  meta: {
    pagination: PaginationView;
    filters: Record<string, unknown>;
  };
}

export interface ProblemFieldError {
  field: string;
  code: string;
  message: string;
}

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
  code: string;
  request_id: string;
  errors?: ProblemFieldError[];
}

export type OrganizationRole = "owner" | "admin" | "member";
export type OrganizationStatus = "active" | "suspended" | "pending_deletion";
export type OnboardingState = "organization" | "data" | "complete";

export interface UserView {
  id: string;
  email: string;
  display_name: string;
  status: "active" | "invited" | "disabled";
  email_verified_at: string | null;
  locale: string;
  time_zone: string;
  created_at: string;
}

export interface PreferenceView {
  weekly_summary_email: boolean;
  insight_alert_email: boolean;
  product_updates_email: boolean;
  compact_tables: boolean;
}

export interface CurrentUserView extends UserView {
  preferences: PreferenceView;
}

export interface SessionMetadataView {
  id: string;
  is_demo: boolean;
  idle_expires_at: string;
  absolute_expires_at: string;
}

export interface OrganizationSummaryView {
  id: string;
  name: string;
  slug: string;
  role: OrganizationRole;
  status: OrganizationStatus;
  onboarding_state: OnboardingState;
  reporting_currency: string;
  timezone: string;
  is_demo: boolean;
  demo_expires_at: string | null;
}

export interface SessionView {
  user: UserView;
  session: SessionMetadataView;
  organizations: OrganizationSummaryView[];
}

export interface PasswordResetRequestView {
  message: string;
  recovery_path: string | null;
}

export interface CurrentOrganizationView {
  id: string;
  name: string;
  slug: string;
  reporting_currency: string;
  timezone: string;
  industry: string | null;
  status: OrganizationStatus;
  onboarding_state: OnboardingState;
  data_revision: number;
  version: number;
  role: OrganizationRole;
  permissions: string[];
  is_demo: boolean;
  demo_expires_at: string | null;
  demo_status: "preparing" | "ready" | "resetting" | "expired" | null;
  plan: "free" | "pro" | "business";
}

export interface OrganizationJobView {
  id: string;
  job_type: string;
  status: JobStatus;
  progress: Record<string, unknown>;
  result: Record<string, unknown> | null;
  created_at: string;
  completed_at: string | null;
}

export type CustomerStatus = "active" | "at_risk" | "inactive";
export type CustomerSegment =
  "new" | "repeat" | "loyal" | "high_value" | "at_risk" | "inactive";

export interface CustomerView {
  id: string;
  external_id: string | null;
  name: string;
  email: string | null;
  company: string | null;
  status: CustomerStatus;
  segment: CustomerSegment;
  acquired_at: string;
  last_order_at: string | null;
  total_spent_minor: number;
  order_count: number;
  version: number;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface CustomerMetricsView {
  customer_id: string;
  spend_minor: number;
  order_count: number;
  average_order_value_minor: number | null;
  last_order_at: string | null;
  recency_days: number | null;
}

export type ProductStatus = "active" | "archived";

export interface ProductView {
  id: string;
  external_id: string | null;
  sku: string;
  name: string;
  category: string;
  unit_price_minor: number;
  status: ProductStatus;
  units_sold: number;
  revenue_minor: number;
  average_price_minor: number | null;
  version: number;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface ProductPeriodMetricsView {
  units_sold: number;
  eligible_revenue_minor: number;
  average_selling_price_minor: number | null;
  order_count: number;
}

export interface ProductMetricsView {
  product_id: string;
  currency: string;
  range: AnalyticsRangeView;
  comparison_range: AnalyticsRangeView;
  current: ProductPeriodMetricsView;
  previous: ProductPeriodMetricsView;
  units_change_percent: number | null;
  revenue_change_percent: number | null;
  trend: Array<{
    period_start: string;
    units_sold: number;
    eligible_revenue_minor: number;
  }>;
}

export type OrderStatus =
  "pending" | "paid" | "processing" | "completed" | "cancelled" | "refunded";

export interface OrderItemView {
  id: string;
  product_id: string;
  product_name: string;
  sku: string;
  quantity: number;
  unit_price_minor: number;
  discount_minor: number;
  line_total_minor: number;
}

export interface OrderStatusEventView {
  id: string;
  from_status: OrderStatus | null;
  to_status: OrderStatus;
  reason: string | null;
  changed_by_user_id: string | null;
  occurred_at: string;
}

export interface OrderView {
  id: string;
  external_id: string | null;
  order_number: string;
  status: OrderStatus;
  ordered_at: string;
  subtotal_minor: number;
  discount_minor: number;
  tax_minor: number;
  total_minor: number;
  currency: string;
  source: string;
  customer: { id: string; name: string; email: string | null };
  item_count: number;
  items: OrderItemView[] | null;
  status_history: OrderStatusEventView[] | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export type AnalyticsRange = "7d" | "30d" | "90d" | "year_to_date" | "custom";
export type AnalyticsCompare = "previous_period" | "previous_year" | "none";

export interface AnalyticsRangeView {
  start: string;
  end: string;
}

export interface ComparisonMetricView {
  value: number | null;
  comparison_value: number | null;
  change_ratio: number | null;
  change_status:
    "increase" | "decrease" | "unchanged" | "new" | "not_comparable";
}

export interface AvailabilityMetricView {
  value: number | null;
  available: boolean;
  reason: string | null;
}

export interface TimeSeriesPointView {
  period_start: string;
  revenue_minor: number;
  order_count: number;
  new_customers: number;
}

export interface BreakdownView {
  id: string | null;
  label: string;
  revenue_minor: number;
  units: number;
  count: number;
  share_ratio: number | null;
}

export interface AnalyticsView {
  range: AnalyticsRangeView;
  comparison_range: AnalyticsRangeView | null;
  granularity: "day" | "week" | "month";
  time_zone: string;
  currency: string;
  metric_version: string;
  source_revision: number;
  generated_at: string;
  data_availability: "available" | "empty";
  metrics: Record<string, ComparisonMetricView>;
  revenue_series: TimeSeriesPointView[];
  order_series: TimeSeriesPointView[];
  customer_acquisition: TimeSeriesPointView[];
  categories: BreakdownView[];
  products: BreakdownView[];
  order_statuses: BreakdownView[];
  recent_transactions: Array<{
    id: string;
    order_number: string;
    customer_name: string;
    status: OrderStatus;
    total_minor: number;
    currency: string;
    ordered_at: string;
  }>;
  conversion_rate: AvailabilityMetricView;
  mrr: AvailabilityMetricView;
}

export type ImportKind = "customers" | "products" | "orders";
export type ImportStatus =
  | "uploaded"
  | "validating"
  | "ready"
  | "importing"
  | "completed"
  | "validation_failed"
  | "import_failed"
  | "cancelled"
  | "expired";

export interface ImportView {
  id: string;
  kind: ImportKind;
  status: ImportStatus;
  original_filename: string;
  content_sha256: string;
  size_bytes: number;
  template_version: number;
  mapping: Record<string, unknown>;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  imported_rows: number;
  validation_summary: Record<string, unknown>;
  progress: Record<string, unknown>;
  created_at: string;
  confirmed_at: string | null;
  completed_at: string | null;
  expires_at: string;
}

export interface ImportPreviewView {
  import_id: string;
  headers: string[];
  rows: Array<Record<string, unknown>>;
  formula_cells: Array<Record<string, unknown>>;
  rows_truncated: boolean;
}

export interface ImportErrorView {
  id: string;
  row_number: number;
  column: string | null;
  code: string;
  message: string;
}

export interface TeamMemberView {
  id: string;
  user_id: string;
  email: string;
  display_name: string;
  role: OrganizationRole;
  joined_at: string;
}

export interface InvitationView {
  id: string;
  email: string;
  role: "admin" | "member";
  status: "pending" | "expired" | "accepted" | "revoked";
  invited_by_user_id: string;
  expires_at: string;
  created_at: string;
}

export interface InvitationPreviewView {
  organization_name: string;
  email_hint: string;
  role: string;
  expires_at: string;
}

export interface InvitationAcceptedView {
  organization_id: string;
  organization_name: string;
  member: TeamMemberView;
}

export interface PlanView {
  id: "free" | "pro" | "business";
  name: string;
  monthly_price_minor: number;
  currency: string;
  description: string;
  features: string[];
  limits: {
    members: number;
    customers: number;
    products: number;
    orders: number;
  };
}

export interface UsageMetricView {
  used: number;
  limit: number;
}

export interface SubscriptionView {
  plan: string;
  status: string;
  provider: string;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  usage: {
    members: UsageMetricView;
    customers: UsageMetricView;
    products: UsageMetricView;
    orders: UsageMetricView;
  };
}

export interface InvoiceView {
  id: string;
  number: string;
  issued_at: string;
  amount_minor: number;
  currency: string;
  status: "paid";
  hosted_url: string | null;
}

export interface BillingIntentView {
  id: string;
  kind: "upgrade" | "portal";
  status: "completed";
  mode: "demo";
  plan: string;
  destination: string | null;
  message: string;
  created_at: string;
}

export type JobStatus =
  "queued" | "running" | "succeeded" | "failed" | "cancelled";

export interface DataExportView {
  id: string;
  status: JobStatus | "expired";
  format: "json";
  filename: string | null;
  content_type: string | null;
  size_bytes: number | null;
  content_sha256: string | null;
  expires_at: string;
  download_url: string | null;
  created_at: string;
}

export interface InsightView {
  id: string;
  category: "growth" | "warning" | "opportunity" | "performance" | "anomaly";
  severity: "info" | "low" | "medium" | "high";
  title: string;
  description: string;
  supporting_metrics: Array<{
    key: string;
    value: number;
    comparison_value: number | null;
    unit: "minor_currency" | "count" | "ratio";
  }>;
  provider: string;
  model: string | null;
  prompt_version: string;
  generation_mode: "deterministic" | "provider" | "fallback";
  status: "active" | "superseded" | "failed";
  source_revision: number;
  period_start: string;
  period_end: string;
  generated_at: string;
  expires_at: string | null;
  superseded_at: string | null;
}

export interface WeeklySummaryView {
  id: string;
  week_start: string;
  week_end: string;
  headline: string;
  overview: string;
  highlights: string[];
  watch_items: string[];
  provider: string;
  model: string | null;
  prompt_version: string;
  generation_mode: "deterministic" | "provider" | "fallback";
  source_revision: number;
  generated_at: string;
}

export interface GenerationJobView {
  id: string;
  job_type: "generate_insights" | "generate_weekly_summary";
  status: JobStatus;
  progress: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error_code: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface AskCapabilityView {
  intent:
    | "sales_status"
    | "top_product"
    | "revenue_decline"
    | "top_customers"
    | "business_summary";
  label: string;
  example: string;
}

export interface AskCapabilitiesView {
  capabilities: AskCapabilityView[];
  safety_note: string;
}

export interface AnswerCitationView {
  metric: string;
  label: string;
  value: number | string;
  unit: string;
  source: "tenant_analytics";
}

export interface AssistantAnswerView {
  id: string;
  question_redacted: string;
  intent: string;
  parameters: Record<string, unknown>;
  answer: string;
  answer_status: "answered" | "unsupported" | "insufficient_data" | "blocked";
  applied_range: Record<string, unknown>;
  confidence: number | null;
  follow_ups: string[];
  citations: AnswerCitationView[];
  provider: string;
  created_at: string;
}

export interface ReportTemplateView {
  report_type:
    "monthly_performance" | "sales" | "customer" | "product_performance";
  label: string;
  description: string;
  default_name: string;
  supported_formats: Array<"json" | "csv">;
}

export interface ReportView {
  id: string;
  report_type: ReportTemplateView["report_type"];
  name: string;
  filters: {
    date_from: string;
    date_to: string;
    granularity: "day" | "week" | "month";
  };
  status: "queued" | "generating" | "ready" | "failed" | "expired";
  format: "json" | "csv";
  source_revision: number;
  result_summary: Record<string, unknown> | null;
  generated_at: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}
