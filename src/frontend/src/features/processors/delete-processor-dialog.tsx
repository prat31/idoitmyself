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
import { useDeleteProcessor, type Processor } from './api'

export function DeleteProcessorDialog({ processor, onDeleted }: { processor: Processor; onDeleted?: () => void }) {
  const [open, setOpen] = useState(false)
  const deleteProcessor = useDeleteProcessor()

  const onConfirm = () => {
    deleteProcessor.mutate(processor.id, {
      onSuccess: () => {
        toast.success(`Processor "${processor.name}" deleted`)
        setOpen(false)
        onDeleted?.()
      },
      onError: (error) => toast.error("Couldn't delete the processor", { description: error.message }),
    })
  }

  return (
    <AlertDialog open={open} onOpenChange={(next) => !deleteProcessor.isPending && setOpen(next)}>
      <AlertDialogTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="size-8 text-muted-foreground hover:text-destructive"
          aria-label={`Delete processor ${processor.name}`}
        >
          <Trash2 />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete “{processor.name}”?</AlertDialogTitle>
          <AlertDialogDescription>
            It stops running on new emails, and runs still waiting are cancelled. The results it already extracted are
            kept. To pause it instead, make it inactive.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleteProcessor.isPending}>Cancel</AlertDialogCancel>
          <Button variant="destructive" onClick={onConfirm} disabled={deleteProcessor.isPending}>
            {deleteProcessor.isPending && <Loader2 className="animate-spin" />}
            Delete processor
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
