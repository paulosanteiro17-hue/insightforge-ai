import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type TestInfo } from "@playwright/test";

async function expectAccessible(page: Page, testInfo: TestInfo): Promise<void> {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();

  if (results.violations.length > 0) {
    await testInfo.attach("axe-violations", {
      body: JSON.stringify(results.violations, null, 2),
      contentType: "application/json"
    });
  }

  expect(results.violations).toEqual([]);
}

function recordBrowserErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  return errors;
}

test("public and authenticated product surfaces meet the accessibility gate", async ({
  page
}, testInfo) => {
  const browserErrors = recordBrowserErrors(page);

  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Turn business data into decisions/i })
  ).toBeVisible();
  await expectAccessible(page, testInfo);

  await page.goto("/app/northstar-commerce/overview?range=90d");
  await expect(page.getByText("Total revenue", { exact: true })).toBeVisible();
  await expectAccessible(page, testInfo);

  await page.goto("/app/northstar-commerce/ai-insights?range=30d");
  await expect(
    page.getByRole("heading", {
      name: "Discount mix is putting pressure on order value"
    })
  ).toBeVisible();
  await expectAccessible(page, testInfo);

  expect(browserErrors).toEqual([]);
});

test("Ask Your Data remains accessible after an answer is rendered", async ({
  page
}, testInfo) => {
  const browserErrors = recordBrowserErrors(page);

  await page.goto("/app/northstar-commerce/ask-your-data?range=30d");
  await page
    .getByRole("button", { name: /Top product.*generated the most revenue/i })
    .click();
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(
    page.getByText("Grounded answer", { exact: true })
  ).toBeVisible();
  await expectAccessible(page, testInfo);

  expect(browserErrors).toEqual([]);
});
