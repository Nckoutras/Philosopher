// Founder-approved landing copy, verbatim.
//
// Every string below is approved copy and is locked (SKILL.md §3): it is the
// canonical object, changed only by a new ruling — not edited, improved, or
// re-wrapped in place. It lives in one module so the page renders it and the
// tests assert it against the same source, and so a diff to any wording is
// visible on its own line rather than buried in JSX.
export const LANDING_COPY = {
  scrollHint: "SEE WHAT'S INSIDE",

  offer: {
    eyebrow: 'WHAT HAPPENS INSIDE',
    title: 'Three ways to think with the room.',
    intro:
      'Talk one-to-one with a thinker, receive a letter that reflects your week back to you, or bring one difficult question to four minds at once.',
    distinction:
      'Eleven minds, eleven methods of thought — not one voice in eleven costumes.',
    cards: [
      {
        title: 'The Council',
        body: 'Bring your hardest question. Four thinkers deliberate it from four traditions and deliver a verdict — where they converge, and where they split.',
      },
      {
        title: 'A letter, every Sunday',
        body: 'The mind who knows your week best writes to you — what kept returning, what you circled but never opened, and one thing to carry.',
      },
      {
        title: 'Conversation with a method',
        body: 'Socrates questions. Freud interprets. Epictetus steadies. Each mind works the way it actually worked — not a costume, a discipline.',
      },
    ],
  },

  midCta: {
    button: 'Enter The Wise Room',
    note: 'Membership from €11.99 / month.',
  },

  letter: {
    eyebrow: 'FROM A SUNDAY LETTER',
    quote:
      '"The question is not whether you can stop proving yourself. It is what you are using all that effort to avoid knowing."',
    // Supplied as "Yours faithfully, / Lao Tzu" — the slash is a line break in the
    // approved copy, not a character to render.
    signatureLine1: 'Yours faithfully,',
    signatureLine2: 'Lao Tzu',
    contextNote:
      'A Sunday letter reflects the patterns that kept returning in your conversations that week.',
  },

  minds: {
    eyebrow: 'THE MINDS',
    caption: 'Eleven minds. One question: yours.',
  },

  pricing: {
    eyebrow: 'ONE ROOM. ONE PRICE.',
    price: '€11.99 / month',
    annual: 'or €99.99 / year',
    inclusions: [
      'Conversations with all eleven minds',
      'A personal Sunday letter',
      'The Council and reflection rituals',
    ],
    includedLine: 'Everything included. Cancel anytime.',
    button: 'Start membership',
    checkoutNote: 'Choose monthly or annual when you continue.',
  },

  footer: {
    disclaimer:
      'The Wise Room is a reflective companion, not therapy or medical advice. Conversations are AI interpretations of historical thinkers — not the persons themselves.',
    label: 'THEWISEROOM.APP',
  },
} as const
