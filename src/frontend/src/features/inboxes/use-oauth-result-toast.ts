import { useEffect } from 'react'
import { useSearchParams } from 'react-router'
import { toast } from 'sonner'

const errorMessages: Record<string, string> = {
  access_denied: 'You cancelled the Google sign-in.',
  missing_scope: 'Gmail read access is required. Please allow it on the Google consent screen.',
  invalid_state: 'The sign-in link expired or was already used. Please try again.',
  missing_refresh_token: "Google didn't grant offline access. Please try again.",
}

/** The Gmail OAuth callback redirects back with `?oauth=...`; announce the result once, then clean the URL. */
export function useOAuthResultToast() {
  const [params, setParams] = useSearchParams()
  const result = params.get('oauth')
  const reason = params.get('reason')

  useEffect(() => {
    if (!result) return
    // A fixed toast id de-duplicates StrictMode's double effect run.
    if (result === 'connected') {
      toast.success('Inbox connected', { id: 'oauth-result' })
    } else if (result === 'reconnected') {
      toast.success('Inbox reconnected', {
        id: 'oauth-result',
        description: 'This account was already connected; its details and access were updated.',
      })
    } else if (result === 'error') {
      toast.error("Couldn't connect the inbox", {
        id: 'oauth-result',
        description: errorMessages[reason ?? ''] ?? 'Something went wrong. Please try again.',
      })
    }
    setParams({}, { replace: true })
  }, [result, reason, setParams])
}
