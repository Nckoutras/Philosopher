import { test, expect } from '@playwright/test';

/**
 * Day 3 UAT prerequisite checks.
 * No OTP automation, no credentials, no chat messages, no production mutations.
 *
 * Usage (from apps/web):
 *   npm exec --yes --package=@playwright/test playwright test tests/uat-day3.smoke.spec.ts
 *
 * To run the authenticated check, provide a locally stored auth state:
 *   WISE_ROOM_UAT_STORAGE_STATE=/absolute/path/to/state.json ...
 * NEVER commit storageState/cookies/tokens into git.
 */
const BASE = process.env.WISE_ROOM_UAT_BASE_URL || 'https://thewiseroom.app';
const ACCOUNT = process.env.WISE_ROOM_UAT_EXPECTED_EMAIL || 'nckoutras+uatpro1@gmail.com';
const AUTH = process.env.WISE_ROOM_UAT_STORAGE_STATE;

test('public homepage responds and is not a server error', async ({ page }) => {
  const response = await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  expect(response, 'navigation must return a response').not.toBeNull();
  expect(response!.status()).toBeLessThan(500);
  await expect(page.locator('body')).not.toBeEmpty();
});

test('authenticated UAT prerequisite: correct account, no OTP', async ({ browser }) => {
  test.skip(!AUTH, 'BLOCKED: no existing authenticated storage state; do not initiate OTP');
  const context = await browser.newContext({ storageState: AUTH });
  try {
    const page = await context.newPage();
    await page.goto(BASE + '/app/account', { waitUntil: 'domcontentloaded' });
    await expect(page.getByText(ACCOUNT, { exact: true })).toBeVisible({ timeout: 15000 });
    await expect(page).toHaveURL(/\/app\/account/);
  } finally {
    await context.close();
  }
});
