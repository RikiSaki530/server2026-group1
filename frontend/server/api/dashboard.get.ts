import type { Dashboard } from '../../shared/types'
export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const period = String(getQuery(event).period || '1d')
  if (!['30m', '1h', '1d', '1w'].includes(period)) {
    throw createError({ statusCode: 400, statusMessage: 'Invalid period' })
  }
  setHeader(event, 'Cache-Control', 'no-store')
  try {
    return await $fetch<Dashboard>(`${config.backendUrl}/dashboard`, { query: { period }, timeout: 15000, retry: 0 })
  } catch {
    throw createError({ statusCode: 503, statusMessage: 'Data service unavailable', message: '測定データを取得できません。しばらくしてから再試行してください。' })
  }
})
