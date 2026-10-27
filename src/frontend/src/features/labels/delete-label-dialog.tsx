import { useState } from 'react'
import { Loader2, Trash2 } from 'lucide-react'
import { Link } from 'react-router'
import { toast } from 'sonner'

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { useDeleteLabel, type Label } from './api'

/** Deletes a label, or — while filters still write it or processors run on it — explains which to change
 *  first. */
export function DeleteLabelDialog({ label, onDeleted }: { label: Label; onDeleted?: () => void }) {
  const [open, setOpen] = useState(false)
  const deleteLabel = useDeleteLabel()
  const blocked = label.filters.length > 0 || label.processors.length > 0

  const onConfirm = () => {
    deleteLabel.mutate(label.id, {
      onSuccess: () => {
        toast.success(`Label "${label.display_name}" deleted`)
        setOpen(false)
        onDeleted?.()
      },
      onError: (error) => toast.error("Couldn't delete the label", { description: error.message }),
    })
  }

  const emails = label.email_count === 1 ? '1 email' : `${label.email_count.toLocaleString()} emails`

  return (
    <AlertDialog open={open} onOpenChange={(next) => !deleteLabel.isPending && setOpen(next)}>
      <AlertDialogTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="size-8 text-muted-foreground hover:text-destructive"
          aria-label={`Delete label ${label.display_name}`}
        >
          <Trash2 />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            {blocked ? `“${label.display_name}” is in use` : `Delete “${label.display_name}”?`}
          </AlertDialogTitle>
          <AlertDialogDescription asChild>
            {blocked ? (
              <div className="space-y-2">
                <p>
                  A label can only be deleted when no filter adds it and no processor runs on it. Point these filters
                  at another label, or delete them and the processors, first:
                </p>
                <ul className="list-inside list-disc">
                  {label.filters.map((f) => (
                    <li key={f.id}>
                      Filter{' '}
                      <Link to={`/automation/filters/${f.id}`} className="font-medium text-foreground underline-offset-2 hover:underline">
                        {f.name}
                      </Link>
                      {f.status === 'inactive' && ' (inactive)'}
                    </li>
                  ))}
                  {label.processors.map((p) => (
                    <li key={p.id}>
                      Processor{' '}
                      <Link
                        to={`/automation/processors/${p.id}`}
                        className="font-medium text-foreground underline-offset-2 hover:underline"
                      >
                        {p.name}
                      </Link>
                      {p.status === 'inactive' && ' (inactive)'}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p>
                {label.email_count > 0
                  ? `It will be removed from ${emails}. This can't be undone.`
                  : "No emails carry this label. This can't be undone."}
              </p>
            )}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleteLabel.isPending}>{blocked ? 'Close' : 'Cancel'}</AlertDialogCancel>
          {!blocked && (
            <Button variant="destructive" onClick={onConfirm} disabled={deleteLabel.isPending}>
              {deleteLabel.isPending && <Loader2 className="animate-spin" />}
              Delete label
            </Button>
          )}
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
