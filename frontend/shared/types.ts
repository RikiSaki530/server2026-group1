export type Metric = 'temperature' | 'humidity' | 'illumination'
export type Point = { timestamp: string } & Record<Metric, number | null>
export type Reading = {
  '@timestamp': string; device_id: string; device_name: string; source: string
  online?: boolean
  temperature?: number; humidity?: number; illumination?: number
  temperature_updated_at?: string; humidity_updated_at?: string; illumination_updated_at?: string
  motion_detected_at?: string
}
export type Device = { id: string; name: string; latest: Reading; stale: boolean; connection_status: 'online' | 'offline' | 'unknown' | 'demo'; connection_checked_at: string | null; history: Point[] }
export type Dashboard = {
  devices: Device[]; demo: boolean; collection_interval_seconds: number; generated_at: string; period: string
  collector: { error?: string; last_success?: string; last_attempt?: string; device_count?: number }
}
