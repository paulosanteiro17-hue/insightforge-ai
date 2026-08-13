export type AnalyticsRange = "7d" | "30d" | "90d" | "year_to_date";

export type OrganizationRole = "owner" | "admin" | "member";

export interface OrganizationSummary {
  id: string;
  name: string;
  slug: string;
  role: OrganizationRole;
  status: "active" | "suspended" | "pending_deletion";
  onboarding_state: "organization" | "data" | "complete";
  reporting_currency: string;
  timezone: string;
  is_demo: boolean;
  demo_expires_at: string | null;
}

export interface UserSummary {
  id: string;
  display_name: string;
  email: string;
  status: "active" | "invited" | "disabled";
  email_verified_at: string | null;
  locale: string;
  time_zone: string;
  created_at: string;
}

export interface SessionView {
  user: UserSummary;
  session: {
    id: string;
    is_demo: boolean;
    idle_expires_at: string;
    absolute_expires_at: string;
  };
  organizations: OrganizationSummary[];
}

export type MetricValue =
  | { kind: "money"; amount_minor: number; currency: string }
  | { kind: "integer"; value: number }
  | { kind: "percentage"; ratio: number };

export interface MetricComparison {
  ratio: number | null;
  label: string;
  direction: "up" | "down" | "flat" | "new";
  sentiment: "positive" | "negative" | "neutral";
}

export interface KpiMetric {
  id:
    | "total_revenue"
    | "monthly_revenue"
    | "orders"
    | "customers"
    | "average_order_value"
    | "conversion_rate"
    | "customer_growth"
    | "mrr";
  label: string;
  value: MetricValue;
  comparison: MetricComparison;
  supporting_label: string;
}

export interface RevenuePoint {
  label: string;
  date: string;
  revenue_minor: number;
  comparison_minor?: number;
}

export interface AcquisitionPoint {
  label: string;
  customers: number;
}

export interface CategoryRevenue {
  name: string;
  revenue_minor: number;
  share_ratio: number;
  color: string;
}

export interface ProductPerformance {
  name: string;
  category?: string;
  revenue_minor: number;
  units_sold: number;
  change_ratio: number | null;
  relative_ratio: number;
}

export interface OrderStatusDatum {
  status: OrderStatus;
  count: number;
  share_ratio: number;
  color: string;
}

export interface RecentTransaction {
  id: string;
  order_number: string;
  customer_name: string;
  customer_initials: string;
  status: OrderStatus;
  total_minor: number;
  ordered_at: string;
}

export interface WeeklySummary {
  id?: string;
  week_start?: string;
  week_end?: string;
  headline?: string;
  overview?: string;
  highlights: Array<
    string | { label: string; value: string; tone: "teal" | "coral" | "ink" }
  >;
  watch_items?: string[];
  eyebrow?: string;
  title?: string;
  body?: string;
  generated_at: string;
  provider: string;
  generation_mode?: "deterministic" | "provider" | "fallback";
  source_revision?: string;
}

export interface DashboardOverview {
  organization_id: string;
  data_availability: "available" | "empty";
  range: AnalyticsRange;
  comparison_range: string;
  granularity: "day" | "week" | "month";
  time_zone: string;
  currency: string;
  metric_version: string;
  source_revision: string;
  generated_at: string;
  kpis: KpiMetric[];
  revenue: RevenuePoint[];
  acquisition: AcquisitionPoint[];
  category_revenue: CategoryRevenue[];
  top_products: ProductPerformance[];
  order_statuses: OrderStatusDatum[];
  order_status_total: number;
  recent_transactions: RecentTransaction[];
  weekly_summary: WeeklySummary | null;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: PaginationMeta;
}

export type OrderStatus =
  "pending" | "paid" | "processing" | "completed" | "cancelled" | "refunded";

export interface OrderListQuery {
  search?: string;
  status?: OrderStatus;
  sort: "ordered_at_desc" | "ordered_at_asc" | "total_desc" | "total_asc";
  page: number;
  page_size: number;
  range: AnalyticsRange;
}

