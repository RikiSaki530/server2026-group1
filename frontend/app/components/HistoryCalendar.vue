<script setup lang="ts">
const props = defineProps<{ start: string; end: string; today: string }>()
const emit = defineEmits<{ select: [start: string, end: string]; preset: [days: number] }>()
const open = ref(false)
const dateButton = ref<HTMLButtonElement | null>(null)
const anchor = ref('')
const month = ref(props.start.slice(0, 7))
const weekdays = ['日', '月', '火', '水', '木', '金', '土']
const presets = [{ label: '1日', days: 1 }, { label: '1週間', days: 7 }, { label: '1ヶ月', days: 0 }]
const dayMs = 86400000
const first = computed(() => new Date(month.value + '-01T00:00:00Z'))
const days = computed(() => {
  const next = new Date(first.value)
  next.setUTCMonth(next.getUTCMonth() + 1)
  return Array.from({ length: (next.getTime() - first.value.getTime()) / dayMs }, (_, i) =>
    new Date(first.value.getTime() + i * dayMs).toISOString().slice(0, 10))
})
function moveMonth(offset: number) {
  const next = new Date(first.value)
  next.setUTCMonth(next.getUTCMonth() + offset)
  month.value = next.toISOString().slice(0, 7)
}
function close() {
  open.value = false
  anchor.value = ''
}
function closeFromCalendar() {
  if (!open.value) return
  close()
  dateButton.value?.focus()
}
function toggle() {
  if (open.value) return close()
  month.value = props.start.slice(0, 7)
  open.value = true
}
function disabled(day: string) {
  return day > props.today || Boolean(anchor.value && Math.abs(Date.parse(day) - Date.parse(anchor.value)) >= 366 * dayMs)
}
function select(day: string) {
  if (!anchor.value) {
    anchor.value = day
    emit('select', day, day)
    return
  }
  const [start, end] = [anchor.value, day].sort() as [string, string]
  emit('select', start, end)
  closeFromCalendar()
}
</script>

<template>
  <section class="history-calendar card" aria-label="表示期間（日本時間）" @keydown.esc="closeFromCalendar">
    <div class="calendar-controls">
      <div class="periods">
        <button v-for="preset in presets" :key="preset.days" type="button" @click="close(); emit('preset', preset.days)">
          {{ preset.label }}
        </button>
      </div>
      <button ref="dateButton" type="button" class="csv-button" :aria-expanded="open" @click="toggle">
        <span class="calendar-icon" aria-hidden="true"></span>
        <span>{{ start.replaceAll('-', '/') }}<template v-if="end !== start">〜{{ end.replaceAll('-', '/') }}</template></span>
        <span aria-hidden="true">▾</span>
      </button>
    </div>
    <div v-if="open" class="calendar-body">
      <div class="calendar-controls">
        <button type="button" class="csv-button" aria-label="前の月" @click="moveMonth(-1)">‹</button>
        <strong>{{ Number(month.slice(0, 4)) }}年{{ Number(month.slice(5)) }}月</strong>
        <button type="button" class="csv-button" aria-label="次の月" :disabled="month >= today.slice(0, 7)" @click="moveMonth(1)">›</button>
      </div>
      <p class="calendar-hint">{{ anchor ? '終了日を選択（最大366日）' : '日付を選択。期間を指定するには続けて終了日を選択' }}</p>
      <div class="calendar-grid">
        <span v-for="weekday in weekdays" :key="weekday">{{ weekday }}</span>
        <span v-for="blank in first.getUTCDay()" :key="blank" aria-hidden="true" />
        <button v-for="day in days" :key="day" type="button" :disabled="disabled(day)"
          :aria-label="day" :aria-current="day === today ? 'date' : undefined"
          :aria-pressed="day >= start && day <= end" :class="{ endpoint: day === start || day === end }"
          @click="select(day)">{{ Number(day.slice(8)) }}</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.history-calendar { padding: 12px 16px; margin-bottom: 16px; }
.calendar-controls { display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
.calendar-icon {
  position: relative;
  width: 14px;
  height: 13px;
  border: 1px solid currentColor;
  border-radius: 3px;
  color: var(--accent);
  background: linear-gradient(currentColor, currentColor) 0 3px / 100% 1px no-repeat;
}
.calendar-icon::before {
  content: '';
  position: absolute;
  top: -3px;
  left: 3px;
  width: 1px;
  height: 4px;
  background: currentColor;
  box-shadow: 5px 0 currentColor;
}
.calendar-body { max-width: 340px; margin-top: 14px; }
.calendar-hint { font-size: 11px; color: var(--muted); }
.calendar-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); text-align: center; gap: 3px; font-size: 12px; }
.calendar-grid span { color: var(--muted); padding: 6px 0; }
.calendar-grid button { min-height: 36px; border: 0; border-radius: 6px; background: transparent; color: var(--ink); }
.calendar-grid button:hover:not(:disabled), .calendar-grid button[aria-pressed="true"] { background: var(--accent-soft); color: var(--accent); }
.calendar-grid button.endpoint[aria-pressed="true"] { background: var(--accent); color: var(--surface); }
.calendar-grid button:disabled, .calendar-controls button:disabled { cursor: not-allowed; }
</style>
