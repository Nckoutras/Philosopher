import toast from 'react-hot-toast'
import { Bookmark } from 'lucide-react'

export function renderSavedToast(): void {
  toast.custom(
    () => (
      <div
        style={{
          background: 'var(--ink)',
          color: 'var(--vellum)',
          padding: '9px 16px',
          borderRadius: '4px',
          fontFamily: 'var(--font-lora), Georgia, serif',
          fontSize: '12px',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
        }}
      >
        <Bookmark
          size={11}
          strokeWidth={1}
          fill="var(--bronze)"
          color="var(--bronze)"
        />
        Saved to your reflections
      </div>
    ),
    { position: 'bottom-center', duration: 2000 },
  )
}
