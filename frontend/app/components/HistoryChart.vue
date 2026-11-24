<script setup lang="ts">
import { Chart, LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler } from 'chart.js'
import type { Device, Metric } from '../../shared/types'
import { chartMetrics, seriesColor, type SeriesColors } from '../utils/chartSeries'
Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler)
const props = defineProps<{ devices: Device[]; deviceIds: string[]; metric: Metric; rightMetric?: Metric; seriesColors?: Record<string, SeriesColors>; dark: boolean; period: string; range?: { start: string; end: string } }>()
const canvas = ref<HTMLCanvasElement | null>(null)
let chart: Chart | undefined
function saveImage() {
  const source = canvas.value
  if (!chart || !source?.width || !source.height) return

  const image = document.createElement('canvas')
  const scale = chart.currentDevicePixelRatio
  const header = Math.round(38 * scale)
  image.width = source.width
  image.height = source.height + header
  const context = image.getContext('2d')
  if (!context) return

  context.fillStyle = props.dark ? '#18272e' : '#ffffff'
  context.fillRect(0, 0, image.width, image.height)
  context.fillStyle = props.dark ? '#e4edef' : '#223c47'
  context.font = `${13 * scale}px sans-serif`
  const range = props.range
  const dateLabel = range ? `  ${range.start}${range.end === range.start ? '' : ` 〜 ${range.end}`}  JST` : ''
  context.fillText(`環境の推移${dateLabel}`, 12 * scale, 24 * scale, image.width - 24 * scale)
  context.drawImage(source, 0, header)
  image.toBlob(blob => {
    if (!blob) return
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = range ? `environment_${range.start}_${range.end}.png` : 'environment.png'
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }, 'image/png')
}
defineExpose({ saveImage })

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
      datasets: props.devices.flatMap(device => {
        const index = props.deviceIds.indexOf(device.id)
        const points = new Map(device.history.map(point => [point.timestamp, point]))
        const axes = [{ metric: props.metric, id: 'y' }]
        if (props.rightMetric) axes.push({ metric: props.rightMetric, id: 'yRight' })
        return axes.map(({ metric, id }) => {
          const color = seriesColor(index, id === 'yRight' ? 'right' : 'left', props.seriesColors?.[device.id])
          const data = times.map(timestamp => ({ x: Date.parse(timestamp), y: points.get(timestamp)?.[metric] ?? null }))
          return {
            label: range ? `${device.name} · ${chartMetrics[metric].name}` : device.name,
            yAxisID: id,
            data,
            borderColor: color,
            pointBackgroundColor: color,
            backgroundColor: `${color}12`,
            borderWidth: 2.5,
            pointRadius: 0,
            pointHoverRadius: 0,
            tension: 0,
            spanGaps: false,
            fill: !props.rightMetric && props.devices.length === 1,
          }
        })
      }),
    },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          display: Boolean(range), onClick: () => {},
          labels: { color: text, boxWidth: 18, boxHeight: 4, font: { size: 10 } },
        },
        tooltip: {
          callbacks: {
            title: items => items[0] ? timeLabel(items[0].parsed.x ?? 0, true) : '',
            label: ctx => {
              const metric = ctx.dataset.yAxisID === 'yRight' ? props.rightMetric ?? props.metric : props.metric
              return `${ctx.dataset.label}: ${ctx.parsed.y ?? '—'} ${chartMetrics[metric].unit}`
            },
          },
        },
      },
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
        y: {
          position: 'left', border: { display: false },
          grid: { color: props.dark ? '#ffffff0b' : '#153c460a' },
          ticks: { color: text, padding: 12 },
          title: { display: true, text: range ? `${chartMetrics[props.metric].name} (${chartMetrics[props.metric].unit})` : chartMetrics[props.metric].unit, color: text },
        },
        ...(props.rightMetric ? {
          yRight: {
            type: 'linear' as const, position: 'right' as const, border: { display: false },
            grid: { drawOnChartArea: false }, ticks: { color: text, padding: 12 },
            title: { display: true, text: `${chartMetrics[props.rightMetric].name} (${chartMetrics[props.rightMetric].unit})`, color: text },
          },
        } : {}),
      },
    },
  })
}
onMounted(draw)
watch(() => [props.devices, props.metric, props.rightMetric, props.seriesColors, props.dark, props.period, props.range], draw, { deep: true })
onBeforeUnmount(() => chart?.destroy())
</script>
<template><div class="chart-canvas"><canvas ref="canvas" role="img" :aria-label="`${chartMetrics[metric].name}${rightMetric ? `と${chartMetrics[rightMetric].name}` : ''}の測定履歴。数値は下の表でも確認できます。`" /></div></template>
<style scoped>.chart-canvas { height: 310px; width: 100%; } @media(max-width:600px) { .chart-canvas {height:250px} }</style>
