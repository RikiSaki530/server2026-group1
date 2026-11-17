function escapeCsvCell(value: unknown): string {
  if (value === null || value === undefined) return ''
  const str = String(value)
  // カンマ、ダブルクォーテーション、改行(\r, \n)が含まれる場合を含め、すべて安全にクォート処理する
  return `"${str.replace(/"/g, '""')}"`
}

export function buildCsvContent(headers: string[], rows: unknown[][]): string {
  const headerLine = headers.map(escapeCsvCell).join(',')
  const dataLines = rows.map(row => row.map(escapeCsvCell).join(','))
  // Windows版Excelの文字化け対策としてBOM(\uFEFF)を先頭に付与
  return '\uFEFF' + [headerLine, ...dataLines].join('\r\n')
}

export function downloadCsvFile(headers: string[], rows: unknown[][], filename: string): void {
  const csvContent = buildCsvContent(headers, rows)
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}