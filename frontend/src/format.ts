// Number formatting: thousands separators; 2 decimals under $100, none above.

export function money(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  const abs = Math.abs(v)
  const digits = abs < 100 ? 2 : 0
  return `$${v.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })}`
}

export function cost(v: number | null | undefined): string {
  if (!v) return '$0.00'
  if (v < 0.01) return `$${v.toFixed(5)}`
  return `$${v.toFixed(2)}`
}

export function num(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined) return '—'
  return v.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: digits })
}

export function kg(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—'
  return `${num(v, v < 10 ? 1 : 0)} kg`
}

const CONDITIONS: Record<string, string> = {
  new_sealed: 'New, sealed',
  new_open_box: 'New, open box',
  refurbished: 'Refurbished',
  used_working: 'Used, working',
  used_untested: 'Used, untested',
  for_parts: 'For parts',
}

export const condition = (c: string | null | undefined) => (c ? CONDITIONS[c] ?? c : '—')

export function sentence(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s
}

export function date(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(`${iso.slice(0, 10)}T00:00:00`)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}
