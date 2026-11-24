const dayMs = 86400000
const hourMs = 3600000
type Observation = { timestamp: number; label?: string; temperature?: number }

// The Naha station's hourly table includes observed weather as image alt text.
const fetchDay = defineCachedFunction(async (date: string) => {
  const [year, month, day] = date.split('-')
  const html = await $fetch<string>('https://www.data.jma.go.jp/stats/etrn/view/hourly_s1.php', {
    query: { prec_no: 91, block_no: 47936, year, month, day },
    responseType: 'text', timeout: 5000, retry: 0,
  })
  const table = html.match(/<table\b[^>]*\bid=['"]tablefix1['"][^>]*>([\s\S]*?)<\/table>/i)?.[1]
  if (!table) throw new Error('Naha observation table missing')
  const midnight = Date.parse(date + 'T00:00:00+09:00')
  return [...table.matchAll(/<tr\b[^>]*>\s*<td\b[^>]*>\s*(\d{1,2})\s*<\/td>([\s\S]*?)<\/tr>/gi)]
    .flatMap(([, hour, row]) => {
      const image = row?.match(/<img\b[^>]*\/tenki\/[^>]*>/i)?.[0]
      const label = image?.match(/\balt=["']([^"']+)["']/i)?.[1]?.trim()
      const h = Number(hour)
      const cell = [...(row ?? '').matchAll(/<td\b[^>]*>([\s\S]*?)<\/td>/gi)][3]?.[1]?.trim()
      const temperature = cell && /^-?\d+(?:\.\d+)?$/.test(cell) ? Number(cell) : undefined
      if (h < 1 || h > 24 || (!label && temperature === undefined)) return []
      return [{ timestamp: midnight + h * hourMs, label: label === '曇' ? '曇り' : label, temperature }]
    })
}, { name: 'jma-naha-hourly', maxAge: 900, swr: false })

// Codes used by the JMA AMeDAS observation display (30 and 31 are unknown/missing).
const liveLabels = [
  '晴れ', '曇り', '煙霧', '霧', '降水', '霧雨', '着氷性の霧雨', '雨',
  '着氷性の雨', 'みぞれ', '雪', '凍雨', '霧雪', 'しゅう雨', 'しゅう雪', 'ひょう', '雷',
]
const fetchLiveBlock = defineCachedFunction(async (date: string, block: number) => {
  const hour = String(block).padStart(2, '0')
  const readings = await $fetch<Record<string, { weather?: [number | null, number | null]; temp?: [number | null, number | null] }>>(
    `https://www.jma.go.jp/bosai/amedas/data/point/91197/${date.replaceAll('-', '')}_${hour}.json`,
    { timeout: 5000, retry: 0 },
  )
  const midnight = Date.parse(date + 'T00:00:00+09:00')
  return Object.entries(readings).flatMap(([key, reading]) => {
    if (!/^\d{10}0000$/.test(key)) return []
    const code = reading.weather?.[1] === 0 ? reading.weather[0] : null
    const label = code != null ? liveLabels[code] : undefined
    const temperature = reading.temp?.[1] === 0 ? reading.temp[0] ?? undefined : undefined
    return label || temperature !== undefined ? [{ timestamp: midnight + Number(key.slice(8, 10)) * hourMs, label, temperature }] : []
  })
}, { name: 'jma-naha-amedas-live', maxAge: 300, swr: false })

export default defineEventHandler(async event => {
  const { start, end } = getQuery(event)
  const dayPattern = /^\d{4}-\d{2}-\d{2}$/
  const today = new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Tokyo' })
  if (typeof start !== 'string' || typeof end !== 'string' || !dayPattern.test(start) || !dayPattern.test(end) ||
      !Number.isFinite(Date.parse(start)) || !Number.isFinite(Date.parse(end)) || start > end || end > today) {
    throw createError({ statusCode: 400, message: '天気の表示期間が正しくありません。' })
  }

  const days = (Date.parse(end) - Date.parse(start)) / dayMs + 1
  if (days > 31) return { weather: [], temperatures: [], incomplete: false, tooLong: true }
  const dates = Array.from({ length: days }, (_, i) =>
    new Date(Date.parse(start) + i * dayMs).toISOString().slice(0, 10))
  const from = Date.parse(start + 'T00:00:00+09:00')
  const until = Date.parse(end + 'T00:00:00+09:00') + dayMs
  // The first midnight is the 24:00 row on the previous day's table.
  const previousDay = new Date(Date.parse(start) - dayMs).toISOString().slice(0, 10)
  const historicalDates = [previousDay, ...dates.filter(date => date !== today)]
  const observations: Observation[] = []
  let incomplete = false
  // Keep requests to the public data site in small batches.
  for (let i = 0; i < historicalDates.length; i += 3) {
    const batch = await Promise.allSettled(historicalDates.slice(i, i + 3).map(date => fetchDay(date)))
    for (const result of batch) {
      if (result.status === 'fulfilled') observations.push(...result.value)
      else incomplete = true
    }
  }
  const now = Date.now()
  if (end === today) {
    const midnight = Date.parse(today + 'T00:00:00+09:00')
    const blockCount = Math.floor((now - midnight) / (3 * hourMs)) + 1
    const blocks = await Promise.allSettled(Array.from({ length: blockCount }, (_, i) => fetchLiveBlock(today, i * 3)))
    for (const block of blocks) {
      if (block.status === 'fulfilled') observations.push(...block.value)
      else incomplete = true
    }
  }
  // Yesterday's 24:00 and today's 00:00 can report the same observation.
  const byTime = new Map<number, Observation>()
  for (const point of observations) {
    if (point.timestamp < from || point.timestamp >= until || point.timestamp > now) continue
    const previous = byTime.get(point.timestamp)
    byTime.set(point.timestamp, {
      timestamp: point.timestamp,
      label: point.label ?? previous?.label,
      temperature: point.temperature ?? previous?.temperature,
    })
  }
  const ordered = [...byTime.values()].sort((a, b) => a.timestamp - b.timestamp)
  const weather = ordered.flatMap(({ timestamp, label }) => label ? [{ timestamp, label }] : [])
  const temperatures = ordered.flatMap(({ timestamp, temperature }) =>
    temperature === undefined ? [] : [{ timestamp, temperature }])
  return { weather, temperatures, incomplete, tooLong: false }
})
