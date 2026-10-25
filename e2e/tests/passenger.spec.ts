import { expect, test } from "@playwright/test";

import {
  DECLINE_CARD,
  DELHI,
  MUMBAI,
  TRAVEL_DATE,
  bookAndPay,
  evidence,
  register,
  resultsUrl,
} from "./helpers";

test("ST-01 guest searches trains and sees availability and fares", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("combobox", { name: "From" }).fill("New Del");
  await page.getByRole("option", { name: /New Delhi/ }).click();
  await page.getByRole("combobox", { name: "To" }).fill("MMCT");
  await page.getByRole("option", { name: /Mumbai Central/ }).click();
  await page.getByLabel("Journey date").fill(TRAVEL_DATE);
  await evidence(page, "st01-search-form");
  await page.getByRole("button", { name: "Search trains" }).click();

  await expect(page.getByRole("heading", { name: "New Delhi to Mumbai Central" })).toBeVisible();
  const train = page.getByRole("article").filter({ hasText: "22401" });
  await expect(train).toContainText("Capital Western Express");
  await expect(train).toContainText("16:30");
  await expect(train).toContainText("Available");
  await expect(train.getByRole("button", { name: "Book SL on 22401" })).toBeEnabled();
  await evidence(page, "st01-search-results");
});

test("ST-02 and ST-14 a passenger books, pays and downloads the e-ticket", async ({ page }) => {
  await register(page);
  await page.goto(resultsUrl(DELHI, MUMBAI));
  const screens: string[] = [];
  page.on("framenavigated", (frame) => {
    if (frame === page.mainFrame()) screens.push(new URL(frame.url()).pathname);
  });

  await page.getByRole("button", { name: "Book 3A on 22401" }).click();
  await page.getByLabel("Passenger 1 name").fill("Riya Kapoor");
  await page.getByLabel("Age").first().fill("29");
  await page.getByLabel("Gender").first().selectOption({ label: "Female" });
  await page.getByRole("button", { name: "Add passenger" }).click();
  await page.getByLabel("Passenger 2 name").fill("Arjun Kapoor");
  await page.getByLabel("Age").nth(1).fill("31");
  await page.getByLabel("Gender").nth(1).selectOption({ label: "Male" });
  await expect(page.getByText("Total for 2")).toBeVisible();
  await evidence(page, "st02-passenger-details");
  await page.getByRole("button", { name: "Continue to payment" }).click();

  await expect(page.getByRole("heading", { name: "Payment" })).toBeVisible();
  await page.getByLabel("Card number").fill("4111 1111 1111 1111");
  await evidence(page, "st02-payment");
  await page.getByRole("button", { name: /^Pay / }).click();

  await expect(page.getByRole("heading", { name: /^PNR \d{10}$/ })).toBeVisible();
  await expect(page.getByText("All passengers have confirmed berths.")).toBeVisible();
  await expect(page.getByRole("row").filter({ hasText: "Riya Kapoor" })).toContainText(/CNF\/B\d/);
  await evidence(page, "st02-confirmation");

  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download e-ticket (PDF)" }).click();
  expect((await download).suggestedFilename()).toMatch(/^berth-ticket-\d{10}\.pdf$/);

  // Results -> passenger details -> payment -> confirmation (NFR-11: at most 5 screens).
  expect(new Set(screens).size).toBeLessThanOrEqual(5);
});

test("ST-04 a declined payment can be retried", async ({ page }) => {
  await register(page, "Dev Malhotra");
  await page.goto(resultsUrl(DELHI, MUMBAI));
  await bookAndPay(page, "22401", "SL", [{ name: "Dev Malhotra", age: 40, gender: "Male" }], DECLINE_CARD);

  await expect(page.getByRole("alert")).toContainText("Declined by the issuing bank");
  await evidence(page, "st04-declined");
  await page.getByLabel("Card number").fill("4111 1111 1111 1111");
  await page.getByRole("button", { name: /^Pay / }).click();
  await expect(page.getByRole("heading", { name: /^PNR \d{10}$/ })).toBeVisible();
});

test("ST-03 and ST-05 my bookings, partial cancellation and public PNR status", async ({
  page,
  browser,
}) => {
  await register(page, "Meera Iyer");
  await page.goto(resultsUrl(DELHI, MUMBAI));
  await bookAndPay(page, "22401", "SL", [
    { name: "Meera Iyer", age: 35, gender: "Female" },
    { name: "Kabir Iyer", age: 8, gender: "Male" },
  ]);
  const pnr = (await page.getByRole("heading", { name: /^PNR / }).textContent())!.slice(4);

  await page.getByRole("link", { name: "My bookings" }).click();
  await expect(page.getByRole("heading", { name: "Upcoming journeys" })).toBeVisible();
  await expect(page.getByText(`PNR ${pnr}`)).toBeVisible();
  await evidence(page, "st03-my-bookings");
  await page.getByText(`PNR ${pnr}`).click();

  await page.getByLabel("Select Kabir Iyer for cancellation").check();
  await page.getByRole("button", { name: "Check refund for 1 passenger" }).click();
  await expect(page.getByText(/^Refund: ₹/)).toBeVisible();
  await evidence(page, "st03-refund-quote");
  await page.getByRole("button", { name: "Confirm cancellation" }).click();
  await expect(page.getByRole("row").filter({ hasText: "Kabir Iyer" })).toContainText("Cancelled");
  await expect(page.getByText("Refunded")).toBeVisible();
  await evidence(page, "st03-after-cancellation");

  const guest = await browser.newPage();
  await guest.goto("/pnr");
  await guest.getByLabel("PNR number").fill(pnr);
  await guest.getByRole("button", { name: "Check status" }).click();
  // The first two letters of each word stay visible: "Iyer" becomes "Iy**".
  await expect(guest.getByRole("cell", { name: "Me*** Iy**" })).toBeVisible();
  await expect(guest.getByRole("cell", { name: "Ka*** Iy**" })).toBeVisible();
  await evidence(guest, "st05-pnr-status");
  await guest.close();
});
