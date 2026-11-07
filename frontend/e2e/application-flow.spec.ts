import { test, expect, request as pwRequest, type Page, type Browser } from '@playwright/test';
import fs from 'node:fs';

/**
 * Candidate application flow, end to end through the real UI, API and database.
 *
 * Needs the backend on :8000 started with a mail-capturing harness that appends every
 * outgoing email as a JSON line to $E2E_MAIL_FILE (emails are how guests get their links),
 * and the Vite dev server on :3000. Test data uses e2e-<tag>@example.com addresses.
 */

const TAG = Math.random().toString(36).slice(2, 8);
const MAIL_FILE = process.env.E2E_MAIL_FILE || '';
const SHOTS = process.env.E2E_SHOTS || '';
const API = 'http://localhost:3000';

const ORG_EMAIL = `e2e-${TAG}-org@example.com`;
const ORG_PASSWORD = 'e2e-org-pass-1';
const ALICE = `e2e-${TAG}-alice@example.com`;
const BOB = `e2e-${TAG}-bob@example.com`;
const CAROL = `e2e-${TAG}-carol@example.com`;
const PASSWORD = 'e2e-cand-pass-1';
const TITLE = `E2E Backend Engineer ${TAG}`;

type Mail = { to: string; subject: string; template: string; vars: Record<string, string> };

function readMails(): Mail[] {
  if (!MAIL_FILE || !fs.existsSync(MAIL_FILE)) return [];
  return fs.readFileSync(MAIL_FILE, 'utf-8').split('\n').filter(Boolean).map(l => JSON.parse(l));
}

async function waitForMail(to: string, template: string, timeout = 20000): Promise<Mail> {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const found = readMails().filter(m => m.to.toLowerCase() === to.toLowerCase() && m.template === template);
    if (found.length) return found[found.length - 1];
    await new Promise(r => setTimeout(r, 300));
  }
  throw new Error(`No ${template} email to ${to} within ${timeout}ms`);
}

/** Emails carry absolute URLs built from APP_URL; the browser must stay on the dev server. */
const localPath = (url: string) => {
  const u = new URL(url);
  return u.pathname + u.search;
};

