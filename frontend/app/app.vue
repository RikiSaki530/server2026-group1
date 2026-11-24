<script setup lang="ts">
import type { Dashboard, Metric } from '../shared/types'
import { downloadCsvFile } from './utils/csv'
import { chartMetrics as metrics, deviceColors, seriesColor, seriesColorOptions, type SeriesColors } from './utils/chartSeries'

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
const historyMetric = ref<Metric>('temperature')
const rightAxis = ref<Metric | ''>('')
const chartMetric = computed(() => tab.value === 'history' ? historyMetric.value : metric.value)
const rightMetric = computed(() => tab.value === 'history' && rightAxis.value && rightAxis.value !== historyMetric.value ? rightAxis.value : undefined)
const historyChart = ref<{ saveImage: () => void } | null>(null)
const customColors = ref<Record<string, SeriesColors>>({})
function updateSeriesColor(id: string, axis: 'left' | 'right', event: Event) {
  const color = (event.target as HTMLSelectElement).value
  customColors.value = { ...customColors.value, [id]: { ...customColors.value[id], [axis]: color } }
}
watch(historyMetric, value => {
  if (rightAxis.value === value) rightAxis.value = ''
})
const selected = ref<string[]>([])
const dark = ref(false)
const tab = ref<'overview' | 'history'>('overview')
const periods = [{ id: '30m', name: '30分' }, { id: '1h', name: '1時間' }, { id: '1d', name: '1日' }, { id: '1w', name: '1週間' }]
function todayInJst() {
  return new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Tokyo' })
}
const today = useState('history-today-jst', todayInJst)
const selection = ref({ start: today.value, end: today.value })
const range = computed(() => tab.value === 'history' ? selection.value : undefined)
const query = computed(() => range.value ?? { period: period.value })
const queryKey = computed(() => JSON.stringify(query.value))
const { data: result, error, status, refresh } = await useAsyncData('dashboard', async (_app, { signal }) => {
  const requestedQuery = query.value
  const key = JSON.stringify(requestedQuery)
  const dashboard = await $fetch<Dashboard>('/api/dashboard', { query: requestedQuery, signal, timeout: 20000 })
  return { key, dashboard }
}, { watch: [queryKey] })
const data = computed(() => result.value?.dashboard)
const dayMs = 86400000
const rangeDays = computed(() => range.value ? (Date.parse(range.value.end) - Date.parse(range.value.start)) / dayMs + 1 : 0)
const historyInterval = computed(() => rangeDays.value === 1 ? '5分' : rangeDays.value <= 7 ? '1時間' : rangeDays.value <= 31 ? '3時間' : '1日')
function selectRange(start: string, end: string) {
  selection.value = { start, end }
}
function selectPreset(days: number) {
  const end = today.value
  const start = new Date(Date.parse(end) - (days - 1) * dayMs)
  if (days === 0) {
    const day = start.getUTCDate()
    start.setUTCDate(1)
    start.setUTCMonth(start.getUTCMonth() - 1)
    const lastDay = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + 1, 0)).getUTCDate()
    start.setUTCDate(Math.min(day, lastDay))
  }
  selectRange(start.toISOString().slice(0, 10), end)
}
const devices = computed(() => data.value?.devices || [])
const visible = computed(() => devices.value.filter(d => !selected.value.includes(d.id)))
const historyReady = computed(() => result.value?.key === queryKey.value)
const hasHistory = computed(() => historyReady.value && visible.value.some(d => d.history.some(p => p[chartMetric.value] !== null || (rightMetric.value && p[rightMetric.value] !== null))))
const mean = computed(() => {
  const vals = devices.value.filter(d => !d.stale).map(d => d.latest[metric.value]).filter((v): v is number => typeof v === 'number')
  return vals.length ? (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1) : '—'
})
const rows = computed(() => historyReady.value ? visible.value.flatMap(d => d.history.filter(p => p.temperature !== null || p.humidity !== null || p.illumination !== null).map(p => ({ ...p, device: d.name, id: d.id }))).sort((a,b) => b.timestamp.localeCompare(a.timestamp)).slice(0, 100) : [])

