import BottomTabBar from '@/components/layout/BottomTabBar'
import BodyScrollLock from '@/components/layout/BodyScrollLock'
import SubscriptionBootstrap from '@/components/layout/SubscriptionBootstrap'
import InsightBootstrap from '@/components/layout/InsightBootstrap'
import LettersBootstrap from '@/components/layout/LettersBootstrap'

export default function TabsLayout({ children }: { children: React.ReactNode }) {
  // dvh, not svh (see interactiveWidget in app/layout.tsx): an svh shell keeps its full
  // height when the keyboard opens, and overflow-hidden + BodyScrollLock leave no way to
  // reach the clipped bottom — e.g. Today's TodaysTopicCard textarea.
  return (
    <div className="relative h-[100dvh] overflow-hidden flex flex-col">
      <BodyScrollLock />
      <SubscriptionBootstrap />
      <InsightBootstrap />
      <LettersBootstrap />
      <div
        className="flex-1 overflow-y-auto overscroll-contain"
        // Bar is now a fixed floating pill (out of flow); reserve its footprint so
        // scrolled content clears it. h-16 pill + safe-area + 12px lift + 8px breathing.
        style={{ paddingBottom: 'calc(4rem + env(safe-area-inset-bottom) + 12px + 8px)' }}
      >
        {children}
      </div>
      <BottomTabBar />
    </div>
  )
}
