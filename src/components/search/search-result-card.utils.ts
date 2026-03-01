const MAX_SNIPPET_LENGTH = 150

export function createSearchSnippet(content: string): string {
  const normalized = content.replace(/\s+/g, ' ').trim()

  if (normalized.length <= MAX_SNIPPET_LENGTH) {
    return normalized
  }

  const truncated = normalized.slice(0, MAX_SNIPPET_LENGTH)
  const lastSpace = truncated.lastIndexOf(' ')
  const breakAt =
    lastSpace > MAX_SNIPPET_LENGTH * 0.7 ? lastSpace : MAX_SNIPPET_LENGTH

  return `${normalized.slice(0, breakAt).trimEnd()}…`
}

export function toRelevancePercent(score: number): number {
  if (!Number.isFinite(score) || score <= 0) {
    return 0
  }

  if (score >= 1) {
    return 100
  }

  return Math.round(score * 100)
}
