import {
  BarChart3,
  Bot,
  FileUp,
  Gauge,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  UsersRound
} from "lucide-react";

export const benefitItems = [
  {
    title: "See the whole business",
    description:
      "Bring revenue, orders, customers, and product performance into one coherent operating view.",
    icon: Gauge
  },
  {
    title: "Understand every movement",
    description:
      "Compare periods, expose the drivers behind a trend, and keep every metric grounded in the same definitions.",
    icon: ScanSearch
  },
  {
    title: "Act on the next signal",
    description:
      "Translate patterns into concise opportunities, risks, and weekly priorities your team can use immediately.",
    icon: Sparkles
  }
];

export const featureItems = [
  {
    title: "Executive analytics",
    description:
      "A portfolio-grade dashboard with revenue, customer, order, and recurring-growth signals.",
    icon: BarChart3,
    accent: "teal"
  },
  {
    title: "AI-guided insight",
    description:
      "Grounded explanations are generated from calculated aggregates—not unbounded database access.",
    icon: Bot,
    accent: "coral"
  },
  {
    title: "Safe data imports",
    description:
      "Preview, validate, and commit private CSV uploads through a durable, auditable workflow.",
    icon: FileUp,
    accent: "ink"
  },
  {
    title: "Built for teams",
    description:
      "Owner, Admin, and Member roles keep organization access clear as the business grows.",
    icon: UsersRound,
    accent: "teal"
  },
  {
    title: "Tenant-first security",
    description:
      "Every business request is scoped to an authorized organization and checked again by the API.",
    icon: ShieldCheck,
    accent: "ink"
  },
  {
    title: "Ask with guardrails",
    description:
      "Natural-language questions map to controlled analytical intents—never arbitrary model-authored SQL.",
    icon: ScanSearch,
    accent: "coral"
  }
] as const;

export const workflowSteps = [
  {
    number: "01",
    title: "Connect the signal",
    description:
      "Start instantly with a realistic demo workspace or validate your own structured CSV data."
  },
  {
    number: "02",
    title: "Measure what changed",
    description:
      "InsightForge applies consistent business definitions across dashboards, reports, and comparisons."
  },
  {
    number: "03",
    title: "Move with context",
    description:
      "Use grounded AI summaries and controlled questions to turn movement into a clear next action."
  }
];

export const plans = [
  {
    name: "Free",
    price: "$0",
    description: "For a focused view of early business momentum.",
    features: [
      "One workspace",
      "Core analytics",
      "CSV imports",
      "Deterministic insights"
    ],
    featured: false
  },
  {
    name: "Pro",
    price: "$49",
    description: "For growing teams turning data into a weekly rhythm.",
    features: [
      "Five team members",
      "AI insights",
      "Ask Your Data",
      "Scheduled reports"
    ],
    featured: true
  },
  {
    name: "Business",
    price: "$149",
    description: "For multi-team operations that need deeper control.",
    features: [
      "Unlimited members",
      "Advanced reporting",
      "Priority processing",
      "Audit history"
    ],
    featured: false
  }
];
