/** Inline validation message under a form field. Renders nothing without a message. */
export function FieldError({ message }: { message?: string }) {
  if (!message) return null
  return <p className="text-xs text-destructive">{message}</p>
}

/** "(optional)" suffix for a field label. */
export function Optional() {
  return <span className="font-normal text-muted-foreground">(optional)</span>
}

/** A request error shown inside a dialog or form. */
export function FormError({ message }: { message: string }) {
  return (
    <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">{message}</p>
  )
}