export interface OrderCustomerSummary {
  id: string;
  name: string;
  email: string | null;
  initials: string;
}

export interface OrderListItem {
  id: string;
  order_number: string;
  status: OrderStatus;
  customer: OrderCustomerSummary;
  item_count: number;
  total_minor: number;
  currency: string;
  ordered_at: string;
}

export interface OrderLineItem {
  id: string;
  product_id: string;
  product_name: string;
  sku: string;
  quantity: number;
  unit_price_minor: number;
  discount_minor: number;
  line_total_minor: number;
}

export interface OrderStatusEvent {
  id: string;
  from_status: OrderStatus | null;
  to_status: OrderStatus;
  reason: string | null;
  changed_by_user_id: string | null;
  occurred_at: string;
}

export interface OrderDetail extends OrderListItem {
  etag: string;
  external_id: string | null;
  source: string;
  subtotal_minor: number;
  discount_minor: number;
  tax_minor: number;
  items: OrderLineItem[];
  status_history: OrderStatusEvent[];
}

export type CustomerStatus = "active" | "at_risk" | "inactive";
export type CustomerSegment =
  "new" | "repeat" | "loyal" | "high_value" | "at_risk" | "inactive";

export interface CustomerListQuery {
  search?: string;
  status?: CustomerStatus;
  segment?: CustomerSegment;
  sort: "total_spent_desc" | "total_spent_asc" | "name_asc" | "last_order_desc";
  page: number;
  page_size: number;
}

