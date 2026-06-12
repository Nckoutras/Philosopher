import BottomTabBar from '@/components/layout/BottomTabBar'
import BodyScrollLock from '@/components/layout/BodyScrollLock'
import SubscriptionBootstrap from '@/components/layout/SubscriptionBootstrap'
import ViewportDebugHUD from '@/components/layout/ViewportDebugHUD'

export default function TabsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative h-[100svh] overflow-hidden flex flex-col">
      <BodyScrollLock />
      <SubscriptionBootstrap />
      <div
        className="flex-1 overflow-y-auto overscroll-contain"
        // Bar is now a fixed bottom overlay (out of flow); reserve its footprint so
        // scrolled content is never hidden under it. h-16 bar + safe-area inset.
        style={{ paddingBottom: 'calc(4rem + env(safe-area-inset-bottom))' }}
      >
        {children}
      </div>
      <BottomTabBar />
      <ViewportDebugHUD />
    </div>
  )
}
