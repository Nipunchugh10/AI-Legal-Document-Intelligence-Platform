import { test, expect } from '@playwright/test';

test.describe('Critical User Journey E2E Suite', () => {
  test('executes complete 8-step journey from authentication and 2FA to analysis, Q&A, and history', async ({ page }) => {
    let is2faEnabled = false;

    // Set up comprehensive route mocking for deterministic E2E execution
    await page.route('**/auth/oauth-config', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ google_client_id: 'test-google-id' }),
      });
    });

    await page.route('**/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          email: 'lawyer@example.com',
          is_active: true,
          is_2fa_enabled: is2faEnabled,
          created_at: '2026-09-01T00:00:00Z',
        }),
      });
    });

    await page.route('**/auth/login', async (route) => {
      if (is2faEnabled) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            requires_2fa: true,
            pending_2fa_token: 'pending-e2e-token',
            message: 'A 6-digit OTP has been sent to l***r@example.com',
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            access_token: 'e2e-access-token',
            refresh_token: 'e2e-refresh-token',
            requires_2fa: false,
          }),
        });
      }
    });

    await page.route('**/auth/login/2fa-verify', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'e2e-verified-token',
          refresh_token: 'e2e-verified-refresh',
          requires_2fa: false,
        }),
      });
    });

    await page.route('**/auth/2fa/enable', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Verification code sent to email' }),
      });
    });

    await page.route('**/auth/2fa/confirm', async (route) => {
      is2faEnabled = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: '2FA enabled successfully' }),
      });
    });

    await page.route('**/auth/sessions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.route('**/users/me/retention', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ retention_days: null }),
      });
    });

    await page.route('**/contracts/upload', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 42, filename: 'Master_Services_Agreement.pdf' }),
      });
    });

    await page.route('**/contracts/42/extract', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ text: 'Extracted text' }),
      });
    });

    await page.route('**/contracts/42/chunk', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ chunks_count: 5 }),
      });
    });

    await page.route('**/contracts/42/ingest*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'success' }),
      });
    });

    await page.route('**/contracts/42', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 42,
          filename: 'Master_Services_Agreement.pdf',
          upload_path: '/uploads/Master_Services_Agreement.pdf',
          status: 'analyzed',
          created_at: '2026-09-05T14:30:00Z',
        }),
      });
    });

    await page.route('**/contracts/42/analysis', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          contract_id: 42,
          status: 'completed',
          document_type: 'Master Services Agreement (SaaS)',
          metadata: {
            party_a: 'Acme Cloud Solutions Inc.',
            party_b: 'Global Enterprises LLC',
            effective_date: 'October 1, 2026',
            jurisdiction: 'State of California',
          },
          clauses: {
            payment_terms: { text: 'Net-30 payment terms', present: true, location: 'Section 3.1' },
            termination_clauses: { text: '30 days termination for cause', present: true, location: 'Section 7.2' },
          },
          risks: [
            {
              risk_type: 'Uncapped Consequential Damages Carve-Out',
              flag_category: 'RED_FLAG',
              severity: 'RED_FLAG',
              irac_issue: 'Is indemnity exposure uncapped?',
              clause_text: 'The liability cap shall not apply to indemnification obligations.',
            },
          ],
          compliance_issues: [],
          summary: 'Comprehensive SaaS agreement between Acme Cloud Solutions and Global Enterprises.',
        }),
      });
    });

    await page.route('**/contracts/42/text', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ text: 'Extracted text of agreement' }),
      });
    });

    await page.route('**/contracts/42/ask', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          contract_id: 42,
          question: 'Can I terminate early?',
          answer: 'Section 7.2 permits termination for cause upon 30 days written notice.',
          sources: [{ chunk_index: 2, text: '30 days termination for cause', section: 'Section 7.2' }],
          conversation_id: 88,
        }),
      });
    });

    await page.route('**/conversations*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.route('**/conversations/88', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 88,
          contract_id: 42,
          title: 'Early Termination Discussion',
          created_at: '2026-09-08T12:00:00Z',
          messages: [
            {
              id: 1,
              conversation_id: 88,
              role: 'user',
              content: 'Can I terminate early?',
              cited_clause_refs: [],
              created_at: '2026-09-08T12:00:01Z',
            },
            {
              id: 2,
              conversation_id: 88,
              role: 'assistant',
              content: 'Section 7.2 permits termination for cause upon 30 days written notice.',
              cited_clause_refs: [{ chunk_index: 2, text: '30 days termination for cause', section: 'Section 7.2' }],
              created_at: '2026-09-08T12:00:05Z',
            },
          ],
        }),
      });
    });

    await page.route('**/audit-logs*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 101,
              user_id: 1,
              action: 'UPLOAD_DOCUMENT',
              category: 'CONTRACTS',
              status: 'SUCCESS',
              description: 'Uploaded document Master_Services_Agreement.pdf',
              created_at: '2026-09-08T10:00:00Z',
            },
            {
              id: 102,
              user_id: 1,
              action: 'RUN_ANALYSIS',
              category: 'ANALYSIS',
              status: 'SUCCESS',
              description: 'Completed 5-agent LangGraph analysis for contract #42',
              created_at: '2026-09-08T10:02:00Z',
            },
          ],
          total: 2,
          limit: 25,
          offset: 0,
        }),
      });
    });

    // ════════════════════════════════════════════════════════════════════════
    // STEP 1: Registration / Initial Login
    // ════════════════════════════════════════════════════════════════════════
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: /Welcome Back/i })).toBeVisible();

    await page.getByPlaceholder('name@company.com').fill('lawyer@example.com');
    await page.getByPlaceholder('••••••••').fill('StrongPass123!');
    await page.getByRole('button', { name: /Sign In/i }).click();

    // ════════════════════════════════════════════════════════════════════════
    // STEP 2: Enable Email 2FA in /security
    // ════════════════════════════════════════════════════════════════════════
    await page.goto('/security');
    const enableBtn = page.getByRole('button', { name: /Enable Email 2FA/i });
    await expect(enableBtn).toBeVisible();
    await enableBtn.click();

    await expect(page.getByRole('heading', { name: /Verify Your Email/i })).toBeVisible();
    const firstOtpInput = page.locator('.otp-digit-input').first();
    await firstOtpInput.fill('123456');

    await page.getByRole('button', { name: /Verify & Activate/i }).click();
    await expect(page.getByText(/Two-Factor Authentication is now active/i)).toBeVisible();

    // ════════════════════════════════════════════════════════════════════════
    // STEP 3: Logout and Log In Through Full Email OTP Flow
    // ════════════════════════════════════════════════════════════════════════
    await page.goto('/login');
    await page.getByPlaceholder('name@company.com').fill('lawyer@example.com');
    await page.getByPlaceholder('••••••••').fill('StrongPass123!');
    await page.getByRole('button', { name: /Sign In/i }).click();

    await expect(page.getByRole('heading', { name: /Two-Factor Authentication/i })).toBeVisible();
    const loginOtpInput = page.locator('.otp-digit-input').first();
    await loginOtpInput.fill('654321');

    // ════════════════════════════════════════════════════════════════════════
    // STEP 4: Upload a Contract & Ingest into Vault Storage
    // ════════════════════════════════════════════════════════════════════════
    await page.goto('/upload');
    await expect(page.getByText(/Drag and drop your contract here/i)).toBeVisible();

    // Set file input
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'Master_Services_Agreement.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 mock legal content'),
    });

    const startIngestBtn = page.getByRole('button', { name: /Start Ingestion →/i });
    await expect(startIngestBtn).toBeVisible();
    await startIngestBtn.click();

    await expect(page.getByRole('heading', { name: /Document Ingested & Vectorized/i })).toBeVisible();

    // ════════════════════════════════════════════════════════════════════════
    // STEP 5 & 6: View Analysis Workspace and 3-Tier Risk Dialectic
    // ════════════════════════════════════════════════════════════════════════
    await page.goto('/contracts/42');
    await expect(page.getByRole('heading', { name: 'Master_Services_Agreement.pdf' })).toBeVisible();
    await expect(page.getByText(/Senior Partner Executive Synthesis/i)).toBeVisible();

    // Switch to 3-Tier Risk Dialectic tab
    const risksTab = page.getByRole('button', { name: /3-Tier Risk Dialectic/i });
    await risksTab.click();
    await expect(page.getByText('Uncapped Consequential Damages Carve-Out')).toBeVisible();

    // ════════════════════════════════════════════════════════════════════════
    // STEP 7: Grounded Q&A and Persistence Across Refresh
    // ════════════════════════════════════════════════════════════════════════
    await page.goto('/contracts/42/ask');
    const qaInput = page.getByPlaceholder(/Ask any legal question/i);
    await qaInput.fill('Can I terminate early?');
    await page.getByTitle(/Send query \(Enter\)/i).click();

    await expect(page.getByText(/Section 7\.2 permits termination for cause/i)).toBeVisible();

    // Refresh simulation
    await page.goto('/contracts/42/ask?conversation_id=88');
    await expect(page.getByText(/Section 7\.2 permits termination for cause/i)).toBeVisible();

    // ════════════════════════════════════════════════════════════════════════
    // STEP 8: Check History Page Shows Audit Actions
    // ════════════════════════════════════════════════════════════════════════
    await page.goto('/history');
    await expect(page.getByRole('heading', { name: /Activity Timeline & Governance/i })).toBeVisible();
    await expect(page.getByText('Uploaded document Master_Services_Agreement.pdf')).toBeVisible();
    await expect(page.getByText('Completed 5-agent LangGraph analysis for contract #42')).toBeVisible();
  });
});
