import type { RunEmailTab } from './api'

export const RUN_EMAIL_TABS: { id: RunEmailTab; label: string; empty: string }[] = [
  { id: 'matched', label: 'Matched', empty: 'No emails matched in this run.' },
  { id: 'near', label: 'Near threshold', empty: 'No answers close to the threshold.' },
  { id: 'not_matched', label: 'Not matched', empty: 'No unmatched answers attributed to this run.' },
  { id: 'skipped', label: 'Skipped (reused)', empty: 'Nothing was reused from earlier runs.' },
]
