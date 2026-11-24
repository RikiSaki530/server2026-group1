import type { Metric } from '../../shared/types'

export const deviceColors = ['#26b391', '#6383ed', '#edaa49', '#cf6ba5', '#8f80cf']
export const chartMetrics: Record<Metric, { name: string; unit: string; icon: string }> = {
  temperature: { name: '温度', unit: '°C', icon: '♨' },
  humidity: { name: '湿度', unit: '%', icon: '◈' },
  illumination: { name: '照度', unit: 'lx', icon: '☼' },
}
