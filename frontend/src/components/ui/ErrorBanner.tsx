export function ErrorBanner({ message, className = '' }: { message: string; className?: string }) {
  return (
    <div
      role="alert"
      className={`rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 ${className}`}
    >
      {message}
    </div>
  )
}

export function InfoBanner({ message, className = '' }: { message: string; className?: string }) {
  return (
    <div className={`rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-700 ${className}`}>
      {message}
    </div>
  )
}

export function SuccessBanner({ message, className = '' }: { message: string; className?: string }) {
  return (
    <div
      className={`rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 ${className}`}
    >
      {message}
    </div>
  )
}
