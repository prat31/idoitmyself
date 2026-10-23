import { useId, useState, type KeyboardEvent } from 'react'
import { Plus, X } from 'lucide-react'

import { cn } from '@/lib/utils'

type TagInputProps = {
  value: string[]
  onChange: (tags: string[]) => void
  /** Existing tags offered as one-click suggestions. */
  suggestions?: string[]
  maxTags?: number
  maxLength?: number
  placeholder?: string
  id?: string
  invalid?: boolean
}

/** Free-text tag entry: Enter or a comma adds a tag (pasting "a, b, c" adds three), Backspace on an empty field removes the last one.
 *  Tags are de-duplicated case-insensitively. */
export function TagInput({
  value,
  onChange,
  suggestions = [],
  maxTags = 20,
  maxLength = 50,
  placeholder = 'Type a tag and press Enter',
  id,
  invalid,
}: TagInputProps) {
  const [draft, setDraft] = useState('')
  const fallbackId = useId()
  const inputId = id ?? fallbackId
  const chosen = new Set(value.map((t) => t.toLowerCase()))
  const atLimit = value.length >= maxTags

  const addMany = (raws: string[]) => {
    const next = [...value]
    const seen = new Set(chosen)
    for (const raw of raws) {
      const tag = raw.trim().slice(0, maxLength)
      if (!tag || next.length >= maxTags || seen.has(tag.toLowerCase())) continue
      seen.add(tag.toLowerCase())
      next.push(tag)
    }
    if (next.length !== value.length) onChange(next)
  }

  const add = (raw: string) => addMany([raw])

  // Commas separate tags, whether typed or pasted: everything before the last comma becomes tags.
  const onDraftChange = (text: string) => {
    if (!text.includes(',')) {
      setDraft(text)
      return
    }
    const parts = text.split(',')
    addMany(parts.slice(0, -1))
    setDraft(parts[parts.length - 1])
  }

  const remove = (tag: string) => onChange(value.filter((t) => t !== tag))

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      add(draft)
      setDraft('')
    } else if (event.key === 'Backspace' && draft === '' && value.length > 0) {
      remove(value[value.length - 1])
    }
  }

  const query = draft.trim().toLowerCase()
  const visibleSuggestions = suggestions
    .filter((s) => !chosen.has(s.toLowerCase()) && (!query || s.toLowerCase().includes(query)))
    .slice(0, 8)

  return (
    <div className="space-y-2">
      <div
        className={cn(
          'flex min-h-9 w-full flex-wrap items-center gap-1.5 rounded-md border border-input bg-card px-2 py-1.5 shadow-xs transition-[color,box-shadow]',
          'focus-within:border-ring focus-within:ring-[3px] focus-within:ring-ring/30',
          invalid && 'border-destructive ring-destructive/20',
        )}
        onClick={() => document.getElementById(inputId)?.focus()}
      >
        {value.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-md bg-secondary py-0.5 pl-2 pr-1 text-xs font-medium text-secondary-foreground"
          >
            {tag}
            <button
              type="button"
              onClick={() => remove(tag)}
              className="rounded-sm p-0.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              aria-label={`Remove tag ${tag}`}
            >
              <X className="size-3" />
            </button>
          </span>
        ))}
        <input
          id={inputId}
          value={draft}
          onChange={(e) => onDraftChange(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={() => {
            add(draft)
            setDraft('')
          }}
          disabled={atLimit}
          placeholder={value.length === 0 ? placeholder : atLimit ? `Up to ${maxTags} tags` : ''}
          aria-invalid={invalid || undefined}
          className="h-6 min-w-24 flex-1 bg-transparent px-1 text-sm outline-none placeholder:text-muted-foreground/70 disabled:cursor-not-allowed"
        />
      </div>
      {visibleSuggestions.length > 0 && !atLimit && (
        <div className="flex flex-wrap items-center gap-1.5">
          {visibleSuggestions.map((s) => (
            <button
              key={s}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                add(s)
                setDraft('')
              }}
              className="inline-flex items-center gap-1 rounded-md border border-dashed px-2 py-0.5 text-xs text-muted-foreground transition-colors hover:border-solid hover:bg-accent hover:text-accent-foreground"
            >
              <Plus className="size-3" />
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
