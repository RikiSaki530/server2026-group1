<script setup lang="ts">
import type { Dashboard, Metric } from '../shared/types'
import { formatEnvironmentTrendForCsv } from './utils/environmentFormatter'
import { downloadCsvFile } from './utils/csv'

const config = useRuntimeConfig()
const connectionLabels = { online: 'オンライン', offline: 'オフライン', unknown: '未確認', demo: 'デモ' }
const collecting = ref(false)
const collectionError = ref('')
async function collectNow() {
  if (collecting.value) return
  collecting.value = true
  collectionError.value = ''
  try {
    await $fetch('/api/collect', { method: 'POST', timeout: 190000, retry: 0 })
  } catch (err: any) {
    collectionError.value = err?.data?.message || 'データの取得に失敗しました。時間をおいて再試行してください。'
  } finally {
    await refresh()
    collecting.value = false
  }
}
const period = ref('1d')
const metric = ref<Metric>('temperature')
const selected = ref<string[]>([])
const dark = ref(false)
const tab = ref<'overview' | 'history'>('overview')
const periods = [{ id: '30m', name: '30分' }, { id: '1h', name: '1時間' }, { id: '1d', name: '1日' }, { id: '1w', name: '1週間' }]
const metrics = { temperature: { name: '温度', unit: '°C', icon: '♨' }, humidity: { name: '湿度', unit: '%', icon: '◈' }, illumination: { name: '照度', unit: 'lx', icon: '☼' } }
const { data, error, status, refresh } = await useFetch<Dashboard>('/api/dashboard', { query: { period }, timeout: 20000 })
const devices = computed(() => data.value?.devices || [])
const visible = computed(() => devices.value.filter(d => !selected.value.includes(d.id)))
const hasHistory = computed(() => visible.value.some(d => d.history.some(p => p[metric.value] !== null)))
const mean = computed(() => {
  const vals = devices.value.filter(d => !d.stale).map(d => d.latest[metric.value]).filter((v): v is number => typeof v === 'number')
  return vals.length ? (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1) : '—'
})
const rows = computed(() => visible.value.flatMap(d => d.history.filter(p => p[metric.value] !== null).map(p => ({ ...p, device: d.name, id: d.id }))).sort((a,b) => b.timestamp.localeCompare(a.timestamp)).slice(0, 100))

// 出力対象データの準備とクリック時ハンドラ
const csvData = computed(() => formatEnvironmentTrendForCsv(visible.value, period.value))
function handleExportCsv() {
  if (!csvData.value.rows.length) return
  downloadCsvFile(csvData.value.headers, csvData.value.rows, csvData.value.filename)
}

