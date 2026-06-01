'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { api, RateLimitError, SSEEvent, SSEEventMember } from '@/lib/api'

const MATTER_MAX = 600

type MemberBlock = {
  slug: string
  name: string
  position: string
  content: string
}

type Phase =
  | { kind: 'idle' }
  | { kind: 'convening' }
  | { kind: 'members'; members: MemberBlock[]; activeMember: string | null }
  | { kind: 'synthesis'; members: MemberBlock[]; synthesisContent: string }
  | { kind: 'done'; members: MemberBlock[]; synthesisContent: string }
  | { kind: 'safety' }
  | { kind: 'error'; message: string }

export default function CouncilPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)

  const [matter, setMatter] = useState('')
  const [source, setSource] = useState<string>('direct')
  const [mirrorId, setMirrorId] = useState<string | null>(null)
  const [phase, setPhase] = useState<Phase>({ kind: 'idle' })

  const membersRef = useRef<MemberBlock[]>([])
  const synthesisRef = useRef('')

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }
    const prefill = sessionStorage.getItem('council_prefill') ?? ''
    const src = sessionStorage.getItem('council_source') ?? 'direct'
    const mid = sessionStorage.getItem('council_mirror_id') ?? null
    sessionStorage.removeItem('council_prefill')
    sessionStorage.removeItem('council_source')
    sessionStorage.removeItem('council_mirror_id')
    if (prefill) setMatter(prefill)
    setSource(src)
    setMirrorId(mid)
  }, [token, router])

  async function handleConvene() {
    if (!matter.trim() || phase.kind !== 'idle') return

    membersRef.current = []
    synthesisRef.current = ''
    setPhase({ kind: 'convening' })

    try {
      const res = await api.streamCouncil({
        matter: matter.trim(),
        source,
        mirror_id: mirrorId,
      })

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let activeMemberSlug: string | null = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue

          let event: SSEEvent
          try {
            event = JSON.parse(raw) as SSEEvent
          } catch {
            continue
          }

          switch (event.type) {
            case 'convening':
              setPhase({ kind: 'convening' })
              break

            case 'member': {
              const ev = event as SSEEventMember
              const existing = membersRef.current.find((m) => m.slug === ev.slug)
              if (!existing) {
                membersRef.current = [
                  ...membersRef.current,
                  { slug: ev.slug, name: ev.name, position: ev.position, content: '' },
                ]
              }
              activeMemberSlug = ev.slug
              setPhase({
                kind: 'members',
                members: [...membersRef.current],
                activeMember: ev.slug,
              })
              break
            }

            case 'chunk': {
              if (activeMemberSlug && phase.kind !== 'synthesis') {
                membersRef.current = membersRef.current.map((m) =>
                  m.slug === activeMemberSlug
                    ? { ...m, content: m.content + event.data }
                    : m
                )
                setPhase((prev) => {
                  if (prev.kind === 'members') {
                    return { ...prev, members: [...membersRef.current] }
                  }
                  return prev
                })
              } else {
                synthesisRef.current += event.data
                setPhase((prev) => {
                  if (prev.kind === 'synthesis') {
                    return { ...prev, synthesisContent: synthesisRef.current }
                  }
                  return prev
                })
              }
              break
            }

            case 'synthesis_start':
              activeMemberSlug = null
              setPhase({
                kind: 'synthesis',
                members: [...membersRef.current],
                synthesisContent: '',
              })
              break

            case 'done':
              setPhase({
                kind: 'done',
                members: [...membersRef.current],
                synthesisContent: synthesisRef.current,
              })
              break

            case 'safety':
            case 'safety_override':
              setPhase({ kind: 'safety' })
              break

            case 'synthesis_error':
              setPhase({
                kind: 'done',
                members: [...membersRef.current],
                synthesisContent: synthesisRef.current,
              })
              break

            case 'error':
              setPhase({ kind: 'error', message: event.error_code ?? 'Something went wrong.' })
              break
          }
        }
      }
    } catch (err) {
      if (err instanceof RateLimitError) {
        setPhase({ kind: 'error', message: 'You have reached your weekly Council limit.' })
      } else {
        setPhase({ kind: 'error', message: 'Something went wrong. Please try again.' })
      }
    }
  }

  const isStreaming = phase.kind === 'convening' || phase.kind === 'members' || phase.kind === 'synthesis'
  const canSubmit = matter.trim().length > 0 && matter.length <= MATTER_MAX && phase.kind === 'idle'

  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum px-[24px] pt-[32px] pb-[40px] flex flex-col gap-[24px]">
      <div>
        <p className="font-lora text-[11px] uppercase tracking-[0.24em] text-bronze-dark mb-[6px]">
          THE COUNCIL
        </p>
        <h1 className="font-cormorant text-[36px] font-medium text-ink leading-tight">
          Bring your matter before them
        </h1>
      </div>

      {phase.kind === 'idle' && (
        <div className="flex flex-col gap-[12px]">
          <textarea
            value={matter}
            onChange={(e) => setMatter(e.target.value)}
            maxLength={MATTER_MAX}
            rows={6}
            placeholder="What do you want the council to consider?"
            className="w-full bg-paper border-[0.5px] border-edge rounded-[14px] px-[16px] py-[14px] font-lora text-[15px] text-ink placeholder:text-sepia/50 resize-none focus:outline-none focus:ring-1 focus:ring-bronze"
          />
          <div className="flex items-center justify-between">
            <span className={`font-lora text-[11px] ${matter.length > MATTER_MAX ? 'text-safety' : 'text-sepia'}`}>
              {matter.length} / {MATTER_MAX}
            </span>
            <button
              type="button"
              disabled={!canSubmit}
              onClick={handleConvene}
              className="font-cormorant text-[17px] font-medium px-[24px] py-[12px] rounded-[12px] bg-ink text-vellum disabled:opacity-40"
            >
              Convene the council
            </button>
          </div>
        </div>
      )}

      {phase.kind === 'convening' && (
        <p className="font-lora italic text-[15px] text-sepia">The council deliberates…</p>
      )}

      {(phase.kind === 'members' || phase.kind === 'synthesis' || phase.kind === 'done') && (
        <div className="flex flex-col gap-[28px]">
          {(phase.kind === 'members' ? phase.members : phase.members).map((member) => (
            <div key={member.slug}>
              <p className="font-cormorant text-[20px] font-medium text-ink mb-[4px]">{member.name}</p>
              <p className="font-lora text-[11px] uppercase tracking-wide text-sepia mb-[8px]">{member.position}</p>
              <p className="font-lora text-[15px] text-ink leading-relaxed whitespace-pre-wrap">{member.content}</p>
            </div>
          ))}

          {(phase.kind === 'synthesis' || phase.kind === 'done') && (
            <div>
              <p className="font-cormorant text-[20px] font-medium text-ink mb-[8px]">The council's reading</p>
              <p className="font-lora text-[15px] text-ink leading-relaxed whitespace-pre-wrap">
                {phase.synthesisContent}
              </p>
            </div>
          )}

          {phase.kind === 'done' && (
            <button
              type="button"
              onClick={() => {
                setPhase({ kind: 'idle' })
                setMatter('')
              }}
              className="font-lora text-[13px] text-sepia underline underline-offset-2 self-start"
            >
              Bring another matter
            </button>
          )}

          {isStreaming && (
            <p className="font-lora italic text-[13px] text-sepia">The council deliberates…</p>
          )}
        </div>
      )}

      {phase.kind === 'safety' && (
        <div className="bg-paper border-[0.5px] border-edge rounded-[14px] px-[16px] py-[20px]">
          <p className="font-lora text-[14px] text-charcoal leading-relaxed">
            The council cannot meet on this matter.
          </p>
          <button
            type="button"
            onClick={() => setPhase({ kind: 'idle' })}
            className="mt-[12px] font-lora text-[13px] text-sepia underline underline-offset-2"
          >
            Try a different matter
          </button>
        </div>
      )}

      {phase.kind === 'error' && (
        <div className="bg-paper border-[0.5px] border-edge rounded-[14px] px-[16px] py-[20px]">
          <p className="font-lora text-[14px] text-charcoal leading-relaxed">{phase.message}</p>
          <button
            type="button"
            onClick={() => setPhase({ kind: 'idle' })}
            className="mt-[12px] font-lora text-[13px] text-sepia underline underline-offset-2"
          >
            Try again
          </button>
        </div>
      )}
    </main>
  )
}
