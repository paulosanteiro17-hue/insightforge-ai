import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3107";
const skipWebServer = process.env.PLAYWRIGHT_SKIP_WEBSERVER === "1";
const portfolioCapture = process.env.CAPTURE_PORTFOLIO === "1";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  workers: process.env.CI ? 2 : 4,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "list",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL,
    navigationTimeout: 30_000,
    trace: "on-first-retry"
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ],
  webServer: skipWebServer
    ? undefined
    : {
        command: portfolioCapture
          ? "npm run build && npm run start -- --port 3107"
          : "npm run dev -- --port 3107",
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
        env: {
          ...process.env,
          INSIGHTFORGE_API_MODE: "mock",
          ...(portfolioCapture
            ? { INSIGHTFORGE_STANDARD_START: "1" }
            : undefined)
        }
      }
});
