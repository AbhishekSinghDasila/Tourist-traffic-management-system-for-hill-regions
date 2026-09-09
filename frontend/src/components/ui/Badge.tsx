import type { HTMLAttributes } from 'react'

type Tone = 'green' | 'amber' | 'red' | 'slate' | 'blue'

const toneClasses: Record<Tone, string> = {
  green: 'bg-emerald-100 text-emerald-800',
  amber: 'bg-amber-100 text-amber-800',
  red: 'bg-red-100 text-red-800',
  slate: 'bg-slate-100 text-slate-700',
  blue: 'bg-sky-100 text-sky-800',
}

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone
}

export function Badge({ tone = 'slate', className = '', children, ...rest }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${toneClasses[tone]} ${className}`}
      {...rest}
    >
      {children}
    </span>
  )
}

/** Maps backend risk_level (GREEN/AMBER/RED) to a Badge tone. */
export function riskTone(risk: string): Tone {
  if (risk === 'GREEN') return 'green'
  if (risk === 'AMBER') return 'amber'
  if (risk === 'RED') return 'red'
  return 'slate'
}

/** Maps complaint/alert status strings to a reasonable Badge tone. */
export function statusTone(status: string): Tone {
  switch (status) {
    case 'RESOLVED':
    case 'CLOSED':
    case 'ACTIVE':
      return status === 'ACTIVE' ? 'red' : 'green'
    case 'PENDING':
    case 'PENDING_REVIEW':
      return 'amber'
    case 'ASSIGNED':
    case 'IN_PROGRESS':
      return 'blue'
    case 'CANCELLED':
    case 'ARCHIVED':
      return 'slate'
    default:
      return 'slate'
  }
}
