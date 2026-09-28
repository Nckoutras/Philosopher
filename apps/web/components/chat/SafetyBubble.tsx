import { useStore } from '@/lib/store'
import CrisisBubble from './CrisisBubble'

/**
 * The chat crisis bubble: the server's crisis text from the store, rendered by the
 * shared CrisisBubble (SAFETY-003).
 *
 * ONE SOURCE OF TRUTH (SAFETY-003, founder ruling 2026-09-28). The server writes
 * the crisis text in the language the person wrote in
 * (prompt_builder.build_safety_response -> prompts/safety_response*.jinja2),
 * saves it, and streams it; useStream collects it into safetyText. Until SAFETY-003
 * the English path rendered four hardcoded paragraphs here instead, which drifted
 * from the saved text and named no helpline at all.
 *
 * THE TEXT ARRIVES WITH THE EVENT. The server puts the whole crisis text inside
 * the 'safety' / 'safety_override' event, and useStream renders it the moment the
 * event lands, so a connection dropped before the chunks cannot leave this empty.
 */
export default function SafetyBubble() {
  const safetyText = useStore((s) => s.safetyText)
  return <CrisisBubble text={safetyText} />
}
