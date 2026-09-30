// shadcn/ui-style Dialog + Sheet (MIT, https://ui.shadcn.com)
import * as React from 'react'
import * as D from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
export const Dialog = D.Root
export const DialogTrigger = D.Trigger
export const DialogClose = D.Close
const Overlay = React.forwardRef<React.ElementRef<typeof D.Overlay>, React.ComponentPropsWithoutRef<typeof D.Overlay>>(({ className, ...p }, ref) => (
  <D.Overlay ref={ref} className={cn('fixed inset-0 z-50 bg-black/60 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=closed]:animate-out data-[state=closed]:fade-out-0', className)} {...p} />
))
Overlay.displayName = 'Overlay'
export const DialogContent = React.forwardRef<React.ElementRef<typeof D.Content>, React.ComponentPropsWithoutRef<typeof D.Content>>(({ className, children, ...p }, ref) => (
  <D.Portal>
    <Overlay />
    <D.Content ref={ref} className={cn('fixed left-1/2 top-1/2 z-50 grid w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 gap-4 rounded-xl border bg-popover p-5 shadow-2xl data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95 max-h-[90dvh] overflow-y-auto', className)} {...p}>
      {children}
      <D.Close className="absolute right-3 top-3 rounded-sm opacity-70 hover:opacity-100 focus-visible:ring-2 focus-visible:ring-ring" aria-label="Fechar"><X className="size-4" /></D.Close>
    </D.Content>
  </D.Portal>
))
DialogContent.displayName = 'DialogContent'
export const SheetContent = React.forwardRef<React.ElementRef<typeof D.Content>, React.ComponentPropsWithoutRef<typeof D.Content>>(({ className, children, ...p }, ref) => (
  <D.Portal>
    <Overlay />
    <D.Content ref={ref} className={cn('fixed inset-y-0 right-0 z-50 flex h-full w-full flex-col border-l bg-background shadow-2xl sm:max-w-3xl data-[state=open]:animate-in data-[state=open]:slide-in-from-right data-[state=closed]:animate-out data-[state=closed]:slide-out-to-right', className)} {...p}>
      {children}
      <D.Close className="absolute right-3 top-3 rounded-md p-1 opacity-70 hover:bg-accent hover:opacity-100 focus-visible:ring-2 focus-visible:ring-ring" aria-label="Fechar painel"><X className="size-5" /></D.Close>
    </D.Content>
  </D.Portal>
))
SheetContent.displayName = 'SheetContent'
export function DialogHeader({ className, ...p }: React.HTMLAttributes<HTMLDivElement>) { return <div className={cn('flex flex-col gap-1.5 pr-6', className)} {...p} /> }
export function DialogFooter({ className, ...p }: React.HTMLAttributes<HTMLDivElement>) { return <div className={cn('flex flex-col-reverse gap-2 sm:flex-row sm:justify-end', className)} {...p} /> }
export const DialogTitle = React.forwardRef<React.ElementRef<typeof D.Title>, React.ComponentPropsWithoutRef<typeof D.Title>>(({ className, ...p }, ref) => (
  <D.Title ref={ref} className={cn('text-base font-semibold', className)} {...p} />
))
DialogTitle.displayName = 'DialogTitle'
export const DialogDescription = React.forwardRef<React.ElementRef<typeof D.Description>, React.ComponentPropsWithoutRef<typeof D.Description>>(({ className, ...p }, ref) => (
  <D.Description ref={ref} className={cn('text-sm text-muted-foreground', className)} {...p} />
))
DialogDescription.displayName = 'DialogDescription'
