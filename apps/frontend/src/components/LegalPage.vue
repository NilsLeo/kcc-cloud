<script setup lang="ts">
import { computed } from 'vue';
import Icon from '@/components/Icon.vue';

const props = defineProps<{ slug: string }>();
defineEmits<{ back: [] }>();

const LEGAL_CONTENT: Record<string, { title: string; subtitle: string; body: [string, string][] }> = {
  imprint: {
    title: 'Impressum',
    subtitle: 'Angaben gemäß § 5 TMG',
    body: [
      ['Service provider', 'MGC Conversion Services UG (haftungsbeschränkt)\nMusterstraße 12\n10115 Berlin, Germany'],
      ['Represented by', 'Alex Chen, Geschäftsführer'],
      ['Contact', 'Email: hello@mgc.example\nPhone: +49 30 0000 0000'],
      ['Registry', 'Handelsregister: HRB 000000 B · Amtsgericht Berlin-Charlottenburg'],
      ['VAT ID', 'USt-IdNr. DE000000000 (gemäß § 27 a UStG)'],
      ['Responsible for content', 'Alex Chen (address as above), gemäß § 18 Abs. 2 MStV'],
      ['EU dispute resolution', 'The European Commission provides a platform for online dispute resolution (OS): https://ec.europa.eu/consumers/odr/. Our email is listed above. We are not obligated and not willing to participate in dispute resolution proceedings in front of a consumer arbitration board.'],
    ],
  },
  privacy: {
    title: 'Datenschutzerklärung',
    subtitle: 'Information zur Datenverarbeitung gemäß Art. 13 DSGVO',
    body: [
      ['Controller', 'MGC Conversion Services UG (haftungsbeschränkt), Musterstraße 12, 10115 Berlin, Germany. Contact: privacy@mgc.example.'],
      ['Data we process', 'Account data (name, email, hashed password), billing data (address, payment-method tokens via Stripe), conversion jobs (filenames, file sizes, device profile, processing logs).'],
      ['Purposes & legal bases', 'Providing the service: Art. 6(1)(b) DSGVO. Billing and accounting: Art. 6(1)(b) and (c). Security and abuse prevention: Art. 6(1)(f). Marketing emails only with your separate consent under Art. 6(1)(a).'],
      ['Processors', 'Stripe Payments Europe Ltd. (payments), Hetzner Online GmbH (hosting in Germany), Postmark (transactional email). All bound by data processing agreements.'],
      ['Retention', 'Uploaded files are deleted automatically 24 hours after the conversion job completes. Account data is kept until you delete your account. Invoices are retained for 10 years per § 147 AO.'],
      ['Your rights', 'You have the right to access, rectify, erase, restrict and port your data, and to lodge a complaint with a supervisory authority (e.g. BlnBDI for Berlin). Withdraw consent at any time via privacy@mgc.example.'],
      ['Cookies', 'We use only strictly necessary cookies (auth session, CSRF). No tracking or analytics cookies.'],
    ],
  },
  toc: {
    title: 'Allgemeine Geschäftsbedingungen',
    subtitle: 'Terms of service · As of January 2026',
    body: [
      ['§ 1 Scope', 'These terms govern the use of the file-conversion service operated by MGC Conversion Services UG (the "Service"). By creating an account or using the Service you agree to be bound by these terms.'],
      ['§ 2 Service description', 'The Service converts comic and manga files (CBZ, CBR, PDF, EPUB, etc.) into e-reader-optimized formats. We provide best-effort processing and do not guarantee perfect conversion for any specific source file.'],
      ['§ 3 Subscription & prices', "Paid plans are billed monthly via Stripe. Prices are shown including statutory VAT. We may adjust prices with 30 days' written notice; you can cancel before the new price takes effect."],
      ['§ 4 User obligations', 'You may only upload files that you have the right to convert. You may not upload illegal content. You are responsible for keeping your credentials safe.'],
      ['§ 5 Term & termination', 'Subscriptions run on a monthly basis and renew automatically until cancelled. Both parties may terminate for good cause at any time. We may suspend the Service for misuse.'],
      ['§ 6 Liability', 'We are liable without limitation for intent and gross negligence. For slight negligence we are only liable for breach of essential contractual obligations and limited to typically foreseeable damages.'],
      ['§ 7 Applicable law', 'German law applies, excluding the UN Convention on Contracts for the International Sale of Goods. For consumers, mandatory consumer-protection laws of your habitual residence apply.'],
    ],
  },
  withdrawal: {
    title: 'Widerrufsbelehrung',
    subtitle: 'Right of withdrawal for consumers (Verbraucher i.S.d. § 13 BGB)',
    body: [
      ['Right of withdrawal', 'You have the right to withdraw from this contract within 14 days without giving any reason. The withdrawal period is 14 days from the day of the conclusion of the contract.'],
      ['How to exercise', 'To exercise the right of withdrawal, you must inform us (MGC Conversion Services UG, Musterstraße 12, 10115 Berlin, Germany, email: hello@mgc.example) of your decision to withdraw by an unequivocal statement (e.g. by post or email).'],
      ['Effects of withdrawal', 'If you withdraw, we shall reimburse all payments received from you without undue delay and no later than 14 days from the day on which we are informed about your decision.'],
      ['Expiry — digital services', 'The right of withdrawal expires early for digital services if we have begun the service with your express prior consent and your acknowledgement that you thereby lose your right of withdrawal (§ 356 Abs. 4 BGB).'],
      ['Model form', 'To MGC Conversion Services UG, Musterstraße 12, 10115 Berlin, Germany, hello@mgc.example —\nI/We (*) hereby give notice that I/We (*) withdraw from my/our (*) contract.\nOrdered on (*) / received on (*):\nName of consumer(s):\nDate:\n(*) Delete as appropriate.'],
    ],
  },
  faq: {
    title: 'Frequently asked questions',
    subtitle: 'Quick answers to common questions',
    body: [
      ['What file formats are supported?', 'Input: CBZ, CBR, CB7, ZIP, RAR, PDF, EPUB. Output: EPUB, MOBI, KFX, CBZ, PDF — whichever your device prefers.'],
      ['How big can my files be?', 'Up to 1 GB per file. Free plan allows up to 5 files per day; paid plans remove that limit.'],
      ['How long are my files stored?', 'Uploaded sources and converted outputs are automatically deleted 24 hours after conversion completes.'],
      ['Is my data shared?', 'No. We do not sell, rent, or share your data. See the Datenschutzerklärung for our processor list.'],
      ['Can I self-host?', 'Yes — the Community Edition is open source and fully self-hostable. The hosted version offers an account, billing, support and managed infrastructure.'],
      ['How do I cancel my subscription?', 'Account → Subscription → Cancel. Your plan stays active until the end of the current billing period.'],
      ['Can I get an invoice?', 'Yes. Every monthly charge generates a PDF invoice with all VAT details, downloadable from Account → Subscription → Invoices.'],
      ['Which devices are supported?', '30+ profiles including Kindle (all generations), Kobo (all generations), reMarkable 1/2/Paper Pro, plus a custom-dimensions option.'],
    ],
  },
};

const doc = computed(() => LEGAL_CONTENT[props.slug] || LEGAL_CONTENT.imprint);
</script>

<template>
  <div class="max-w-3xl animate-slide-up">
    <button class="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1 mb-4" @click="$emit('back')">
      <Icon name="chevronLeft" class="h-4 w-4" /> Back
    </button>
    <h2 class="text-2xl md:text-3xl font-bold font-poppins tracking-tight">{{ doc.title }}</h2>
    <p class="text-muted-foreground mt-1">{{ doc.subtitle }}</p>

    <div class="mt-6 space-y-5">
      <section v-for="([title, body], idx) in doc.body" :key="idx" class="rounded-lg border bg-card p-5">
        <h3 class="font-poppins font-semibold mb-2">{{ title }}</h3>
        <p class="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">{{ body }}</p>
      </section>
    </div>
  </div>
</template>
