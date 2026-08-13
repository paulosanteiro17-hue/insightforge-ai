import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BillingPage } from "@/components/administration/billing-page";
import { DataOnboardingStep } from "@/components/administration/onboarding-steps";
import { TeamMembersSection } from "@/components/administration/team-members";
import type { OnboardingDataChoice } from "@/lib/api/contracts";
import { resetAccountMockState } from "@/lib/api/mock-adapter";
import { mockOrganizations } from "@/lib/api/mock-fixtures";
import { mockTeamMembers } from "@/lib/api/mock-account-fixtures";
import { TestProviders } from "@/test/test-providers";

function DataChoiceHarness() {
  const [choice, setChoice] = useState<OnboardingDataChoice | null>(null);
  return (
    <DataOnboardingStep
      choice={choice}
      pending={false}
      onChoiceChange={setChoice}
      onBack={vi.fn()}
      onContinue={vi.fn()}
    />
  );
}

describe("administration page controls", () => {
  beforeEach(() => resetAccountMockState());

  it("requires an onboarding data choice before continuing", async () => {
    const user = userEvent.setup();
    render(<DataChoiceHarness />);

    const continueButton = screen.getByRole("button", { name: "Continue" });
    expect(continueButton).toBeDisabled();
    await user.click(screen.getByRole("radio", { name: /Use demo data/i }));
    expect(continueButton).toBeEnabled();
  });

  it("renders the final owner with protected role and removal controls", () => {
    render(
      <TeamMembersSection
        members={mockTeamMembers}
        currentRole="owner"
        rolePending={false}
        onRoleChange={vi.fn()}
        onRemove={vi.fn()}
      />
    );

    const ownerRow = screen.getByRole("row", { name: /Jordan Blake/i });
    expect(within(ownerRow).getByText("Final owner")).toBeInTheDocument();
    expect(
      within(ownerRow).getByRole("button", { name: "Remove" })
    ).toBeDisabled();
  });

  it("simulates a billing plan change without collecting payment", async () => {
    const user = userEvent.setup();
    render(<BillingPage organization={mockOrganizations[0]!} />, {
      wrapper: TestProviders
    });

    await screen.findByRole("heading", { name: "Billing" });
    await user.click(
      screen.getByRole("button", { name: "Use Business in demo" })
    );

    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(
        "No payment was collected"
      )
    );
  });
});
