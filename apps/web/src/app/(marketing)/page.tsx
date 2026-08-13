import type { Metadata } from "next";
import { LandingPage } from "@/components/marketing/landing-page";

export const metadata: Metadata = {
  title: "Business analytics that explains itself",
  description:
    "Turn revenue, customer, order, and product performance into clear decisions with grounded AI insight.",
  alternates: { canonical: "/" }
};

export default function HomePage() {
  return <LandingPage />;
}
