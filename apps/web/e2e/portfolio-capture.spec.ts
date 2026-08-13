import path from "node:path";
import { expect, test } from "@playwright/test";

test.skip(
  process.env.CAPTURE_PORTFOLIO !== "1",
  "Runs only when refreshing the reviewed portfolio screenshot set."
);

const screenshotDirectory = path.resolve(
  __dirname,
  "../../../docs/screenshots"
);

function screenshotPath(filename: string): string {
  return path.join(screenshotDirectory, filename);
}

test("capture the reviewed desktop portfolio set", async ({ page }) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1440, height: 1100 });

  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Turn business data into decisions/i })
  ).toBeVisible();
  await page.screenshot({
    path: screenshotPath("01-landing-page.png"),
    fullPage: true
  });

  await page.goto("/app/northstar-commerce/overview?range=90d");
  await expect(
    page.getByRole("heading", { name: "Welcome back." })
  ).toBeVisible();
  await expect(page.getByText("Total revenue", { exact: true })).toBeVisible();
  await page.screenshot({
    path: screenshotPath("02-overview-dashboard.png"),
    fullPage: true
  });

  await page.goto("/app/northstar-commerce/analytics?range=90d");
  await expect(page.getByRole("heading", { name: "Analytics" })).toBeVisible();
  await expect(page.getByText("Net revenue", { exact: true })).toBeVisible();
  await page.screenshot({
    path: screenshotPath("03-analytics.png"),
    fullPage: true
  });

  await page.goto("/app/northstar-commerce/customers");
  await expect(page.getByRole("heading", { name: "Customers" })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "James Okafor", exact: true })
  ).toBeVisible();
  await page.screenshot({
    path: screenshotPath("04-customers.png"),
    fullPage: true
  });

  await page.goto("/app/northstar-commerce/ai-insights?range=30d");
  await expect(
    page.getByRole("heading", { name: "AI Insights" })
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Discount mix is putting pressure on order value"
    })
  ).toBeVisible();
  await page.screenshot({
    path: screenshotPath("05-ai-insights.png"),
    fullPage: true
  });

  await page.goto("/app/northstar-commerce/ask-your-data?range=30d");
  await page
    .getByRole("button", { name: /Top product.*generated the most revenue/i })
    .click();
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(
    page.getByText("Grounded answer", { exact: true })
  ).toBeVisible();
  await expect(page.getByText("Atlas revenue", { exact: true })).toBeVisible();
  await page.screenshot({
    path: screenshotPath("06-ask-your-data.png"),
    fullPage: true
  });

  await page.goto("/app/northstar-commerce/reports");
  await expect(page.getByRole("heading", { name: "Reports" })).toBeVisible();
  await expect(
    page.getByRole("table", { name: "Generated report history" })
  ).toBeVisible();
  await page.screenshot({
    path: screenshotPath("07-reports.png"),
    fullPage: true
  });
});

test("capture the reviewed mobile dashboard", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/app/northstar-commerce/overview?range=30d");
  await expect(
    page.getByRole("heading", { name: "Welcome back." })
  ).toBeVisible();
  await expect(page.getByText("Total revenue", { exact: true })).toBeVisible();
  await page.screenshot({
    path: screenshotPath("08-mobile-dashboard.png"),
    fullPage: true
  });
});
