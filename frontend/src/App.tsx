import { useState } from 'react'
import PreviewStage from './components/PreviewStage'
import TituloPanel from './components/TituloPanel'
import { clipsDemo } from './demo'
import { formatTime } from './lib/time'
import type { Clip, TituloVideo } from './types'

export default function App() {
  const [clips, setClips] = useState<Clip[]>(clipsDemo)
  const [selId, setSelId] = useState<string | null>(clipsDemo[0]?.id ?? null)
  const [zonasSeguras, setZonasSeguras] = useState(false)

  const sel = clips.find((c) => c.id === selId) ?? null

  const actualizarTitulo = (cambios: Partial<TituloVideo>) => {
    if (!sel) return
    setClips((prev) =>
      prev.map((c) => (c.id === sel.id ? { ...c, tituloVideo: { ...c.tituloVideo, ...cambios } } : c)),
    )
  }

  return (
    <div className="flex h-dvh flex-col pb-[env(safe-area-inset-bottom)] pt-[env(safe-area-inset-top)] lg:grid lg:grid-cols-[300px_minmax(0,1fr)_320px] lg:grid-rows-[minmax(0,1fr)]">
      {/* Lista de clips */}
      <aside className="max-h-[28dvh] shrink-0 overflow-y-auto border-b border-line bg-panel p-3 lg:max-h-none lg:border-b-0 lg:border-r">
        <h2 className="mb-3 px-1 text-xs font-medium uppercase tracking-wider text-muted">
          {clips.length} {clips.length === 1 ? 'clip' : 'clips'}
        </h2>

        {clips.length === 0 ? (
          <p className="px-1 text-sm text-muted">Todavía no hay clips. Genera uno y aparecerá aquí.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {clips.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => setSelId(c.id)}
                  aria-pressed={c.id === selId}
                  className={`press w-full min-w-0 rounded-lg border p-3 text-left ${
                    c.id === selId ? 'border-accent bg-raised' : 'border-line hover:bg-raised'
                  }`}
                >
                  <span className="line-clamp-2 wrap-break-word text-sm font-medium">{c.titulo}</span>
                  <span className="mt-1.5 flex items-center gap-2 text-xs text-muted">
                    <span className="rounded bg-bg px-1.5 py-0.5">{c.tipo}</span>
                    <span className="tnum">
                      {formatTime(c.inicio)}–{formatTime(c.fin)}
                    </span>
                    <span className="tnum ml-auto">{Math.round(c.fin - c.inicio)} s</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      {/* Vista previa */}
      <main className="flex min-h-0 flex-1 items-center justify-center p-4">
        {sel ? (
          <PreviewStage titulo={sel.tituloVideo} onChange={actualizarTitulo} zonasSeguras={zonasSeguras} />
        ) : (
          <p className="text-sm text-muted">Selecciona un clip</p>
        )}
      </main>

      {/* Ajustes */}
      <section className="max-h-[38dvh] shrink-0 overflow-y-auto border-t border-line bg-panel p-4 lg:max-h-none lg:border-l lg:border-t-0">
        {sel && (
          <>
            <h2 className="text-xs font-medium uppercase tracking-wider text-muted">Por qué se eligió</h2>
            <p className="mb-5 mt-1.5 text-sm leading-relaxed">{sel.razon}</p>
            <TituloPanel
              titulo={sel.tituloVideo}
              onChange={actualizarTitulo}
              zonasSeguras={zonasSeguras}
              onZonasSeguras={setZonasSeguras}
            />
          </>
        )}
      </section>
    </div>
  )
}