const csvDialog = ref<HTMLDialogElement | null>(null)
const csvMode = ref<'hourly' | 'raw'>('hourly')
const exporting = ref(false)
const csvMessage = ref('')
function openCsvDialog() {
  csvMessage.value = ''
  csvDialog.value?.showModal()
}
async function handleExportCsv() {
  if (exporting.value) return
  const mode = csvMode.value
  const requestedRange = range.value
  const requestedPeriod = period.value
  const deviceIds = visible.value.map(device => device.id)
  exporting.value = true
  csvMessage.value = ''
  try {
    const rows = await $fetch<unknown[][]>('/api/export', {
      method: 'POST', body: { mode, period: requestedPeriod, ...requestedRange, device_ids: deviceIds },
      timeout: 125000, retry: 0,
    })
    if (!rows.length) {
      csvMessage.value = 'この期間に出力できる測定データがありません。'
      return
    }
    const dateLabel = requestedRange ? `${requestedRange.start}_${requestedRange.end}` : `${requestedPeriod}_${today.value}`
    downloadCsvFile(['時刻(JST)', 'デバイス', '温度(°C)', '湿度(%)', '照度(lx)'], rows, `environment_${mode}_${dateLabel}.csv`)
    csvDialog.value?.close()
  } catch {
    csvMessage.value = 'CSVを出力できませんでした。もう一度お試しください。'
  } finally {
    exporting.value = false
  }
}

