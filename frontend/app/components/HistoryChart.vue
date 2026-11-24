<script setup lang="ts">
import { Chart, LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler } from 'chart.js'
import type { Device, Metric } from '../../shared/types'
Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler)
const props = defineProps<{ devices: Device[]; deviceIds: string[]; metric: Metric; dark: boolean; period: string; range?: { start: string; end: string } }>()
const canvas = ref<HTMLCanvasElement | null>(null)
let chart: Chart | undefined
const colors = ['#26b391', '#6383ed', '#edaa49', '#cf6ba5', '#8f80cf']
const units = { temperature: '°C', humidity: '%', illumination: 'lx' }
function draw() {
  if (!canvas.value) return
  chart?.destroy()
  const times = [...new Set(props.devices.flatMap(d => d.history.map(p => p.timestamp)))].sort()
  const text = props.dark ? '#a9b9c1' : '#70838c'
  const range = props.range
  const start = range ? Date.parse(range.start + 'T00:00:00+09:00') : undefined
  const end = range ? Date.parse(range.end + 'T00:00:00+09:00') + 86400000 : undefined
  const multiDay = range ? range.start !== range.end : props.period === '1w'
  const timeLabel = (timestamp: number, includeDate: boolean) => new Date(timestamp).toLocaleString('ja-JP', {
    timeZone: 'Asia/Tokyo', month: includeDate ? 'numeric' : undefined,
    day: includeDate ? 'numeric' : undefined, hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  })
  chart = new Chart(canvas.value, {
    type: 'line',
    data: {
      datasets: props.devices.map((d) => {
        const i = props.deviceIds.indexOf(d.id)
        const points = new Map(d.history.map(p => [p.timestamp, p[props.metric]]))
        return { label: d.name, data: times.map(t => ({ x: Date.parse(t), y: points.get(t) ?? null })), borderColor: colors[i % colors.length], backgroundColor: `${colors[i % colors.length]}12`, borderWidth: 2.5, pointRadius: 2.5, pointHoverRadius: 5, tension: .25, spanGaps: false, fill: props.devices.length === 1 }
      }),
    },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { display: false }, tooltip: { callbacks: { title: items => items[0] ? timeLabel(items[0].parsed.x ?? 0, true) : '', label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y ?? '—'} ${units[props.metric]}` } } },
      scales: {
        x: {
          type: 'linear', min: start, max: end,
          grid: { display: false }, border: { display: false },
          afterBuildTicks: scale => {
            if (start === undefined || end === undefined) return
            const days = (end - start) / 86400000
            const step = multiDay ? Math.ceil(days / 7) * 86400000 : 6 * 3600000
            scale.ticks = Array.from({ length: Math.ceil((end - start) / step) }, (_, i) => ({ value: start + i * step }))
          },
          ticks: {
            color: text, maxTicksLimit: 7, maxRotation: 0,
            callback: value => range && multiDay
              ? new Date(Number(value)).toLocaleDateString('ja-JP', { timeZone: 'Asia/Tokyo', month: 'numeric', day: 'numeric' })
              : timeLabel(Number(value), multiDay),
          },
        },
        y: { border: { display: false }, grid: { color: props.dark ? '#ffffff0b' : '#153c460a' }, ticks: { color: text, padding: 12 }, title: { display: true, text: units[props.metric], color: text } },
      },
    },
  })
}
onMounted(draw)
watch(() => [props.devices, props.metric, props.dark, props.period, props.range], draw, { deep: true })
onBeforeUnmount(() => chart?.destroy())
</script>
<template><div class="chart-canvas"><canvas ref="canvas" role="img" :aria-label="`${metric} の測定履歴。数値は下の表でも確認できます。`" /></div></template>
<style scoped>.chart-canvas { height: 310px; width: 100%; } @media(max-width:600px) { .chart-canvas {height:250px} }</style>
