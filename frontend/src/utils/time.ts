export function formatBeijingClock(date?: Date): string {
  const now = date || new Date()
  const formatter = new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
  return formatter.format(now)
}

export function formatMessageTime(isoString: string | undefined): string {
  if (!isoString) return ''

  const msgDate = new Date(isoString)
  const now = new Date()

  const formatter = new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })

  const isSameDay =
    msgDate.getUTCFullYear() === now.getUTCFullYear() &&
    msgDate.getUTCMonth() === now.getUTCMonth() &&
    msgDate.getUTCDate() === now.getUTCDate()

  if (isSameDay) {
    const timeFormatter = new Intl.DateTimeFormat('zh-CN', {
      timeZone: 'Asia/Shanghai',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
    return timeFormatter.format(msgDate)
  }

  return formatter.format(msgDate)
}

/**
 * 格式化为相对时间（「刚刚」、「2分钟前」、「昨天 14:30」）
 */
export function formatRelativeTime(isoString: string | undefined): string {
  if (!isoString) return ''

  const msgDate = new Date(isoString)
  const now = new Date()

  // 计算时间差（毫秒）
  const diffMs = now.getTime() - msgDate.getTime()
  const diffMinutes = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  // 刚刚（1分钟内）
  if (diffMinutes < 1) {
    return '刚刚'
  }

  // N分钟前
  if (diffMinutes < 60) {
    return `${diffMinutes}分钟前`
  }

  // N小时前
  if (diffHours < 24) {
    return `${diffHours}小时前`
  }

  // 昨天
  if (diffDays === 1) {
    const timeFormatter = new Intl.DateTimeFormat('zh-CN', {
      timeZone: 'Asia/Shanghai',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
    return `昨天 ${timeFormatter.format(msgDate)}`
  }

  // 前天及之前
  if (diffDays < 7) {
    const dateFormatter = new Intl.DateTimeFormat('zh-CN', {
      timeZone: 'Asia/Shanghai',
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
    return dateFormatter.format(msgDate)
  }

  // 一周以上显示完整日期
  const formatter = new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
  return formatter.format(msgDate)
}

