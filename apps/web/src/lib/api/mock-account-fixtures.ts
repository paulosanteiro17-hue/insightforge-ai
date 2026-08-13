import type {
  BillingInvoice,
  BillingPlan,
  BillingSubscription,
  BillingUsageMetric,
  OnboardingSnapshot,
  SettingsSnapshot,
  TeamInvitation,
  TeamMember
} from "@/lib/api/contracts";

const organizationId = "01914d2e-50a3-7c44-a9bc-5f98cf7bf803";
const ownerId = "01914d2e-50a3-7c44-a9bc-5f98cf7bf810";

export const mockOnboardingSnapshot: OnboardingSnapshot = {
  organization_id: organizationId,
  current_step: "organization",
  completed_at: null,
  organization: {
    name: "Northstar Commerce",
    slug: "northstar-commerce",
    timezone: "America/New_York",
    reporting_currency: "USD",
    industry: "Retail"
  },
  data_choice: null,
  profile: {
    display_name: "Jordan Blake",
    locale: "en-US",
    time_zone: "America/New_York"
  },
  preferences: {
    weekly_summary_email: true,
    insight_alert_email: true,
    product_updates_email: false,
    compact_tables: false
  }
};

export const mockTeamMembers: TeamMember[] = [
  {
    id: ownerId,
    user_id: ownerId,
    display_name: "Jordan Blake",
    email: "jordan@northstar.example",
    role: "owner",
    joined_at: "2025-11-04T14:20:00Z",
    is_current_user: true
  },
  {
    id: "member-maya-chen",
    user_id: "user-maya-chen",
    display_name: "Maya Chen",
    email: "maya@northstar.example",
    role: "admin",
    joined_at: "2026-01-12T16:05:00Z",
    is_current_user: false
  },
  {
    id: "member-elliot-reed",
    user_id: "user-elliot-reed",
    display_name: "Elliot Reed",
    email: "elliot@northstar.example",
    role: "member",
    joined_at: "2026-03-18T10:40:00Z",
    is_current_user: false
  },
  {
    id: "member-priya-shah",
    user_id: "user-priya-shah",
    display_name: "Priya Shah",
    email: "priya@northstar.example",
    role: "member",
    joined_at: "2026-06-02T09:15:00Z",
    is_current_user: false
  }
];

export const mockTeamInvitations: TeamInvitation[] = [
  {
    id: "invite-riley-stone",
    email: "riley@northstar.example",
    role: "member",
    status: "pending",
    invited_by_user_id: ownerId,
    created_at: "2026-08-08T13:30:00Z",
    expires_at: "2026-08-15T13:30:00Z"
  },
  {
    id: "invite-alex-morgan",
    email: "alex@northstar.example",
    role: "admin",
    status: "expired",
    invited_by_user_id: ownerId,
    created_at: "2026-07-24T11:10:00Z",
    expires_at: "2026-07-31T11:10:00Z"
  }
];

export const mockBillingPlans: BillingPlan[] = [
  {
    id: "free",
    name: "Free",
    description: "Essential analytics for a small workspace.",
    monthly_price_minor: 0,
    currency: "USD",
    features: ["Core dashboards", "CSV imports", "Weekly business summary"],
    limits: { members: 3, customers: 1_000, products: 100, orders: 5_000 }
  },
  {
    id: "pro",
    name: "Pro",
    description: "Advanced analytics and AI workflows for growing teams.",
    monthly_price_minor: 4_900,
    currency: "USD",
    features: ["Everything in Free", "AI insights", "Advanced reports"],
    limits: { members: 15, customers: 25_000, products: 2_000, orders: 100_000 }
  },
  {
    id: "business",
    name: "Business",
    description: "Higher limits and controls for established teams.",
    monthly_price_minor: 14_900,
    currency: "USD",
    features: ["Everything in Pro", "Expanded team limits", "Audit exports"],
    limits: {
      members: 100,
      customers: 250_000,
      products: 20_000,
      orders: 1_000_000
    }
  }
];

export const mockBillingSubscription: BillingSubscription = {
  plan: "pro",
  status: "active",
  provider: "demo",
  current_period_start: "2026-08-01T00:00:00Z",
  current_period_end: "2026-09-01T00:00:00Z",
  cancel_at_period_end: false
};

export const mockBillingUsage: BillingUsageMetric[] = [
  { id: "members", label: "Members", used: 4, limit: 15, unit: "records" },
  {
    id: "customers",
    label: "Customers",
    used: 142,
    limit: 25_000,
    unit: "records"
  },
  {
    id: "products",
    label: "Products",
    used: 12,
    limit: 2_000,
    unit: "records"
  },
  { id: "orders", label: "Orders", used: 319, limit: 100_000, unit: "records" }
];

export const mockBillingInvoices: BillingInvoice[] = [
  {
    id: "invoice-demo-august",
    number: "DEMO-2026-008",
    amount_minor: 0,
    currency: "USD",
    status: "paid",
    issued_at: "2026-08-01T00:05:00Z",
    hosted_url: null
  },
  {
    id: "invoice-demo-july",
    number: "DEMO-2026-007",
    amount_minor: 0,
    currency: "USD",
    status: "paid",
    issued_at: "2026-07-01T00:05:00Z",
    hosted_url: null
  }
];

export const mockSettingsSnapshot: SettingsSnapshot = {
  organization_id: organizationId,
  profile: {
    display_name: "Jordan Blake",
    email: "jordan@northstar.example",
    locale: "en-US",
    time_zone: "America/New_York"
  },
  organization: {
    name: "Northstar Commerce",
    slug: "northstar-commerce",
    timezone: "America/New_York",
    reporting_currency: "USD",
    industry: "Retail",
    etag: '"1"'
  },
  preferences: {
    weekly_summary_email: true,
    insight_alert_email: true,
    product_updates_email: false,
    compact_tables: false
  },
  security: {
    password_change_allowed: false,
    demo_message:
      "Credential changes are unavailable in this isolated demo workspace."
  },
  data_controls: {
    export_available: false,
    deletion_allowed: false,
    demo_message: "Sensitive data controls are unavailable in demo workspaces."
  }
};
