import { forwardRef, type InputHTMLAttributes, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react'

interface FieldWrapperProps {
  label?: string
  error?: string
  hint?: string
  id: string
}

function FieldChrome({
  label,
  error,
  hint,
  id,
  children,
}: FieldWrapperProps & { children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-slate-700">
          {label}
        </label>
      )}
      {children}
      {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
      {error && <p className="text-xs font-medium text-red-600">{error}</p>}
    </div>
  )
}

const baseInputClasses =
  'rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100 disabled:bg-slate-100'

type InputProps = InputHTMLAttributes<HTMLInputElement> & FieldWrapperProps

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, error, hint, id, className = '', ...rest },
  ref,
) {
  return (
    <FieldChrome label={label} error={error} hint={hint} id={id}>
      <input
        id={id}
        ref={ref}
        className={`${baseInputClasses} ${error ? 'border-red-400 focus:border-red-500 focus:ring-red-100' : ''} ${className}`}
        {...rest}
      />
    </FieldChrome>
  )
})

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & FieldWrapperProps

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { label, error, hint, id, className = '', ...rest },
  ref,
) {
  return (
    <FieldChrome label={label} error={error} hint={hint} id={id}>
      <textarea
        id={id}
        ref={ref}
        className={`${baseInputClasses} ${error ? 'border-red-400 focus:border-red-500 focus:ring-red-100' : ''} ${className}`}
        {...rest}
      />
    </FieldChrome>
  )
})

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & FieldWrapperProps

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, error, hint, id, className = '', children, ...rest },
  ref,
) {
  return (
    <FieldChrome label={label} error={error} hint={hint} id={id}>
      <select
        id={id}
        ref={ref}
        className={`${baseInputClasses} ${error ? 'border-red-400 focus:border-red-500 focus:ring-red-100' : ''} ${className}`}
        {...rest}
      >
        {children}
      </select>
    </FieldChrome>
  )
})
