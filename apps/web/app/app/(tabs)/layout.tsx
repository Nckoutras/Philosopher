import BottomTabBar from '@/components/layout/BottomTabBar'
import SubscriptionBootstrap from '@/components/layout/SubscriptionBootstrap'

export default function TabsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative min-h-screen [min-height:100svh]">
      <SubscriptionBootstrap />
      <div className="pb-16">{children}</div>
      <BottomTabBar />
    </div>
  )
}
