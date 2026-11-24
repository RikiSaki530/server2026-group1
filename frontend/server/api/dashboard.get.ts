import type { Dashboard } from '../../shared/types'
export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const { period = '1d', start, end } = getQuery(event)
  if (!['30m', '1h', '1d', '1w'].includes(String(period))) {
    throw createError({ statusCode: 400, statusMessage: 'Invalid period' })
  }
  setHeader(event, 'Cache-Control', 'no-store')
  try {
    return await $fetch<Dashboard>(`${config.backendUrl}/dashboard`, { query: { period, start, end }, timeout: 15000, retry: 0 })
  } catch (error) {
    const status = (error as { statusCode?: number }).statusCode
    if (status === 400 || status === 422) {
      throw createError({ statusCode: 400, message: '表示期間が正しくありません。' })
    }
    throw createError({ statusCode: 503, statusMessage: 'Data service unavailable', message: '測定データを取得できません。しばらくしてから再試行してください。' })
  }
})
