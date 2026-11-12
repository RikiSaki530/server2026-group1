export default defineEventHandler(async (event) => {
  // Only same-origin browser requests may trigger a collection; never retry a write.
  const origin = getHeader(event, 'origin')
  if (origin && origin !== getRequestURL(event).origin) {
    throw createError({ statusCode: 403, message: '別のサイトからはデータを更新できません。' })
  }
  setHeader(event, 'Cache-Control', 'no-store')
  try {
    return await $fetch(`${useRuntimeConfig(event).backendUrl}/collect`, {
      method: 'POST', timeout: 180000, retry: 0,
    })
  } catch (err: any) {
    const code = [409, 429].includes(err?.statusCode) ? err.statusCode : 503
    if (code === 429) setHeader(event, 'Retry-After', 60)
    throw createError({ statusCode: code, message: err?.data?.detail || 'データの取得に失敗しました。時間をおいて再試行してください。' })
  }
})