function format(value?: number, digits = 1) { return value == null ? '—' : value.toLocaleString('ja-JP', { maximumFractionDigits: digits }) }
function date(value?: string) { return value ? new Date(value).toLocaleString('ja-JP', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Tokyo' }) : '未取得' }
function sensorStale(value?: string) { return !value || Date.now() - new Date(value).getTime() > 15 * 60 * 1000 }
function toggle(id: string) { selected.value = selected.value.includes(id) ? selected.value.filter(v => v !== id) : [...selected.value, id] }
let timer: ReturnType<typeof setInterval>
onMounted(() => {
  dark.value = localStorage.getItem('temperature-theme') === 'dark'
  timer = setInterval(() => {
    today.value = todayInJst()
    if (!collecting.value) refresh()
  }, 60000)
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

        <HistoryCalendar v-if="range" :start="range.start" :end="range.end" :today="today"
          @select="selectRange" @preset="selectPreset" />

        <section v-if="range" class="graph-settings card" aria-labelledby="graph-settings-title">
          <h2 id="graph-settings-title">グラフ設定</h2>
          <fieldset class="graph-devices">
            <legend>デバイス</legend>
            <div v-for="(device, i) in devices" :key="device.id" class="graph-device">
              <label>
                <input type="checkbox" :checked="!selected.includes(device.id)" @change="toggle(device.id)">
                {{ device.name }}
              </label>
              <label class="series-color">
                左の色
                <i class="series-swatch" aria-hidden="true" :style="{ backgroundColor: seriesColor(i, 'left', customColors[device.id]) }" />
                <select :aria-label="`${device.name}の左軸の線の色`"
                  :value="seriesColor(i, 'left', customColors[device.id])" @change="updateSeriesColor(device.id, 'left', $event)">
                  <option v-for="color in seriesColorOptions" :key="color.value" :value="color.value">{{ color.name }}</option>
                </select>
              </label>
              <label v-if="rightMetric" class="series-color">
                右の色
                <i class="series-swatch" aria-hidden="true" :style="{ backgroundColor: seriesColor(i, 'right', customColors[device.id]) }" />
                <select :aria-label="`${device.name}の右軸の線の色`"
                  :value="seriesColor(i, 'right', customColors[device.id])" @change="updateSeriesColor(device.id, 'right', $event)">
                  <option v-for="color in seriesColorOptions" :key="color.value" :value="color.value">{{ color.name }}</option>
                </select>
              </label>
            </div>
          </fieldset>
          <div class="graph-axes">
            <label>左軸 <select v-model="historyMetric">
              <option v-for="(item, key) in metrics" :key="key" :value="key">{{ item.name }} ({{ item.unit }})</option>
            </select></label>
            <label>右軸 <select v-model="rightAxis">
              <option value="">なし</option>
              <option v-for="(item, key) in metrics" :key="key" :value="key" :disabled="key === historyMetric">{{ item.name }} ({{ item.unit }})</option>
            </select></label>
          </div>
        </section>

        <section class="chart-panel card" aria-label="環境の推移">
          <div class="panel-heading">
            <div><p class="eyebrow">ENVIRONMENT TRENDS</p><h2>環境の推移</h2></div>
            <div class="trend-controls">
              <div v-if="tab === 'overview'" class="periods" aria-label="表示期間"><button v-for="p in periods" :key="p.id" :class="{ active: period === p.id }" :aria-pressed="period === p.id" @click="period = p.id">{{ p.name }}</button></div>
              <button class="csv-button" :disabled="!historyReady || !visible.length" @click="openCsvDialog">
                <span>↓</span> CSV出力
              </button>
              <button v-if="range" type="button" class="csv-button" :disabled="!hasHistory || !historyChart" @click="historyChart?.saveImage()">
                <span aria-hidden="true">↓</span> グラフ画像を保存
              </button>
            </div>
          </div>
          <div v-if="!range" class="chart-toolbar"><div class="metric-tabs"><button v-for="(m, key) in metrics" :key="key" :class="{ active: metric === key }" :aria-pressed="metric === key" @click="metric = key">{{ m.icon }} {{ m.name }}</button></div><span class="average">現在の平均 <strong>{{ mean }}</strong> {{ metrics[metric].unit }}</span></div>
          <div v-if="!range" class="legend"><button v-for="(d,i) in devices" :key="d.id" :class="{ muted: selected.includes(d.id) }" :aria-pressed="!selected.includes(d.id)" @click="toggle(d.id)"><i :style="{ background: deviceColors[i % deviceColors.length] }" />{{ d.name }}</button><span>JST · 区間平均</span></div>
          <ClientOnly><div v-if="!historyReady && !error" class="chart-empty">測定データを読み込んでいます…</div><HistoryChart v-else-if="hasHistory" ref="historyChart" :devices="visible" :device-ids="devices.map(d => d.id)" :metric="chartMetric" :right-metric="rightMetric" :series-colors="range ? customColors : undefined" :dark="dark" :period="period" :range="range" /><div v-else class="chart-empty"><span>⌁</span><h3>{{ devices.length && !visible.length ? '表示するデバイスを選んでください' : 'この期間の測定データはありません' }}</h3><p>収集したデータが、ここにグラフとして表示されます。</p></div><template #fallback><div class="chart-empty">グラフを読み込んでいます…</div></template></ClientOnly>
          <div class="chart-footnote">{{ range ? historyInterval : period === '1w' ? '1時間' : '5分' }}ごとの平均値を表示。空白はデータ未取得の区間です。</div>
        </section>

        <section class="table-panel card"><div class="panel-heading"><div><p class="eyebrow">MEASUREMENT LOG</p><h2>{{ tab === 'history' ? '期間内の測定履歴' : '最新の測定値' }}</h2></div><span class="table-meta">{{ tab === 'history' ? '最新100件 · 区間平均' : `${devices.length} デバイス` }}</span></div>
          <div class="table-scroll"><table v-if="tab === 'overview'"><thead><tr><th>デバイス</th><th>接続状態</th><th>温度</th><th>湿度</th><th>照度</th><th>温度センサー更新（JST）</th></tr></thead><tbody><tr v-for="d in devices" :key="d.id"><td><strong>{{ d.name }}</strong></td><td><span class="device-badge" :class="d.connection_status"><i />{{ connectionLabels[d.connection_status] }}</span></td><td>{{ format(d.latest.temperature) }} °C</td><td :title="`センサー更新: ${date(d.latest.humidity_updated_at)}`">{{ format(d.latest.humidity) }} %</td><td :title="`センサー更新: ${date(d.latest.illumination_updated_at)}`">{{ format(d.latest.illumination, 0) }} lx</td><td>{{ date(d.latest.temperature_updated_at) }}</td></tr><tr v-if="!devices.length"><td colspan="6" class="empty-cell">測定値はまだありません</td></tr></tbody></table>
          <table v-else><thead><tr><th>時刻（JST）</th><th>デバイス</th><th>温度</th><th>湿度</th><th>照度</th></tr></thead><tbody><tr v-for="row in rows" :key="row.id + row.timestamp"><td>{{ date(row.timestamp) }}</td><td><strong>{{ row.device }}</strong></td><td>{{ format(row.temperature ?? undefined) }} °C</td><td>{{ format(row.humidity ?? undefined) }} %</td><td>{{ format(row.illumination ?? undefined, 0) }} lx</td></tr><tr v-if="!rows.length"><td colspan="5" class="empty-cell">{{ !historyReady && !error ? '測定データを読み込んでいます…' : '選択した期間のデータはありません' }}</td></tr></tbody></table></div>
        </section>
        <dialog ref="csvDialog" class="export-dialog card" aria-labelledby="export-title" @cancel="exporting && $event.preventDefault()">
          <form @submit.prevent="handleExportCsv">
            <h2 id="export-title">CSV出力</h2>
            <fieldset :disabled="exporting">
              <legend>出力するデータ</legend>
              <label><input v-model="csvMode" type="radio" value="hourly" autofocus> 1時間平均</label>
              <label><input v-model="csvMode" type="radio" value="raw"> 5分おきの生データ</label>
            </fieldset>
            <p v-if="csvMessage" role="status">{{ csvMessage }}</p>
            <div class="export-actions">
              <button type="button" class="csv-button" :disabled="exporting" @click="csvDialog?.close()">キャンセル</button>
              <button type="submit" class="csv-button" :disabled="exporting">{{ exporting ? '出力中…' : 'ダウンロード' }}</button>
            </div>
          </form>
        </dialog>
        <footer>Temperature Temple <span>Nature Remo / Elasticsearch / Kibana</span></footer>
      </main>
    </div>
  </div>
</template>

<style src="./assets/css/main.css"></style>
