import { beforeEach, describe, expect, it } from "vitest";
import { insightForgeApi, resetAccountMockState } from "@/lib/api/mock-adapter";
import { mockOrganizations } from "@/lib/api/mock-fixtures";

describe("account administration mock adapter", () => {
  const organization = mockOrganizations[0]!;

  beforeEach(() => resetAccountMockState());

  it("persists every onboarding step before completing setup", async () => {
    await expect(
      insightForgeApi.onboarding.complete(organization.id)
    ).rejects.toMatchObject({ problem: { code: "onboarding_incomplete" } });

    await insightForgeApi.onboarding.saveOrganization(organization.id, {
      name: "Northstar Commerce",
      slug: "northstar-commerce",
      timezone: "America/New_York",
      reporting_currency: "USD",
      industry: "Retail"
    });
    await insightForgeApi.onboarding.chooseData(organization.id, {
      choice: "csv"
    });
    await insightForgeApi.onboarding.saveProfile(organization.id, {
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
    });
    const completed = await insightForgeApi.onboarding.complete(
      organization.id
    );

    expect(completed.current_step).toBe("complete");
    expect(completed.completed_at).not.toBeNull();
    expect(completed.data_choice).toBe("csv");
  });

  it("supports local team changes while enforcing demo and final-owner guards", async () => {
    const changed = await insightForgeApi.team.changeRole(
      organization.id,
      "member-maya-chen",
      "member"
    );
    expect(changed.role).toBe("member");

    await expect(
      insightForgeApi.team.removeMember(
        organization.id,
        "01914d2e-50a3-7c44-a9bc-5f98cf7bf810"
      )
    ).rejects.toMatchObject({ problem: { code: "final_owner_required" } });
    await expect(
      insightForgeApi.team.invite(organization.id, {
        email: "new@northstar.example",
        role: "member"
      })
    ).rejects.toMatchObject({
      problem: { code: "demo_policy_restriction" }
    });

    await insightForgeApi.team.revokeInvitation(
      organization.id,
      "invite-riley-stone"
    );
    const overview = await insightForgeApi.team.getOverview(organization.id);
    expect(
      overview.invitations.find((item) => item.id === "invite-riley-stone")
        ?.status
    ).toBe("revoked");
  });

  it("changes only demo billing state and never returns a charge", async () => {
    const result = await insightForgeApi.billing.changePlan(
      organization.id,
      "business"
    );
    const overview = await insightForgeApi.billing.getOverview(organization.id);

    expect(result.charged_amount_minor).toBe(0);
    expect(result.feedback).toMatch(/No payment was collected/i);
    expect(overview.subscription.plan).toBe("business");
    expect(overview.subscription.provider).toBe("demo");
  });

  it("allows settings updates and export while blocking protected account actions", async () => {
    const updated = await insightForgeApi.settings.updateProfile(
      organization.id,
      {
        display_name: "Jordan Blake",
        locale: "en-US",
        time_zone: "America/New_York"
      }
    );
    expect(updated.profile.display_name).toBe("Jordan Blake");

    const artifact = await insightForgeApi.settings.requestExport(
      organization.id
    );
    expect(artifact.filename).toMatch(/\.json$/);
    expect(JSON.parse(artifact.content)).toMatchObject({
      billing: { provider: "demo", payment_collected: false }
    });

    await expect(
      insightForgeApi.settings.changePassword(organization.id, {
        current_password: "current-password",
        new_password: "new-secure-password"
      })
    ).rejects.toMatchObject({
      problem: { code: "demo_policy_restriction" }
    });
    await expect(
      insightForgeApi.settings.deleteOrganization(
        organization.id,
        "Northstar Commerce"
      )
    ).rejects.toMatchObject({
      problem: { code: "demo_policy_restriction" }
    });
  });
});