export interface CustomerListItem {
  id: string;
  external_id: string | null;
  name: string;
  initials: string;
  email: string | null;
  company: string | null;
  status: CustomerStatus;
  segment: CustomerSegment;
  acquired_at: string;
  total_spent_minor: number;
  order_count: number;
  last_order_at: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface CustomerGrowthPoint {
  label: string;
  date: string;
  cumulative_value_minor: number;
  order_value_minor: number;
}

export interface CustomerDetail extends CustomerListItem {
  etag: string;
  metrics: {
    spend_minor: number;
    order_count: number;
    average_order_value_minor: number | null;
    last_order_at: string | null;
    recency_days: number | null;
  };
  recent_orders: OrderListItem[];
}

export type ProductStatus = "active" | "archived";

export interface ProductListQuery {
  search?: string;
  status?: ProductStatus;
  category?: string;
  sort:
    "revenue_desc" | "revenue_asc" | "units_desc" | "name_asc" | "price_desc";
  page: number;
  page_size: number;
  range: AnalyticsRange;
}

export interface ProductListItem {
  id: string;
  external_id: string | null;
  name: string;
  sku: string;
  category: string;
  status: ProductStatus;
  unit_price_minor: number;
  average_price_minor: number | null;
  units_sold: number;
  revenue_minor: number;
  version: number;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface ProductTrendPoint {
  label: string;
  date: string;
  revenue_minor: number;
  units_sold: number;
}

export interface ProductDetail extends ProductListItem {
  etag: string;
  performance_range: AnalyticsRange;
  currency: string;
  comparison_range: { start: string; end: string };
  current: {
    units_sold: number;
    eligible_revenue_minor: number;
    average_selling_price_minor: number | null;
    order_count: number;
  };
  previous: {
    units_sold: number;
    eligible_revenue_minor: number;
    average_selling_price_minor: number | null;
    order_count: number;
  };
  units_change_percent: number | null;
  revenue_change_percent: number | null;
  performance: ProductTrendPoint[];
}

export interface AnalyticsMetric {
  id: string;
  label: string;
  value: MetricValue;
  change_ratio: number;
  context: string;
}

export interface SalesTrendPoint {
  label: string;
  date: string;
  revenue_minor: number;
  order_count: number;
  average_order_value_minor: number;
}

export interface CustomerTrendPoint {
  label: string;
  date: string;
  new_customers: number;
  repeat_customers?: number;
}

export interface ProductMixPoint {
  name: string;
  revenue_minor: number;
  share_ratio: number;
  color: string;
}

export interface AnalyticsPerformance {
  organization_id: string;
  data_availability: "available" | "empty";
  range: AnalyticsRange;
  comparison_range: string;
  granularity: "day" | "week" | "month";
  time_zone: string;
  currency: string;
  metric_version: string;
  source_revision: string;
  generated_at: string;
  metrics: AnalyticsMetric[];
  sales_trend: SalesTrendPoint[];
  customer_trend: CustomerTrendPoint[];
  product_mix: ProductMixPoint[];
  order_statuses: OrderStatusDatum[];
}

export type InsightCategory =
  "growth" | "warning" | "opportunity" | "performance" | "anomaly";
export type InsightSeverity = "info" | "low" | "medium" | "high";

export interface SupportingMetric {
  key?: string;
  value?: number;
  comparison_value?: number | null;
  unit?: "minor_currency" | "count" | "ratio";
  id?: string;
  label?: string;
  formatted_value?: string;
  comparison?: string;
  source?: string;
}

export interface AiInsight {
  id: string;
  title: string;
  description: string;
  category: InsightCategory;
  severity: InsightSeverity;
  supporting_metrics: SupportingMetric[];
  generated_at: string;
  period_start?: string;
  period_end?: string;
  period_label?: string;
  provider: string;
  generation_mode?: "deterministic" | "provider" | "fallback";
}

export interface InsightListQuery {
  search?: string;
  category?: InsightCategory;
  severity?: InsightSeverity;
  range: AnalyticsRange;
}

export interface InsightCollection {
  organization_id: string;
  range: AnalyticsRange;
  generated_at: string;
  generation_mode: "deterministic" | "provider" | "fallback";
  items: AiInsight[];
}

export interface InsightGenerationResult extends InsightCollection {
  generation_id: string;
  status: "succeeded";
  feedback: string;
}

export type AskIntent =
  | "sales_status"
  | "top_product"
  | "revenue_decline"
  | "top_customers"
  | "business_summary";
export type AskAnswerStatus =
  "answered" | "unsupported" | "insufficient_data" | "blocked";

export interface AskCapability {
  intent: AskIntent;
  label: string;
  example?: string;
  description?: string;
  example_question?: string;
}

export interface AskCapabilities {
  capabilities: AskCapability[];
  safety_note: string;
  supported_ranges?: AnalyticsRange[];
  provider?: string;
}

export interface AskCitation {
  metric?: string;
  label?: string;
  value?: number | string;
  unit?: string;
  source: string;
  id?: string;
  metric_label?: string;
  formatted_value?: string;
  comparison?: string;
  period_label?: string;
}

export interface AskQuestionInput {
  question: string;
  range: AnalyticsRange;
}

export interface AskAnswer {
  id: string;
  question: string;
  intent: string | null;
  status: AskAnswerStatus;
  answer: string;
  citations: AskCitation[];
  suggested_follow_ups: string[];
  applied_range: Record<string, unknown> | AnalyticsRange;
  confidence: number | "high" | "medium" | "not_applicable" | null;
  provider?: string;
  created_at: string;
}

export type ReportType =
  "monthly_performance" | "sales" | "customer" | "product_performance";
export type ReportStatus =
  "queued" | "ready" | "generating" | "failed" | "expired";
export type ReportFormat = "csv" | "json";

export interface ReportTemplate {
  type: ReportType;
  label?: string;
  name?: string;
  description: string;
  default_name?: string;
  supported_formats?: ReportFormat[];
  included_sections?: string[];
}

export interface ReportRecord {
  id: string;
  name: string;
  type: ReportType;
  status: ReportStatus;
  format: ReportFormat;
  date_from?: string;
  date_to?: string;
  granularity?: "day" | "week" | "month";
  source_revision?: string;
  result_summary?: Record<string, unknown> | null;
  range?: AnalyticsRange;
  created_by?: string;
  summary?: string;
  created_at: string;
  updated_at?: string;
  generated_at: string | null;
  expires_at: string | null;
  row_count: number | null;
}

export interface ReportListQuery {
  search?: string;
  type?: ReportType;
  status?: ReportStatus;
  range: AnalyticsRange;
}

export interface CreateReportInput {
  type: ReportType;
  name?: string;
  format: ReportFormat;
  range: AnalyticsRange;
}

export interface ReportDownload {
  filename: string;
  mime_type: "text/csv" | "application/json";
  content: string;
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

export interface ImportTemplate {
  kind: ImportKind;
  name: string;
  description: string;
  filename: string;
  headers: string[];
  sample_rows: string[][];
  sample_csv: string;
}

export interface ImportValidationError {
  id: string;
  row_number: number;
  column: string | null;
  code: string;
  message: string;
}

export interface ImportPreview {
  import_id: string;
  kind: ImportKind;
  filename: string;
  status: "ready" | "validation_failed";
  headers: string[];
  preview_rows: Array<Record<string, string>>;
  total_rows: number;
  valid_rows: number;
  error_rows: number;
  errors: ImportValidationError[];
  errors_truncated: boolean;
  duplicate_policy: "create_only";
}

export interface CsvUploadInput {
  kind: ImportKind;
  filename: string;
  size_bytes: number;
  mime_type: string;
  content: string;
}

export interface ImportHistoryRecord {
  id: string;
  kind: ImportKind;
  filename: string;
  status: ImportStatus;
  total_rows: number;
  imported_rows: number;
  error_rows: number;
  created_at: string;
  completed_at: string | null;
}

export type OnboardingStep = "organization" | "data" | "profile" | "complete";
export type OnboardingDataChoice = "demo" | "csv" | "empty";

export interface OnboardingOrganizationDraft {
  name: string;
  slug: string;
  timezone: string;
  reporting_currency: string;
  industry: string | null;
}

export interface AccountPreferences {
  weekly_summary_email: boolean;
  insight_alert_email: boolean;
  product_updates_email: boolean;
  compact_tables: boolean;
}

export interface OnboardingProfileDraft {
  display_name: string;
  locale: string;
  time_zone: string;
}

export interface OnboardingSnapshot {
  organization_id: string;
  current_step: OnboardingStep;
  completed_at: string | null;
  organization: OnboardingOrganizationDraft;
  data_choice: OnboardingDataChoice | null;
  profile: OnboardingProfileDraft;
  preferences: AccountPreferences;
}

export type SaveOnboardingOrganizationInput = OnboardingOrganizationDraft;

export interface SaveOnboardingDataInput {
  choice: OnboardingDataChoice;
}

export interface SaveOnboardingProfileInput {
  profile: OnboardingProfileDraft;
  preferences: AccountPreferences;
}

export type TeamMemberRole = OrganizationRole;
export type InvitationRole = Exclude<OrganizationRole, "owner">;
export type InvitationStatus = "pending" | "expired" | "revoked";

export interface TeamMember {
  id: string;
  user_id: string;
  display_name: string;
  email: string;
  role: TeamMemberRole;
  joined_at: string;
  is_current_user: boolean;
}

export interface TeamInvitation {
  id: string;
  email: string;
  role: InvitationRole;
  status: InvitationStatus | "accepted";
  invited_by_user_id: string;
  created_at: string;
  expires_at: string;
  acceptance_token?: string;
}

export interface TeamOverview {
  organization_id: string;
  current_user_role: OrganizationRole;
  can_manage_members: boolean;
  demo_policy: string;
  members: TeamMember[];
  invitations: TeamInvitation[];
}

export interface InvitationPreview {
  organization_name: string;
  email_hint: string;
  role: string;
  expires_at: string;
}

export interface InvitationAccepted {
  organization_id: string;
  organization_name: string;
  member: TeamMember;
}

export interface InviteMemberInput {
  email: string;
  role: InvitationRole;
}

export type BillingPlanId = "free" | "pro" | "business";

export interface BillingPlan {
  id: BillingPlanId;
  name: string;
  description: string;
  monthly_price_minor: number;
  currency: string;
  features: string[];
  limits: {
    members: number;
    customers: number;
    products: number;
    orders: number;
  };
}

export interface BillingSubscription {
  plan: BillingPlanId;
  status: string;
  provider: string;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

export interface BillingUsageMetric {
  id: "members" | "customers" | "products" | "orders";
  label: string;
  used: number;
  limit: number;
  unit: string;
}

export interface BillingInvoice {
  id: string;
  number: string;
  amount_minor: number;
  currency: string;
  status: "paid";
  issued_at: string;
  hosted_url: string | null;
}

export interface BillingOverview {
  organization_id: string;
  subscription: BillingSubscription;
  plans: BillingPlan[];
  usage: BillingUsageMetric[];
  invoices: BillingInvoice[];
  demo_notice: string;
  can_manage_billing: boolean;
}

export interface BillingPlanChangeResult {
  subscription: BillingSubscription;
  feedback: string;
  charged_amount_minor: 0;
}

export interface SettingsProfile {
  display_name: string;
  email: string;
  locale: string;
  time_zone: string;
}

export interface SettingsOrganization {
  name: string;
  slug: string;
  timezone: string;
  reporting_currency: string;
  industry: string | null;
  etag: string;
}

export interface SettingsSnapshot {
  organization_id: string;
  profile: SettingsProfile;
  organization: SettingsOrganization;
  preferences: AccountPreferences;
  security: {
    password_change_allowed: boolean;
    demo_message: string;
  };
  data_controls: {
    export_available: boolean;
    deletion_allowed: boolean;
    demo_message: string;
  };
}

export interface UpdateProfileInput {
  display_name: string;
  locale: string;
  time_zone: string;
}

export interface UpdateOrganizationInput {
  name: string;
  slug?: string;
  timezone: string;
  reporting_currency?: string;
  industry?: string | null;
  if_match: string;
}

export interface ChangePasswordInput {
  current_password: string;
  new_password: string;
}

export interface DataExportArtifact {
  filename: string;
  mime_type: "application/json";
  content: string;
  generated_at: string;
}

export interface ApiProblem {
  type?: string;
  title: string;
  detail: string;
  status: number;
  code: string;
  instance?: string;
  request_id: string;
  errors?: Array<{
    field: string;
    code: string;
    message: string;
  }>;
}

export class ApiProblemError extends Error {
  readonly problem: ApiProblem;

