export function dynamicFontSize(charCount: number): number {
  const MIN_CHARS = 15
  const MAX_CHARS = 350
  const MAX_SIZE  = 64
  const MIN_SIZE  = 28
  const clamped = Math.max(MIN_CHARS, Math.min(MAX_CHARS, charCount))
  return MAX_SIZE + (MIN_SIZE - MAX_SIZE) * (clamped - MIN_CHARS) / (MAX_CHARS - MIN_CHARS)
}

export function stripEmoji(text: string): string {
  return text.replace(/\p{Extended_Pictographic}/gu, '')
}