function format(value?: number, digits = 1) { return value == null ? '—' : value.toLocaleString('ja-JP', { maximumFractionDigits: digits }) }
function date(value?: string) { return value ? new Date(value).toLocaleString('ja-JP', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Tokyo' }) : '未取得' }
function sensorStale(value?: string) { return !value || Date.now() - new Date(value).getTime() > 15 * 60 * 1000 }
function toggle(id: string) { selected.value = selected.value.includes(id) ? selected.value.filter(v => v !== id) : [...selected.value, id] }
let timer: ReturnType<typeof setInterval>
onMounted(() => {
  dark.value = localStorage.getItem('temperature-theme') === 'dark'
  timer = setInterval(() => { if (!collecting.value) refresh() }, 60000)
})
watch(dark, value => localStorage.setItem('temperature-theme', value ? 'dark' : 'light'))
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <div class="shell" :class="{ dark }">
    <aside class="sidebar">
      <a href="/" class="brand"><span class="brand-mark">T<span>°</span></span><span>Temperature<br><strong>Temple</strong></span></a>
      <p class="nav-heading">WORKSPACE</p>
      <nav>
        <button :class="{ active: tab === 'overview' }" @click="tab = 'overview'"><span>▦</span> ダッシュボード</button>
        <button :class="{ active: tab === 'history' }" @click="tab = 'history'"><span>◷</span> 測定履歴</button>
        <a :href="config.public.kibanaUrl" target="_blank" rel="noopener noreferrer"><span>↗</span> Kibana で分析</a>
      </nav>
      <div class="sidebar-bottom"><span class="green-dot" /> ENVIRONMENT MONITOR<p>Nature Remo × Elasticsearch</p></div>
    </aside>

    <div class="workspace">
      <header class="topbar"><span>ワークスペース <b>/</b> 環境モニター</span><button class="theme-button" :aria-label="dark ? 'ライトモードに切り替え' : 'ダークモードに切り替え'" @click="dark = !dark">{{ dark ? '☀' : '☾' }}</button></header>
      <main>
        <div class="page-heading"><div><p class="eyebrow">YOUR SPACE, AT A GLANCE</p><h1>{{ tab === 'history' ? '測定履歴' : '環境ダッシュボード' }}</h1><p class="description">部屋の今を知り、環境の変化を見つける。</p></div><button class="refresh" :disabled="collecting || status === 'pending'" :aria-busy="collecting" @click="collectNow()"><span :class="{ spinning: collecting || status === 'pending' }">↻</span> {{ collecting ? '取得中…' : status === 'pending' ? '更新中' : 'データを更新' }}</button></div>

        <div v-if="collectionError" class="notice error" role="alert">{{ collectionError }}</div>
        <div v-if="error" class="notice error" role="alert">測定データを取得できません。サービスの起動状態を確認し、再試行してください。<button @click="refresh()">再試行</button></div>
        <div v-if="data?.demo" class="notice demo">デモモード — 表示中の値は生成データです。実際の Nature Remo の測定値ではありません。</div>
        <div v-if="data?.collector.error" class="notice error" role="alert">{{ data.collector.error }} <span>最終成功: {{ date(data.collector.last_success) }}</span></div>
        <div class="status-line"><span><i class="green-dot" :class="{ offline: error || data?.collector.error }" />{{ error ? '接続エラー' : data?.collector.error ? '収集を確認してください' : data?.collector.last_success ? 'データ収集中' : '初回の収集待ち' }}<small>{{ Math.round((data?.collection_interval_seconds || 300) / 60) }}分間隔で収集 · 画面は1分ごとに更新</small></span><span>最終収集 {{ date(data?.collector.last_success) }} JST</span></div>

        <section v-if="tab === 'overview'" class="devices" aria-label="デバイスの現在値">
          <article v-for="(device, i) in devices" :key="device.id" class="device-card" :style="{ '--device-color': ['#26b391', '#6383ed', '#edaa49', '#cf6ba5'][i % 4] }">
            <div class="device-heading"><span class="device-icon">⌂</span><h2>{{ device.name }}</h2><span class="device-badge" :class="device.connection_status" :title="`接続確認: ${date(device.connection_checked_at ?? undefined)}（取得失敗・15分以上経過で未確認）`"><i />{{ connectionLabels[device.connection_status] }}</span></div>
            <div class="temperature">{{ format(device.latest.temperature) }}<span>°C</span><small>室温</small></div>
            <div class="secondary-values"><div><span>◈ 湿度</span><strong>{{ format(device.latest.humidity) }}<small>%</small></strong></div><div><span>☼ 照度</span><strong>{{ format(device.latest.illumination, 0) }}<small>lx</small></strong></div></div>
            <div class="device-footer"><span>センサー更新 {{ date(device.latest.temperature_updated_at) }}</span><b v-if="sensorStale(device.latest.temperature_updated_at)">更新が古い</b></div>
            <p class="motion">接続確認 {{ date(device.connection_checked_at ?? undefined) }}<span v-if="device.stale"> · 収集遅延</span></p>
            <p class="motion">人感の最終検知 {{ date(device.latest.motion_detected_at) }}</p>
          </article>
          <div v-if="!devices.length && !error" class="empty card">{{ status === 'pending' ? '測定データを読み込んでいます…' : 'まだ測定データがありません' }}<p>.env に NATURE_TOKEN を設定して Collector を起動してください。初回収集後にここに表示されます。</p></div>
        </section>

        <section class="chart-panel card" aria-label="環境の推移">
          <div class="panel-heading">
            <div><p class="eyebrow">ENVIRONMENT TRENDS</p><h2>環境の推移</h2></div>
            <div class="trend-controls">
              <div class="periods" aria-label="表示期間"><button v-for="p in periods" :key="p.id" :class="{ active: period === p.id }" :aria-pressed="period === p.id" @click="period = p.id">{{ p.name }}</button></div>
              <button class="csv-button" :disabled="!csvData.rows.length || status === 'pending'" @click="handleExportCsv">
                <span>↓</span> CSV出力
              </button>
            </div>
          </div>
          <div class="chart-toolbar"><div class="metric-tabs"><button v-for="(m, key) in metrics" :key="key" :class="{ active: metric === key }" :aria-pressed="metric === key" @click="metric = key">{{ m.icon }} {{ m.name }}</button></div><span class="average">現在の平均 <strong>{{ mean }}</strong> {{ metrics[metric].unit }}</span></div>
          <div class="legend"><button v-for="(d,i) in devices" :key="d.id" :class="{ muted: selected.includes(d.id) }" :aria-pressed="!selected.includes(d.id)" @click="toggle(d.id)"><i :style="{ background: ['#26b391', '#6383ed', '#edaa49', '#cf6ba5', '#8f80cf'][i % 5] }" />{{ d.name }}</button><span>JST · 区間平均</span></div>
          <ClientOnly><HistoryChart v-if="hasHistory" :devices="visible" :device-ids="devices.map(d => d.id)" :metric="metric" :dark="dark" :period="period" /><div v-else class="chart-empty"><span>⌁</span><h3>{{ devices.length && !visible.length ? '表示するデバイスを選んでください' : 'この期間の測定データはありません' }}</h3><p>収集したデータが、ここにグラフとして表示されます。</p></div><template #fallback><div class="chart-empty">グラフを読み込んでいます…</div></template></ClientOnly>
          <div class="chart-footnote">{{ period === '1w' ? '1時間' : '5分' }}ごとの平均値を表示。空白はデータ未取得の区間です。</div>
        </section>

        <section class="table-panel card"><div class="panel-heading"><div><p class="eyebrow">MEASUREMENT LOG</p><h2>{{ tab === 'history' ? '期間内の測定履歴' : '最新の測定値' }}</h2></div><span class="table-meta">{{ tab === 'history' ? '最新100件 · 区間平均' : `${devices.length} デバイス` }}</span></div>
          <div class="table-scroll"><table v-if="tab === 'overview'"><thead><tr><th>デバイス</th><th>接続状態</th><th>温度</th><th>湿度</th><th>照度</th><th>温度センサー更新（JST）</th></tr></thead><tbody><tr v-for="d in devices" :key="d.id"><td><strong>{{ d.name }}</strong></td><td><span class="device-badge" :class="d.connection_status"><i />{{ connectionLabels[d.connection_status] }}</span></td><td>{{ format(d.latest.temperature) }} °C</td><td :title="`センサー更新: ${date(d.latest.humidity_updated_at)}`">{{ format(d.latest.humidity) }} %</td><td :title="`センサー更新: ${date(d.latest.illumination_updated_at)}`">{{ format(d.latest.illumination, 0) }} lx</td><td>{{ date(d.latest.temperature_updated_at) }}</td></tr><tr v-if="!devices.length"><td colspan="6" class="empty-cell">測定値はまだありません</td></tr></tbody></table>
          <table v-else><thead><tr><th>時刻（JST）</th><th>デバイス</th><th>温度</th><th>湿度</th><th>照度</th></tr></thead><tbody><tr v-for="row in rows" :key="row.id + row.timestamp"><td>{{ date(row.timestamp) }}</td><td><strong>{{ row.device }}</strong></td><td>{{ format(row.temperature ?? undefined) }} °C</td><td>{{ format(row.humidity ?? undefined) }} %</td><td>{{ format(row.illumination ?? undefined, 0) }} lx</td></tr><tr v-if="!rows.length"><td colspan="5" class="empty-cell">選択した期間のデータはありません</td></tr></tbody></table></div>
        </section>
        <footer>Temperature Temple <span>Nature Remo / Elasticsearch / Kibana</span></footer>
      </main>
    </div>
  </div>
</template>

<style src="./assets/css/main.css"></style>