  constructor(problem: ApiProblem) {
    super(problem.detail);
    this.name = "ApiProblemError";
    this.problem = problem;
  }
}

export interface SignInInput {
  email: string;
  password: string;
}

export interface SignUpInput extends SignInInput {
  display_name: string;
}

export interface PasswordResetRequestResult {
  message: string;
  recovery_path: string | null;
}

export interface OrganizationCreateInput {
  name: string;
  slug?: string;
  reporting_currency: string;
  timezone: string;
  industry?: string | null;
}

export interface CustomerCreateInput {
  external_id?: string | null;
  name: string;
  email?: string | null;
  company?: string | null;
  status?: CustomerStatus;
  acquired_at?: string | null;
}

export type CustomerUpdateInput = Partial<
  Pick<
    CustomerCreateInput,
    "external_id" | "name" | "email" | "company" | "status"
  >
>;

export interface ProductCreateInput {
  external_id?: string | null;
  sku: string;
  name: string;
  category: string;
  unit_price_minor: number;
}

export type ProductUpdateInput = Partial<ProductCreateInput> & {
  status?: ProductStatus;
};

export interface InsightForgeApi {
  auth: {
    signIn(input: SignInInput, signal?: AbortSignal): Promise<SessionView>;
    signUp(input: SignUpInput, signal?: AbortSignal): Promise<SessionView>;
    createDemoSession(signal?: AbortSignal): Promise<SessionView>;
    requestPasswordReset(
      email: string,
      signal?: AbortSignal
    ): Promise<PasswordResetRequestResult>;
    confirmPasswordReset(
      token: string,
      password: string,
      signal?: AbortSignal
    ): Promise<void>;
    signOut(signal?: AbortSignal): Promise<void>;
  };
  organizations: {
    list(signal?: AbortSignal): Promise<OrganizationSummary[]>;
    getBySlug(
      slug: string,
      signal?: AbortSignal
    ): Promise<OrganizationSummary | null>;
    create(
      input: OrganizationCreateInput,
      signal?: AbortSignal
    ): Promise<OrganizationSummary>;
  };
  analytics: {
    getOverview(
      organizationId: string,
      range: AnalyticsRange,
      signal?: AbortSignal
    ): Promise<DashboardOverview>;
    getPerformance(
      organizationId: string,
      range: AnalyticsRange,
      signal?: AbortSignal
    ): Promise<AnalyticsPerformance>;
    regenerateWeeklySummary(
      organizationId: string,
      signal?: AbortSignal
    ): Promise<WeeklySummary>;
  };
  orders: {
    list(
      organizationId: string,
      query: OrderListQuery,
      signal?: AbortSignal
    ): Promise<PaginatedResponse<OrderListItem>>;
    getById(
      organizationId: string,
      orderId: string,
      signal?: AbortSignal
    ): Promise<OrderDetail>;
    updateStatus(
      organizationId: string,
      orderId: string,
      status: OrderStatus,
      ifMatch: string,
      signal?: AbortSignal
    ): Promise<OrderDetail>;
    cancel(
      organizationId: string,
      orderId: string,
      reason: string,
      signal?: AbortSignal
    ): Promise<OrderDetail>;
    refund(
      organizationId: string,
      orderId: string,
      reason: string,
      signal?: AbortSignal
    ): Promise<OrderDetail>;
  };
  customers: {
    list(
      organizationId: string,
      query: CustomerListQuery,
      signal?: AbortSignal
    ): Promise<PaginatedResponse<CustomerListItem>>;
    getById(
      organizationId: string,
      customerId: string,
      signal?: AbortSignal
    ): Promise<CustomerDetail>;
    create(
      organizationId: string,
      input: CustomerCreateInput,
      signal?: AbortSignal
    ): Promise<CustomerListItem>;
    update(
      organizationId: string,
      customerId: string,
      input: CustomerUpdateInput,
      ifMatch: string,
      signal?: AbortSignal
    ): Promise<CustomerListItem>;
    archive(
      organizationId: string,
      customerId: string,
      ifMatch: string,
      signal?: AbortSignal
    ): Promise<void>;
  };
  products: {
    list(
      organizationId: string,
      query: ProductListQuery,
      signal?: AbortSignal
    ): Promise<PaginatedResponse<ProductListItem>>;
    getById(
      organizationId: string,
      productId: string,
      range: AnalyticsRange,
      signal?: AbortSignal
    ): Promise<ProductDetail>;
    create(
      organizationId: string,
      input: ProductCreateInput,
      signal?: AbortSignal
    ): Promise<ProductListItem>;
    update(
      organizationId: string,
      productId: string,
      input: ProductUpdateInput,
      ifMatch: string,
      signal?: AbortSignal
    ): Promise<ProductListItem>;
    archive(
      organizationId: string,
      productId: string,
      ifMatch: string,
      signal?: AbortSignal
    ): Promise<void>;
  };
  insights: {
    list(
      organizationId: string,
      query: InsightListQuery,
      signal?: AbortSignal
    ): Promise<InsightCollection>;
    regenerate(
      organizationId: string,
      range: AnalyticsRange,
      signal?: AbortSignal
    ): Promise<InsightGenerationResult>;
  };
  askData: {
    getCapabilities(
      organizationId: string,
      signal?: AbortSignal
    ): Promise<AskCapabilities>;
    ask(
      organizationId: string,
      input: AskQuestionInput,
      signal?: AbortSignal
    ): Promise<AskAnswer>;
    history(organizationId: string, signal?: AbortSignal): Promise<AskAnswer[]>;
  };
  reports: {
    templates(
      organizationId: string,
      signal?: AbortSignal
    ): Promise<ReportTemplate[]>;
    list(
      organizationId: string,
      query: ReportListQuery,
      signal?: AbortSignal
    ): Promise<ReportRecord[]>;
    create(
      organizationId: string,
      input: CreateReportInput,
      signal?: AbortSignal
    ): Promise<ReportRecord>;
    download(
      organizationId: string,
      reportId: string,
      signal?: AbortSignal
    ): Promise<ReportDownload>;
  };
  imports: {
    templates(signal?: AbortSignal): Promise<ImportTemplate[]>;
    history(
      organizationId: string,
      signal?: AbortSignal
    ): Promise<ImportHistoryRecord[]>;
    validate(
      organizationId: string,
      input: CsvUploadInput,
      signal?: AbortSignal
    ): Promise<ImportPreview>;
    commit(
      organizationId: string,
      importId: string,
      signal?: AbortSignal
    ): Promise<ImportHistoryRecord>;
  };
  onboarding: {
    get(
      organizationId: string,
      signal?: AbortSignal
    ): Promise<OnboardingSnapshot>;
    saveOrganization(
      organizationId: string,
      input: SaveOnboardingOrganizationInput,
      signal?: AbortSignal
    ): Promise<OnboardingSnapshot>;
    chooseData(
      organizationId: string,
      input: SaveOnboardingDataInput,
      signal?: AbortSignal
    ): Promise<OnboardingSnapshot>;
    saveProfile(
      organizationId: string,
      input: SaveOnboardingProfileInput,
      signal?: AbortSignal
    ): Promise<OnboardingSnapshot>;
    complete(
      organizationId: string,
      signal?: AbortSignal
    ): Promise<OnboardingSnapshot>;
  };
  team: {
    previewInvitation(
      token: string,
      signal?: AbortSignal
    ): Promise<InvitationPreview>;
    acceptInvitation(
      token: string,
      signal?: AbortSignal
    ): Promise<InvitationAccepted>;
    getOverview(
      organizationId: string,
      signal?: AbortSignal
    ): Promise<TeamOverview>;
    invite(
      organizationId: string,
      input: InviteMemberInput,
      signal?: AbortSignal
    ): Promise<TeamInvitation>;
    changeRole(
      organizationId: string,
      memberId: string,
      role: TeamMemberRole,
      signal?: AbortSignal
    ): Promise<TeamMember>;
    removeMember(
      organizationId: string,
      memberId: string,
      signal?: AbortSignal
    ): Promise<void>;
    resendInvitation(
      organizationId: string,
      invitationId: string,
      signal?: AbortSignal
    ): Promise<TeamInvitation>;
    revokeInvitation(
      organizationId: string,
      invitationId: string,
      signal?: AbortSignal
    ): Promise<void>;
  };
  billing: {
    getOverview(
      organizationId: string,
      signal?: AbortSignal
    ): Promise<BillingOverview>;
    changePlan(
      organizationId: string,
      planId: BillingPlanId,
      signal?: AbortSignal
    ): Promise<BillingPlanChangeResult>;
  };
  settings: {
    get(
      organizationId: string,
      signal?: AbortSignal
    ): Promise<SettingsSnapshot>;
    updateProfile(
      organizationId: string,
      input: UpdateProfileInput,
      signal?: AbortSignal
    ): Promise<SettingsSnapshot>;
    updateOrganization(
      organizationId: string,
      input: UpdateOrganizationInput,
      signal?: AbortSignal
    ): Promise<SettingsSnapshot>;
    updatePreferences(
      organizationId: string,
      input: AccountPreferences,
      signal?: AbortSignal
    ): Promise<SettingsSnapshot>;
    changePassword(
      organizationId: string,
      input: ChangePasswordInput,
      signal?: AbortSignal
    ): Promise<void>;
    requestExport(
      organizationId: string,
      signal?: AbortSignal
    ): Promise<DataExportArtifact>;
    deleteOrganization(
      organizationId: string,
      confirmation: string,
      signal?: AbortSignal
    ): Promise<void>;
  };
}
