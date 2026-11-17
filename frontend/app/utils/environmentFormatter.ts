import type { Dashboard } from '../../shared/types'

type Device = Dashboard['devices'][number]

export interface EnvironmentCsvTable {
  headers: string[]
  rows: (string | number)[][]
  filename: string
}

function formatJstDateTime(value?: string | null): string {
  if (!value) return ''
  return new Date(value).toLocaleString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: 'Asia/Tokyo'
  })
}

function roundNumber(value?: number | null, digits = 1): number | '' {
  return value == null ? '' : Number(value.toFixed(digits))
}

export function formatEnvironmentTrendForCsv(
  visibleDevices: Device[],
  period: string
): EnvironmentCsvTable {
  const today = new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Tokyo' })

  const validRecords = visibleDevices
    .flatMap(device =>
      device.history
        .filter(p => p.temperature !== null || p.humidity !== null || p.illumination !== null)
        .map(p => ({ ...p, deviceName: device.name }))
    )
    .sort((a, b) => b.timestamp.localeCompare(a.timestamp))

  const headers = ['時刻(JST)', 'デバイス', '温度(°C)', '湿度(%)', '照度(lx)']

  const rows = validRecords.map(record => [
    formatJstDateTime(record.timestamp),
    record.deviceName,
    roundNumber(record.temperature, 1),
    roundNumber(record.humidity, 1),
    roundNumber(record.illumination, 0)
  ])

  return {
    headers,
    rows,
    filename: `environment_${period}_${today}.csv`
  }
}