/** Minimal valid text PDF (with xref table). */
function buildPdf(text: string): Buffer {
  const stream = `BT /F1 12 Tf 20 150 Td (${text}) Tj ET`;
  const objects = [
    '<</Type/Catalog/Pages 2 0 R>>',
    '<</Type/Pages/Kids[3 0 R]/Count 1>>',
    '<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 300]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>',
    `<</Length ${stream.length}>>\nstream\n${stream}\nendstream`,
    '<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>',
  ];
  let out = '%PDF-1.4\n';
  const offsets: number[] = [];
  objects.forEach((body, i) => {
    offsets.push(out.length);
    out += `${i + 1} 0 obj\n${body}\nendobj\n`;
  });
  const xref = out.length;
  out += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  offsets.forEach(o => { out += `${String(o).padStart(10, '0')} 00000 n \n`; });
  out += `trailer<</Size ${objects.length + 1}/Root 1 0 R>>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(out, 'latin1');
}

const cvFile = (name: string) => ({
  name,
  mimeType: 'application/pdf',
  buffer: buildPdf('Senior Python developer. Built REST APIs with Postgres and SQL for 6 years.'),
});

async function shot(page: Page, name: string) {
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
}

/** Fail a test on uncaught page errors (not on expected 4xx network noise). */
function trackPageErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  return errors;
}

let listingId = '';
let orgTokens: { access_token: string; refresh_token: string };
let orgId = '';
let aliceSession = '';

async function orgPage(browser: Browser) {
  const ctx = await browser.newContext();
  await ctx.addInitScript(([tokens, org]) => {
    localStorage.setItem('auth_tokens', tokens as string);
    localStorage.setItem('active_org_id', org as string);
  }, [JSON.stringify(orgTokens), orgId]);
  return { ctx, page: await ctx.newPage() };
}

test.describe.configure({ mode: 'serial' });

test.describe('candidate application flow', () => {
  test.beforeAll(async () => {
    expect(MAIL_FILE, 'E2E_MAIL_FILE must point at the mail-capturing backend harness').not.toBe('');
    const api = await pwRequest.newContext({ baseURL: API });
    const reg = await api.post('/api/v1/auth/register', {
      data: { email: ORG_EMAIL, password: ORG_PASSWORD, name: 'E2E Owner', org_name: `E2E Org ${TAG}` },
    });
    expect(reg.ok(), await reg.text()).toBeTruthy();
    const body = await reg.json();
    orgTokens = body.tokens;
    orgId = (body.memberships?.[0]?.org_id) || '';
    if (!orgId) {
      const me = await (await api.get('/api/v1/auth/me', { headers: { Authorization: `Bearer ${orgTokens.access_token}` } })).json();
      orgId = me.memberships[0].org_id;
    }
    const auth = { Authorization: `Bearer ${orgTokens.access_token}`, 'X-Org-Id': orgId };
    const roles = await (await api.get('/api/v1/it/roles?active_only=true', { headers: auth })).json();
    const roleId = (Array.isArray(roles) ? roles : roles.items)[0].id;
    const listing = await api.post('/api/v1/marketplace/interviews', {
      headers: auth,
      data: { title: TITLE, it_role_id: roleId, description: 'Build and run APIs.', skills_required: 'python, sql', interview_mode: 'typing' },
    });
    expect(listing.ok(), await listing.text()).toBeTruthy();
    listingId = (await listing.json()).id;
  });

  test('guest must attach a CV to apply', async ({ page }) => {
    const errors = trackPageErrors(page);
    await page.goto(`/opportunity-hub/interviews/${listingId}`);
    await expect(page.getByRole('heading', { name: TITLE })).toBeVisible();
    await shot(page, '01-apply-form');
    await page.getByLabel('Your Name').fill('Alice Rivera');
    await page.getByLabel('Email Address').fill(ALICE);
    await page.getByRole('button', { name: /submit application/i }).click();
    await expect(page.getByRole('alert')).toContainText(/upload your cv/i);
    await expect(page.getByText('Application submitted')).toHaveCount(0);
    expect(errors).toEqual([]);
  });

  test('non-PDF CV is rejected in the browser', async ({ page }) => {
    await page.goto(`/opportunity-hub/interviews/${listingId}`);
    await page.locator('input[type=file]').setInputFiles({ name: 'cv.docx', mimeType: 'application/msword', buffer: Buffer.from('x') });
    await expect(page.getByRole('alert')).toContainText(/pdf/i);
  });

  for (const [who, email] of [['Alice Rivera', ALICE], ['Bob Stone', BOB]] as const) {
    test(`guest ${who.split(' ')[0]} applies with a CV and gets a confirmation email`, async ({ page }) => {
      const errors = trackPageErrors(page);
      await page.goto(`/opportunity-hub/interviews/${listingId}`);
      await page.getByLabel('Your Name').fill(who);
      await page.getByLabel('Email Address').fill(email);
      await page.locator('input[type=file]').setInputFiles(cvFile(`${who.split(' ')[0].toLowerCase()}-cv.pdf`));
      await expect(page.getByText(/-cv\.pdf/)).toBeVisible();
      await page.getByRole('button', { name: /submit application/i }).click();
      await expect(page.getByRole('status').getByText('Application submitted')).toBeVisible({ timeout: 60_000 });
      await expect(page.getByText(/check your email/i)).toBeVisible();
      await shot(page, `02-applied-${who.split(' ')[0].toLowerCase()}`);
      const mail = await waitForMail(email, 'application_received.html');
      expect(mail.vars.JOB_ROLE).toBe(TITLE);
      expect(errors).toEqual([]);
    });
  }

  test('org reviews the applicant: auto-evaluation, fit details, CV download', async ({ browser }) => {
    const { ctx, page } = await orgPage(browser);
    const errors = trackPageErrors(page);
    await page.goto('/org/applications');
    await expect(page.getByRole('heading', { name: 'Applications' })).toBeVisible();
    const alice = page.locator('div.glass', { hasText: ALICE });
    await expect(alice).toBeVisible();
    await expect(alice.getByText('Fit 7.4/10')).toBeVisible({ timeout: 45000 }); // background evaluation finished
    await expect(alice.getByText('Solid Python/API background')).toBeVisible();

    await alice.getByRole('button', { name: /show fit details/i }).click();
    await expect(alice.getByTestId('fit-breakdown')).toContainText('Matched competencies');
    await expect(alice.getByTestId('fit-breakdown')).toContainText('Walk through a production incident');
    await shot(page, '03-org-applications');

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      alice.getByRole('button', { name: 'CV', exact: true }).click(),
    ]);
    expect(download.suggestedFilename()).toBe('alice-cv.pdf');
    expect(errors).toEqual([]);
    await ctx.close();
  });

  test('org invites Alice and Bob; invitation emails are sent', async ({ browser }) => {
    const { ctx, page } = await orgPage(browser);
    await page.goto('/org/applications');
    for (const email of [ALICE, BOB]) {
      const card = page.locator('div.glass', { hasText: email });
      await expect(card.getByRole('button', { name: /^invite$/i })).toBeVisible({ timeout: 30000 });
      await card.getByRole('button', { name: /^invite$/i }).click();
      await expect(card.getByText(/invitation sent/i)).toBeVisible();
      const mail = await waitForMail(email, 'application_invitation.html');
      expect(mail.vars.INVITE_URL).toContain('/application-invite/');
    }
    await shot(page, '04-org-invited');
    await ctx.close();
  });

  test('guest accepts the emailed invitation without an account and lands in the interview', async ({ browser }) => {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    const errors = trackPageErrors(page);
    const mail = await waitForMail(ALICE, 'application_invitation.html');
    await page.goto(localPath(mail.vars.INVITE_URL));
    await expect(page.getByRole('heading', { name: /you're invited to interview/i })).toBeVisible();
    await expect(page.getByText(TITLE)).toBeVisible();
    await expect(page.getByText(ALICE, { exact: true })).toBeVisible();
    await shot(page, '05-invite-page');
    await page.getByRole('button', { name: /accept & start interview/i }).click();
    await page.waitForURL(/\/interview\/[0-9a-f-]{36}/);
    aliceSession = page.url().split('/interview/')[1].split('?')[0];
    expect(errors).toEqual([]);
    await ctx.close();
  });

  test('reopening the accepted invite link still leads to the interview', async ({ browser }) => {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    const mail = await waitForMail(ALICE, 'application_invitation.html');
    await page.goto(localPath(mail.vars.INVITE_URL));
    await expect(page.getByRole('button', { name: /continue to your interview/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /accept/i })).toHaveCount(0);
    await ctx.close();
  });

  test('guest can decline an invitation', async ({ browser }) => {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    const mail = await waitForMail(BOB, 'application_invitation.html');
    await page.goto(localPath(mail.vars.INVITE_URL));
    await page.getByRole('button', { name: /^decline$/i }).click();
    await expect(page.getByText(/you declined this invitation/i)).toBeVisible();
    await shot(page, '06-declined');
    await ctx.close();
  });

  test('a bad invitation link shows a clear message', async ({ page }) => {
    await page.goto('/application-invite/not-a-real-token');
    await expect(page.getByRole('heading', { name: /invitation not found/i })).toBeVisible();
  });

  test('org sees the replies', async ({ browser }) => {
    const { ctx, page } = await orgPage(browser);
    await page.goto('/org/applications');
    await expect(page.locator('div.glass', { hasText: ALICE }).getByText('Accepted', { exact: true })).toBeVisible();
    await expect(page.locator('div.glass', { hasText: BOB }).getByText('Declined', { exact: true })).toBeVisible();
    await ctx.close();
  });

  test('registering with a guest email sends a claim link instead of creating an account', async ({ page }) => {
    const errors = trackPageErrors(page);
    await page.goto('/candidate/register');
    await page.getByLabel('Full Name').fill('Alice Rivera');
    await page.getByLabel('Email').fill(ALICE);
    await page.getByLabel('Password').fill(PASSWORD);
    await page.getByRole('button', { name: /create account/i }).click();
    await expect(page.getByText('Check your email')).toBeVisible();
    await shot(page, '07-claim-pending');
    await expect(page).toHaveURL(/\/candidate\/register/); // not signed in
    expect(errors).toEqual([]);
  });

  test('the claim link attaches the guest history to the new account', async ({ page }) => {
    const errors = trackPageErrors(page);
    const mail = await waitForMail(ALICE, 'account_claim.html');
    await page.goto(localPath(mail.vars.CLAIM_URL));
    await expect(page.getByRole('heading', { name: /finish setting up your account/i })).toBeVisible();
    await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
    await page.getByLabel('Confirm password').fill('different-pass-1');
    await page.getByRole('button', { name: /create my account/i }).click();
    await expect(page.getByRole('alert')).toContainText(/do not match/i);
    await page.getByLabel('Confirm password').fill(PASSWORD);
    await page.getByRole('button', { name: /create my account/i }).click();
    await page.waitForURL('**/candidate/applications');
    await expect(page.getByText(TITLE)).toBeVisible();
    await expect(page.getByText('Interview accepted')).toBeVisible();
    await expect(page.getByText('alice-cv.pdf')).toBeVisible();
    await expect(page.getByText(/fit 7\.4\/10/i)).toBeVisible();
    await expect(page.getByRole('link', { name: /start interview/i })).toBeVisible();
    await shot(page, '08-claimed-applications');
    expect(errors).toEqual([]);
  });

  test('the claim link works only once', async ({ page }) => {
    const mail = await waitForMail(ALICE, 'account_claim.html');
    await page.goto(localPath(mail.vars.CLAIM_URL));
    await page.getByLabel('Password', { exact: true }).fill('another-pass-123');
    await page.getByLabel('Confirm password').fill('another-pass-123');
    await page.getByRole('button', { name: /create my account/i }).click();
    await expect(page.getByRole('alert')).toContainText(/invalid or has expired/i);
  });

  test('a new candidate registers, verifies their email from the link, and the banner goes away', async ({ page }) => {
    const errors = trackPageErrors(page);
    await page.goto('/candidate/register');
    await page.getByLabel('Full Name').fill('Carol Park');
    await page.getByLabel('Email').fill(CAROL);
    await page.getByLabel('Password').fill(PASSWORD);
    await page.getByRole('button', { name: /create account/i }).click();
    await page.waitForURL('**/candidate/dashboard');
    await expect(page.getByText('Verify your email', { exact: true })).toBeVisible();
    await page.goto('/candidate/applications');
    await expect(page.getByText(/verify your email to see your applications/i)).toBeVisible();
    await shot(page, '09-unverified-applications');

    const mail = await waitForMail(CAROL, 'verification.html');
    await page.goto(localPath(mail.vars.VERIFY_URL));
    await expect(page.getByRole('heading', { name: 'Email verified' })).toBeVisible();
    await page.getByRole('link', { name: /my applications/i }).click();
    await expect(page.getByText(/no applications yet/i)).toBeVisible();
    await page.goto('/candidate/dashboard');
    await expect(page.getByText('Verify your email', { exact: true })).toHaveCount(0);
    expect(errors).toEqual([]);
  });

  test('a used verification link is reported clearly', async ({ page }) => {
    const mail = await waitForMail(CAROL, 'verification.html');
    await page.goto(localPath(mail.vars.VERIFY_URL));
    await expect(page.getByRole('heading', { name: 'Verification failed' })).toBeVisible();
  });

  test('forgot password: emailed link, new password, sign in', async ({ page }) => {
    const errors = trackPageErrors(page);
    await page.goto('/candidate/login');
    await page.getByRole('link', { name: /forgot password/i }).click();
    await expect(page).toHaveURL(/\/candidate\/forgot-password/);
    await page.getByLabel('Email').fill(CAROL);
    await page.getByRole('button', { name: /send reset link/i }).click();
    await expect(page.getByText(/a reset link is on its way/i)).toBeVisible();

    const mail = await waitForMail(CAROL, 'password_reset.html');
    await page.goto(localPath(mail.vars.RESET_URL));
    await page.getByLabel('New password').fill('brand-new-pass-9');
    await page.getByLabel('Confirm password').fill('brand-new-pass-9');
    await page.getByRole('button', { name: /update password/i }).click();
    await expect(page.getByText(/password updated/i)).toBeVisible();
    await page.waitForURL('**/candidate/login');

    await page.getByLabel('Email').fill(CAROL);
    await page.getByLabel('Password').fill('brand-new-pass-9');
    await page.getByRole('button', { name: /^sign in$/i }).click();
    await page.waitForURL('**/candidate/dashboard');
    expect(errors).toEqual([]);
  });

  test('wrong password is rejected at sign in', async ({ page }) => {
    await page.goto('/candidate/login');
    await page.getByLabel('Email').fill(CAROL);
    await page.getByLabel('Password').fill('definitely-wrong-1');
    await page.getByRole('button', { name: /^sign in$/i }).click();
    await expect(page.getByText(/invalid email or password/i)).toBeVisible();
  });

  test('someone with only the interview URL (no access token) is refused', async ({ browser }) => {
    expect(aliceSession).not.toBe('');
    const ctx = await browser.newContext(); // fresh browser: no sessionStorage token, no login
    const page = await ctx.newPage();
    await page.goto(`/interview/${aliceSession}`);
    await page.getByRole('button', { name: /i understand/i }).click();
    await expect(page.getByText(/you don't have access to this interview/i)).toBeVisible({ timeout: 60_000 });
    await shot(page, '10-interview-denied');
    await ctx.close();
  });

  test('the guest runs the interview: first question, an answer, then the next question', async ({ browser }) => {
    test.setTimeout(480_000);
    expect(aliceSession).not.toBe('');
    // Re-enter through the invitation like the guest would (this stores the per-session access token).
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    const errors = trackPageErrors(page);
    const mail = await waitForMail(ALICE, 'application_invitation.html');
    await page.goto(localPath(mail.vars.INVITE_URL));
    await page.getByRole('button', { name: /continue to your interview/i }).click();
    await page.waitForURL(/\/interview\//);
    await page.getByRole('button', { name: /i understand/i }).click();

    const answerBox = page.locator('textarea, input[type="text"]').last();
    await expect(answerBox).toBeVisible({ timeout: 240_000 }); // first question generated by the real engine
    await shot(page, '11-first-question');
    const firstScreen = await page.locator('body').innerText();
    expect(firstScreen).not.toMatch(/something went wrong|unexpected error|access denied/i);

    await answerBox.fill('I built and operated REST APIs in Python with Postgres, adding caching and pagination to keep p95 latency under 200 ms.');
    await page.getByRole('button', { name: /send|submit|answer/i }).last().click();
    await expect(page.locator('body')).not.toContainText(firstScreen.slice(0, 40), { timeout: 240_000, useInnerText: true }).catch(() => {});
    await page.waitForTimeout(3000);
    await shot(page, '12-after-answer');
    expect(await page.locator('body').innerText()).not.toMatch(/something went wrong|unexpected error|access denied/i);
    expect(errors).toEqual([]);
    await ctx.close();
  });
});
