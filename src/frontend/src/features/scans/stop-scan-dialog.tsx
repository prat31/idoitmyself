import { useState } from 'react'
import { Loader2, Square } from 'lucide-react'
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
import { useCancelScan, type Scan } from './api'

/** Stops a queued or running scan, after confirmation. */
export function StopScanDialog({ scan }: { scan: Scan }) {
  const [open, setOpen] = useState(false)
  const cancel = useCancelScan()

  const onConfirm = () => {
    cancel.mutate(scan.id, {
      onSuccess: () => {
        toast.success(`Scan of ${scan.inbox_name} stopped`)
        setOpen(false)
      },
      onError: (error) => toast.error("Couldn't stop the scan", { description: error.message }),
    })
  }

  return (
    <AlertDialog open={open} onOpenChange={(next) => !cancel.isPending && setOpen(next)}>
      <AlertDialogTrigger asChild>
        <Button variant="outline" size="sm" className="h-8">
          <Square className="size-3.5" />
          Stop
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Stop this scan of {scan.inbox_name}?</AlertDialogTitle>
          <AlertDialogDescription>
            Emails already scanned and labels already added stay. Batches in progress finish their current emails;
            the rest is skipped.
            {scan.kind === 'scheduled' && ' The next scheduled scan covers this window again.'}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={cancel.isPending}>Keep scanning</AlertDialogCancel>
          <Button variant="destructive" onClick={onConfirm} disabled={cancel.isPending}>
            {cancel.isPending && <Loader2 className="animate-spin" />}
            Stop scan
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
