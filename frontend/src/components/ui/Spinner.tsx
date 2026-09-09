export function Spinner({ className = 'h-6 w-6' }: { className?: string }) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className={`animate-spin rounded-full border-2 border-brand-200 border-t-brand-600 ${className}`}
    />
  )
}

export function PageSpinner() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <Spinner className="h-10 w-10" />
    </div>
  )
}
