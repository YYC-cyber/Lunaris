const TIMING_TEXT = /\b(?:break|wait)\s+time\s+is\s+(?:about\s+)?[\d.]+\s+(?:ms|s|sec|secs|second|seconds)\b[.!?]?/gi
const TIMING_TOKEN = /(?<![A-Za-z])(?:wait(?:time)?|break(?:time)?|time)\s*[:=]\s*[\d.]+\s*(?:ms|s|sec|secs|seconds)?(?![A-Za-z])/gi

export function cleanVoiceText(value: string | null | undefined): string {
  const lines: string[] = []
  const seen = new Set<string>()
  for (const rawLine of (value || '').split(/\r?\n/)) {
    const line = rawLine.replace(TIMING_TEXT, '').replace(TIMING_TOKEN, '').replace(/\s{2,}/g, ' ').trim()
    if (line && !seen.has(line)) {
      seen.add(line)
      lines.push(line)
    }
  }
  return lines.join('\n').trim()
}

export function getAudioExtension(blob: Blob): string {
  const type = (blob.type || '').toLowerCase()
  if (type.includes('ogg')) return 'ogg'
  if (type.includes('mp4')) return 'mp4'
  if (type.includes('mpeg') || type.includes('mp3')) return 'mp3'
  if (type.includes('wav')) return 'wav'
  return 'webm'
}
