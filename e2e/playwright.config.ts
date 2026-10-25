import { defineConfig, devices } from "@playwright/test";

const CI = Boolean(process.env.CI);
const WEB_URL = process.env.E2E_BASE_URL ?? "http://localhost:5173";

export default defineConfig({
  testDir: "./tests",
  // Tests share one seeded database; running them in order keeps results predictable.
  workers: 1,
  fullyParallel: false,
  retries: CI ? 1 : 0,
  reporter: CI ? [["list"], ["html", { open: "never" }]] : [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: WEB_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    timezoneId: "Asia/Kolkata",
    locale: "en-IN",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : [
        {
          command: "uv run python -m scripts.e2e_server",
          cwd: "../apps/api",
          url: "http://127.0.0.1:8000/api/v1/health",
          reuseExistingServer: !CI,
          timeout: 120_000,
          stdout: "pipe",
        },
        {
          command: "pnpm --filter @berth/web dev --port 5173 --strictPort",
          cwd: "..",
          url: WEB_URL,
          reuseExistingServer: !CI,
          timeout: 60_000,
        },
      ],
});
