export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const body = await readBody(event)
  setHeader(event, 'Cache-Control', 'no-store')
  try {
    return await $fetch(`${config.backendUrl}/export`, {
      method: 'POST', body, timeout: 120000, retry: 0,
    })
  } catch (error) {
    const status = (error as { statusCode?: number }).statusCode
    if (status === 400 || status === 422) {
      throw createError({ statusCode: 400, message: 'CSVの出力条件が正しくありません。' })
    }
    throw createError({ statusCode: 503, message: 'CSV用の測定データを取得できません。' })
  }
})
