import Link from 'next/link'

export const metadata = {
  title: 'Privacy Policy — Great Minds',
}

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-vellum">
      <div className="max-w-[680px] mx-auto px-7 py-12">
        <Link
          href="/"
          className="font-cormorant text-[20px] font-medium text-ink hover:underline underline-offset-2 decoration-[0.5px]"
        >
          Great Minds
        </Link>

        <article className="mt-10 space-y-7">
          <header className="space-y-2">
            <h1 className="font-cormorant text-[32px] font-medium text-ink leading-tight">
              Privacy Policy
            </h1>
            <p className="font-lora text-[12px] text-sepia">
              Effective: 19 May 2026 · Version 1.1
            </p>
          </header>

          <Section title="1. Introduction">
            This Privacy Policy explains how Great Minds (&ldquo;we&rdquo;, &ldquo;us&rdquo;) collects, uses, and protects your personal data. We are the data controller for the personal data we process to provide the Service. If you have questions, contact us at <Email />.
          </Section>

          <Section title="2. Personal Data We Collect">
            <strong className="font-lora font-medium text-ink">From you directly:</strong> email address (for authentication and communication); conversation messages (content you write to personas); disclaimer acceptance (record of your acknowledgment of our age requirement and service positioning, including timestamp, IP address, and browser).
            {' '}
            <strong className="font-lora font-medium text-ink">Automatically:</strong> authentication metadata (one-time codes, session tokens, login timestamps); technical data (IP address, browser type, device characteristics, basic usage events); strictly necessary cookies for authentication and session management.
            {' '}
            We do not intentionally collect special categories of personal data (health, religion, etc.). Please avoid sharing such data with personas.
          </Section>

          <Section title="3. Why We Process Your Data (Legal Basis)">
            Operating your account, providing AI conversations, sending authentication codes, and processing payments where applicable: contract performance (GDPR Article 6(1)(b)).
            {' '}
            Maintaining audit trail of disclaimer acceptance and complying with legal obligations: legal obligation (Article 6(1)(c)).
            {' '}
            Preventing abuse, fraud, and security incidents: legitimate interest (Article 6(1)(f)).
          </Section>

          <Section title="4. Who Has Access (Processors)">
            We work with the following third-party processors, each bound by data processing agreements: Supabase (database hosting, Ireland/EU); Render (backend API hosting, United States); Anthropic (AI language model, United States); Resend (transactional email, United States); Netlify (frontend hosting, United States); Upstash (cache for rate limiting, Ireland/EU); and Stripe (payment processing, United States).
            {' '}
            When personal data is transferred outside the EU/EEA, we rely on Standard Contractual Clauses (SCCs) approved by the European Commission. We do not sell your personal data.
          </Section>

          <Section title="5. AI Conversations">
            Your messages are sent to Anthropic for processing by their language models, governed by Anthropic&rsquo;s data processing terms. We do not use your conversations to train models.
          </Section>

          <Section title="6. Retention">
            Account data and conversation messages: until you delete your account. OTP codes: up to 1 hour. Disclaimer acceptance audit trail: kept until account deletion. Server logs: up to 30 days.
            {' '}
            When you delete your account, we initiate a soft-delete and retain data for a short grace period (during which you can recover the account), after which we proceed with hard deletion. Aggregated, non-identifying analytics may be retained.
          </Section>

          <Section title="7. Your Rights (GDPR)">
            You have the right to access the personal data we hold about you; rectify inaccurate personal data; erase your account and associated personal data (subject to legal retention requirements); restrict or object to certain processing; receive your data in a structured, machine-readable format (data portability); withdraw consent where processing is based on consent; and lodge a complaint with your local Data Protection Authority.
            {' '}
            To exercise any of these rights, email <Email />. We respond within 30 days.
          </Section>

          <Section title="8. Cookies">
            We use only strictly necessary cookies for authentication and session management. We do not currently use analytics or marketing cookies; if this changes, we will update this Policy and obtain consent where required.
          </Section>

          <Section title="9. Security">
            We implement reasonable technical and organizational measures to protect your data, including: TLS encryption in transit; encrypted storage at rest (via Supabase); hashed and salted authentication codes; and limited access on a need-to-know basis. No system is perfectly secure; we encourage you to use a strong, unique password for your email account.
          </Section>

          <Section title="10. Children">
            The Service is not intended for users under 18. We do not knowingly collect personal data from children under 18. If you believe a child has used the Service, contact us.
          </Section>

          <Section title="11. International Users">
            The Service is operated from Greece. By using the Service, you understand your data may be processed in the EU/EEA and (via processors) in the United States.
          </Section>

          <Section title="12. Changes">
            We may update this Privacy Policy. Material changes will be communicated via the Service or by email. The &ldquo;Effective&rdquo; date at the top reflects the latest version.
          </Section>

          <Section title="13. Contact">
            Data Controller: Great Minds, Greece. Email: <Email />.
          </Section>
        </article>
      </div>
    </main>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="font-cormorant text-[22px] font-medium text-ink leading-tight">
        {title}
      </h2>
      <div className="font-lora text-[14px] text-charcoal leading-[1.7]">
        {children}
      </div>
    </section>
  )
}

function Email() {
  return (
    <a
      href="mailto:support@thegreatminds.app"
      className="text-ink underline underline-offset-2 decoration-[0.5px]"
    >
      support@thegreatminds.app
    </a>
  )
}
