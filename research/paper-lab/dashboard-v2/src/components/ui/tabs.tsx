// shadcn/ui-style component (MIT, https://ui.shadcn.com)
import * as React from 'react'
import * as T from '@radix-ui/react-tabs'
import { cn } from '@/lib/utils'
export const Tabs = T.Root
export const TabsList = React.forwardRef<React.ElementRef<typeof T.List>, React.ComponentPropsWithoutRef<typeof T.List>>(({ className, ...p }, ref) => (
  <T.List ref={ref} className={cn('inline-flex items-center gap-1 rounded-lg bg-muted p-1 text-muted-foreground', className)} {...p} />
))
TabsList.displayName = 'TabsList'
export const TabsTrigger = React.forwardRef<React.ElementRef<typeof T.Trigger>, React.ComponentPropsWithoutRef<typeof T.Trigger>>(({ className, ...p }, ref) => (
  <T.Trigger ref={ref} className={cn('inline-flex items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow [&_svg]:size-4', className)} {...p} />
))
TabsTrigger.displayName = 'TabsTrigger'
export const TabsContent = React.forwardRef<React.ElementRef<typeof T.Content>, React.ComponentPropsWithoutRef<typeof T.Content>>(({ className, ...p }, ref) => (
  <T.Content ref={ref} className={cn('mt-3 focus-visible:outline-none', className)} {...p} />
))
TabsContent.displayName = 'TabsContent'
