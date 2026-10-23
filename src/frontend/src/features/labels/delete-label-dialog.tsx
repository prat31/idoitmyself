import { useState } from 'react'
import { Loader2, Trash2 } from 'lucide-react'
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

export function DeleteLabelDialog({ label, onDeleted }: { label: Label; onDeleted?: () => void }) {
  const [open, setOpen] = useState(false)
  const deleteLabel = useDeleteLabel()

  const onConfirm = () => {
    deleteLabel.mutate(label.id, {
      onSuccess: () => {
        toast.success(`Label "${label.name}" deleted`)
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
          aria-label={`Delete label ${label.name}`}
        >
          <Trash2 />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete “{label.name}”?</AlertDialogTitle>
          <AlertDialogDescription>
            {label.email_count > 0
              ? `It will be removed from ${emails}. This can't be undone.`
              : "No emails carry this label. This can't be undone."}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleteLabel.isPending}>Cancel</AlertDialogCancel>
          <Button variant="destructive" onClick={onConfirm} disabled={deleteLabel.isPending}>
            {deleteLabel.isPending && <Loader2 className="animate-spin" />}
            Delete label
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
