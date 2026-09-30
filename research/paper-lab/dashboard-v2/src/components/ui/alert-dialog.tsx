// shadcn/ui-style AlertDialog (MIT, https://ui.shadcn.com)
import * as React from 'react'
import * as A from '@radix-ui/react-alert-dialog'
import { cn } from '@/lib/utils'
import { buttonVariants } from './button'
export const AlertDialog = A.Root
export const AlertDialogTrigger = A.Trigger
export const AlertDialogContent = React.forwardRef<React.ElementRef<typeof A.Content>, React.ComponentPropsWithoutRef<typeof A.Content>>(({ className, ...p }, ref) => (
  <A.Portal>
    <A.Overlay className="fixed inset-0 z-50 bg-black/60 data-[state=open]:animate-in data-[state=open]:fade-in-0" />
    <A.Content ref={ref} className={cn('fixed left-1/2 top-1/2 z-50 grid w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 gap-4 rounded-xl border bg-popover p-5 shadow-2xl data-[state=open]:animate-in data-[state=open]:zoom-in-95', className)} {...p} />
  </A.Portal>
))
AlertDialogContent.displayName = 'AlertDialogContent'
export function AlertDialogHeader({ className, ...p }: React.HTMLAttributes<HTMLDivElement>) { return <div className={cn('flex flex-col gap-1.5', className)} {...p} /> }
export function AlertDialogFooter({ className, ...p }: React.HTMLAttributes<HTMLDivElement>) { return <div className={cn('flex flex-col-reverse gap-2 sm:flex-row sm:justify-end', className)} {...p} /> }
export const AlertDialogTitle = React.forwardRef<React.ElementRef<typeof A.Title>, React.ComponentPropsWithoutRef<typeof A.Title>>(({ className, ...p }, ref) => (
  <A.Title ref={ref} className={cn('text-base font-semibold', className)} {...p} />
))
AlertDialogTitle.displayName = 'AlertDialogTitle'
export const AlertDialogDescription = React.forwardRef<React.ElementRef<typeof A.Description>, React.ComponentPropsWithoutRef<typeof A.Description>>(({ className, ...p }, ref) => (
  <A.Description ref={ref} className={cn('text-sm text-muted-foreground', className)} {...p} />
))
AlertDialogDescription.displayName = 'AlertDialogDescription'
export const AlertDialogAction = React.forwardRef<React.ElementRef<typeof A.Action>, React.ComponentPropsWithoutRef<typeof A.Action> & { destructive?: boolean }>(({ className, destructive, ...p }, ref) => (
  <A.Action ref={ref} className={cn(buttonVariants({ variant: destructive ? 'destructive' : 'default' }), className)} {...p} />
))
AlertDialogAction.displayName = 'AlertDialogAction'
export const AlertDialogCancel = React.forwardRef<React.ElementRef<typeof A.Cancel>, React.ComponentPropsWithoutRef<typeof A.Cancel>>(({ className, ...p }, ref) => (
  <A.Cancel ref={ref} className={cn(buttonVariants({ variant: 'outline' }), className)} {...p} />
))
AlertDialogCancel.displayName = 'AlertDialogCancel'
