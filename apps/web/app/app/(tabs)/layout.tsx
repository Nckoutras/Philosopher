import BottomTabBar from '@/components/layout/BottomTabBar'
import BodyScrollLock from '@/components/layout/BodyScrollLock'
import SubscriptionBootstrap from '@/components/layout/SubscriptionBootstrap'
import TabsShell from '@/components/layout/TabsShell'

export default function TabsLayout({ children }: { children: React.ReactNode }) {
  return (
    <TabsShell>
      <BodyScrollLock />
      <SubscriptionBootstrap />
      <div className="flex-1 overflow-y-auto overscroll-contain">{children}</div>
      <BottomTabBar />
    </TabsShell>
  )
}
