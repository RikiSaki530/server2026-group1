<script setup lang="ts">
import { Chart, LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler } from 'chart.js'
import type { Device, Metric } from '../../shared/types'
Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler)
const props = defineProps<{ devices: Device[]; deviceIds: string[]; metric: Metric; dark: boolean; period: string }>()
const canvas = ref<HTMLCanvasElement | null>(null)
let chart: Chart | undefined
const colors = ['#26b391', '#6383ed', '#edaa49', '#cf6ba5', '#8f80cf']
const units = { temperature: '°C', humidity: '%', illumination: 'lx' }
function draw() {
  if (!canvas.value) return
  chart?.destroy()
  const times = [...new Set(props.devices.flatMap(d => d.history.map(p => p.timestamp)))].sort()
  const text = props.dark ? '#a9b9c1' : '#70838c'
  chart = new Chart(canvas.value, {
    type: 'line',
    data: {
      labels: times.map(t => new Date(t).toLocaleString('ja-JP', { timeZone: 'Asia/Tokyo', month: props.period === '1w' ? 'numeric' : undefined, day: props.period === '1w' ? 'numeric' : undefined, hour: '2-digit', minute: '2-digit' })),
      datasets: props.devices.map((d) => {
        const i = props.deviceIds.indexOf(d.id)
        const points = new Map(d.history.map(p => [p.timestamp, p[props.metric]]))
        return { label: d.name, data: times.map(t => points.get(t) ?? null), borderColor: colors[i % colors.length], backgroundColor: `${colors[i % colors.length]}12`, borderWidth: 2.5, pointRadius: 2.5, pointHoverRadius: 5, tension: .25, spanGaps: false, fill: props.devices.length === 1 }
      }),
    },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y ?? '—'} ${units[props.metric]}` } } },
      scales: {
        x: { grid: { display: false }, border: { display: false }, ticks: { color: text, maxTicksLimit: 7, maxRotation: 0 } },
        y: { border: { display: false }, grid: { color: props.dark ? '#ffffff0b' : '#153c460a' }, ticks: { color: text, padding: 12 }, title: { display: true, text: units[props.metric], color: text } },
      },
    },
  })
}
onMounted(draw)
watch(() => [props.devices, props.metric, props.dark, props.period], draw, { deep: true })
onBeforeUnmount(() => chart?.destroy())
</script>
<template><div class="chart-canvas"><canvas ref="canvas" role="img" :aria-label="`${metric} の測定履歴。数値は下の表でも確認できます。`" /></div></template>
<style scoped>.chart-canvas { height: 310px; width: 100%; } @media(max-width:600px) { .chart-canvas {height:250px} }</style>
