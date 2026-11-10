export default defineNuxtConfig({
  compatibilityDate: '2025-07-01',
  devtools: { enabled: false },
  runtimeConfig: {
    backendUrl: 'http://backend:8000',
    public: { kibanaUrl: 'http://localhost:5601' },
  },
  app: { head: {
    title: 'Temperature Temple | 環境モニター',
    htmlAttrs: { lang: 'ja' },
    meta: [{ name: 'description', content: 'Nature Remo の温度・湿度・照度を収集して比較する環境ダッシュボード' }],
  } },
})
