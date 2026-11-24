import type { Metric } from '../../shared/types'

export const deviceColors = ['#26b391', '#6383ed', '#edaa49', '#cf6ba5', '#8f80cf']
const rightAxisColors = ['#d45a22', '#a53591', '#8051d1', '#ae7212', '#df4361']
export const seriesColorOptions = [
  { name: '緑', value: '#26b391' },
  { name: '青', value: '#6383ed' },
  { name: '黄', value: '#edaa49' },
  { name: 'ピンク', value: '#cf6ba5' },
  { name: '薄紫', value: '#8f80cf' },
  { name: 'オレンジ', value: '#d45a22' },
  { name: '赤紫', value: '#a53591' },
  { name: '紫', value: '#8051d1' },
  { name: '茶', value: '#ae7212' },
  { name: '赤', value: '#df4361' },
]
export type SeriesColors = Partial<Record<'left' | 'right', string>>

export function seriesColor(index: number, axis: 'left' | 'right', custom?: SeriesColors) {
  const palette = axis === 'left' ? deviceColors : rightAxisColors
  return custom?.[axis] ?? palette[Math.max(0, index) % palette.length]!
}

export const chartMetrics: Record<Metric, { name: string; unit: string; icon: string }> = {
  temperature: { name: '温度', unit: '°C', icon: '♨' },
  humidity: { name: '湿度', unit: '%', icon: '◈' },
  illumination: { name: '照度', unit: 'lx', icon: '☼' },
}
