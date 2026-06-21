import toast from 'react-hot-toast'

// Undo toast for a discarded insight. Mirrors renderSavedToast's styling (ink
// bg, vellum text, Lora 12px). The caller commits the dismiss after the 5s
// window; tapping Undo runs onUndo and closes the toast.
export function renderDiscardUndoToast(onUndo: () => void): void {
  toast.custom(
    (t) => (
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
          gap: '12px',
        }}
      >
        <span>Insight discarded</span>
        <button
          type="button"
          onClick={() => {
            onUndo()
            toast.dismiss(t.id)
          }}
          style={{
            color: 'var(--bronze)',
            textDecoration: 'underline',
            fontFamily: 'inherit',
            fontSize: 'inherit',
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            padding: 0,
          }}
        >
          Undo
        </button>
      </div>
    ),
    { position: 'bottom-center', duration: 5000 },
  )
}
