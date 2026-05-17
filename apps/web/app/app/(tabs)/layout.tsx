import BottomTabBar from '@/components/layout/BottomTabBar'

export default function TabsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative min-h-screen [min-height:100svh]">
      <div className="pb-16">{children}</div>
      <BottomTabBar />
    </div>
  )
}
