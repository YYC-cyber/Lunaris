export function isStickerImage(value?: string): boolean {
  if (!value) return false
  return /^(https?:\/\/|\/|\.\/|data:image\/|blob:)/i.test(value)
    || /\.(png|jpe?g|gif|webp|svg)([?#].*)?$/i.test(value)
}

const FALLBACK_EMOJIS: Record<string, string> = {
  happy: '😊',
  sad: '😢',
  angry: '😠',
  love: '🥰',
  gentle: '🤗',
  neutral: '😐',
}

const STICKER_EMOJIS_BY_NAME: Record<string, string> = {
  大笑: '😂',
  哈哈: '😄',
  开心: '😊',
  兴奋: '🤩',
  惊喜: '😁',
  笑哭: '🤣',
  眦牙: '😬',
  龇牙: '😬',
  庆祝: '🥳',
  难过: '😢',
  伤心: '😭',
  低落: '😔',
  沮丧: '😞',
  委屈: '🥹',
  哭泣: '😿',
  生气: '😠',
  发怒: '😡',
  愤怒: '🤬',
  不爽: '😒',
  烦躁: '😤',
  平静: '😐',
  无语: '🙄',
  疑惑: '🤔',
  尴尬: '😅',
  冷静: '😑',
  喜欢: '🥰',
  心动: '💓',
  亲吻: '😘',
  爱你: '❤️',
  甜蜜: '💕',
  温柔: '🥺',
  安慰: '🤗',
  陪伴: '💙',
  理解: '👂',
}

const REPLACEMENT_EMOJIS: Record<string, string[]> = {
  happy: ['😂', '😄', '😊', '🤩', '😁', '🤣', '🥳', '😆', '😸'],
  sad: ['😢', '😭', '😔', '😞', '🥹', '😿', '😥', '😓', '😪'],
  angry: ['😠', '😡', '🤬', '😒', '😤', '😾', '🙃'],
  neutral: ['😐', '🙄', '🤔', '😅', '😑', '🫤', '😶'],
  love: ['🥰', '💓', '😘', '❤️', '💕', '💗', '💖', '😍'],
  gentle: ['🥺', '🤗', '💙', '👂', '🫶', '🌷', '✨'],
}

export function stickerFallbackEmoji(emotion?: string, name?: string): string {
  return (name && STICKER_EMOJIS_BY_NAME[name])
    || FALLBACK_EMOJIS[emotion || 'neutral']
    || FALLBACK_EMOJIS.neutral
}

export function stickerReplacementEmoji(
  emotion?: string,
  used: Set<string> = new Set(),
  seed = 0,
): string {
  const pool = REPLACEMENT_EMOJIS[emotion || 'neutral'] || REPLACEMENT_EMOJIS.neutral
  const available = pool.find((emoji) => !used.has(emoji))
  if (available) return available
  return pool[seed % pool.length]
}
