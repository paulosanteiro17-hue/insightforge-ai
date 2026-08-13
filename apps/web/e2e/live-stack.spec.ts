import { expect, test } from "@playwright/test";

test.skip(
  process.env.PLAYWRIGHT_LIVE_STACK !== "1",
  "Runs only against the integrated API, worker, PostgreSQL, and production web stack."
);

test("the production stack completes a tenant-scoped AI and report journey", async ({
  page
}) => {
  test.setTimeout(120_000);

  await page.goto("/");
  await page.getByRole("link", { name: "Explore the live demo" }).click();
  await page.getByRole("button", { name: "Open Demo Owner workspace" }).click();

  await expect(page).toHaveURL(/\/app\/[^/]+\/overview$/);
  await expect(
    page.getByRole("heading", { name: "Welcome back." })
  ).toBeVisible();
  await expect(
    page.getByText("Revenue", { exact: true }).first()
  ).toBeVisible();

  await page.getByRole("link", { name: "AI Insights", exact: true }).click();
  await expect(page).toHaveURL(/\/ai-insights$/);
  await page.getByRole("button", { name: "Regenerate insights" }).click();
  await expect(page.getByRole("status")).toContainText(
    "grounded insights were generated",
    {
      timeout: 45_000
    }
  );
  await expect(
    page.getByText("Tenant analytics", { exact: true }).first()
  ).toBeVisible();

  await page.getByRole("link", { name: "Reports", exact: true }).click();
  await expect(page).toHaveURL(/\/reports$/);
  await page.locator("form").getByLabel("Report type").selectOption("sales");
  await page.getByRole("button", { name: "Generate CSV report" }).click();
  await expect(page.getByRole("status")).toContainText("is ready to download", {
    timeout: 45_000
  });

  const readyReport = page
    .getByRole("row")
    .filter({ hasText: "Sales Report" })
    .first();
  const downloadPromise = page.waitForEvent("download");
  await readyReport.getByRole("button", { name: "Download CSV" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.csv$/);
});
