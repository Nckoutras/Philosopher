import BottomTabBar from '@/components/layout/BottomTabBar'
import BodyScrollLock from '@/components/layout/BodyScrollLock'
import SubscriptionBootstrap from '@/components/layout/SubscriptionBootstrap'
import ViewportDebugHUD from '@/components/layout/ViewportDebugHUD'

// dvh (not svh) so the shell tracks Chrome iOS's dynamic toolbar: when the browser
// chrome collapses on scroll the visible viewport grows ~80-100px, and an svh-sized
// shell leaves exactly that gap below the tab bar. /1.15 still compensates body zoom.
export default function TabsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative h-[calc(100dvh/1.15)] overflow-hidden flex flex-col">
      <BodyScrollLock />
      <SubscriptionBootstrap />
      <div className="flex-1 overflow-y-auto overscroll-contain">{children}</div>
      <BottomTabBar />
      <ViewportDebugHUD />
    </div>
  )
}
