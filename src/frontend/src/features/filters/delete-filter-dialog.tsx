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
import { useDeleteFilter, type Filter } from './api'

export function DeleteFilterDialog({ filter, onDeleted }: { filter: Filter; onDeleted?: () => void }) {
  const [open, setOpen] = useState(false)
  const deleteFilter = useDeleteFilter()

  const onConfirm = () => {
    deleteFilter.mutate(filter.id, {
      onSuccess: () => {
        toast.success(`Filter "${filter.name}" deleted`)
        setOpen(false)
        onDeleted?.()
      },
      onError: (error) => toast.error("Couldn't delete the filter", { description: error.message }),
    })
  }

  return (
    <AlertDialog open={open} onOpenChange={(next) => !deleteFilter.isPending && setOpen(next)}>
      <AlertDialogTrigger asChild>
        <Button type="button" variant="outline" className="text-destructive hover:text-destructive">
          <Trash2 />
          Delete
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete “{filter.name}”?</AlertDialogTitle>
          <AlertDialogDescription>
            It stops labelling new email. Labels it already added stay on their emails. To pause it instead, make it
            inactive.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleteFilter.isPending}>Cancel</AlertDialogCancel>
          <Button variant="destructive" onClick={onConfirm} disabled={deleteFilter.isPending}>
            {deleteFilter.isPending && <Loader2 className="animate-spin" />}
            Delete filter
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
