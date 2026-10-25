import type { UseFormRegisterReturn } from 'react-hook-form'

import { FieldError } from '@/components/form/field'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { normalizeLabelName } from './name'

/** The normalised name, in the monospace style used wherever it's shown. */
export function NormalizedName({ name }: { name: string }) {
  return <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs text-foreground">{name}</code>
}

/** Display-name input. For a new label it previews the normalised name it will be saved under; for an
 *  existing one it shows the (fixed) normalised name. */
export function LabelNameField({
  id,
  registration,
  value,
  error,
  fixedName,
}: {
  id: string
  registration: UseFormRegisterReturn
  value: string
  error?: string
  /** An existing label's normalised name, which never changes. */
  fixedName?: string
}) {
  const preview = normalizeLabelName(value)
  return (
    <div className="space-y-2">
      <FieldLabel htmlFor={id}>Name</FieldLabel>
      <Input
        id={id}
        placeholder="e.g. Credit card bill"
        autoComplete="off"
        aria-invalid={!!error}
        aria-describedby={`${id}-help`}
        {...registration}
      />
      {error ? (
        <FieldError message={error} />
      ) : (
        <p id={`${id}-help`} className="text-xs text-muted-foreground">
          {fixedName ? (
            <>
              Normalised name <NormalizedName name={fixedName} /> stays the same.
            </>
          ) : preview ? (
            <>
              Normalised as <NormalizedName name={preview} />, which is unique and can't be changed later.
            </>
          ) : (
            'Also stored in lowercase, with spaces and symbols turned into underscores.'
          )}
        </p>
      )}
    </div>
  )
}
