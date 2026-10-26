// Small line icons (Lucide-style, 16 px, 1.75 stroke). Always used next to a text label.
import type { ReactNode } from 'react'

const Svg = ({ children, className }: { children: ReactNode; className?: string }) => (
  <svg className={`icon ${className ?? ''}`} viewBox="0 0 24 24" aria-hidden="true">
    {children}
  </svg>
)

export const Check = (p: { className?: string }) => (
  <Svg {...p}>
    <path d="M20 6 9 17l-5-5" />
  </Svg>
)
export const Ban = (p: { className?: string }) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="10" />
    <path d="m4.9 4.9 14.2 14.2" />
  </Svg>
)
export const Eye = (p: { className?: string }) => (
  <Svg {...p}>
    <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z" />
    <circle cx="12" cy="12" r="3" />
  </Svg>
)
export const Help = (p: { className?: string }) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="10" />
    <path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3" />
    <path d="M12 17h.01" />
  </Svg>
)
export const Bell = (p: { className?: string }) => (
  <Svg {...p}>
    <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
    <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
  </Svg>
)
export const Chevron = (p: { className?: string }) => (
  <Svg {...p}>
    <path d="m6 9 6 6 6-6" />
  </Svg>
)
export const Leaf = (p: { className?: string }) => (
  <Svg {...p}>
    <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
    <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
  </Svg>
)
export const Info = (p: { className?: string }) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="10" />
    <path d="M12 16v-4" />
    <path d="M12 8h.01" />
  </Svg>
)
export const Lock = (p: { className?: string }) => (
  <Svg {...p}>
    <rect x="4" y="11" width="16" height="10" rx="2" />
    <path d="M8 11V7a4 4 0 0 1 8 0v4" />
  </Svg>
)
export const Copy = (p: { className?: string }) => (
  <Svg {...p}>
    <rect x="9" y="9" width="13" height="13" rx="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </Svg>
)
export const Factory = (p: { className?: string }) => (
  <Svg {...p}>
    <path d="M2 20V8l6 4V8l6 4V4h8v16Z" />
    <path d="M6 16h.01M11 16h.01M16 16h.01" />
  </Svg>
)
export const Dot = (p: { className?: string }) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="3" />
  </Svg>
)
export const Spinner = () => <span className="spinner" aria-label="working" />
