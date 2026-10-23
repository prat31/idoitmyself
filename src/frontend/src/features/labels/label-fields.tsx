import type { UseFormRegisterReturn } from 'react-hook-form'

import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'

export function FieldError({ message }: { message?: string }) {
  if (!message) return null
  return <p className="text-xs text-destructive">{message}</p>
}

export function Optional() {
  return <span className="font-normal text-muted-foreground">(optional)</span>
}

/** Per-label match threshold: Jev's probability must reach it for a run to apply the label. */
export function ThresholdField({
  id,
  registration,
  error,
}: {
  id: string
  registration: UseFormRegisterReturn
  error?: string
}) {
  return (
    <div className="space-y-2">
      <FieldLabel htmlFor={id}>Match threshold</FieldLabel>
      <Input
        id={id}
        type="number"
        inputMode="decimal"
        step={0.05}
        min={0.05}
        max={0.95}
        className="w-28 tabular-nums"
        aria-invalid={!!error}
        {...registration}
      />
      {error ? (
        <FieldError message={error} />
      ) : (
        <p className="text-xs text-muted-foreground">
          How confident the model must be (0–1) before a run applies this label. Higher means fewer, surer matches.
        </p>
      )}
    </div>
  )
}
