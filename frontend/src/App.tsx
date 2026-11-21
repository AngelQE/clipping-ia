import { useCallback, useEffect, useRef, useState } from 'react'
import type { ChangeEvent, ReactNode } from 'react'
import { Check, RefreshCw, Save, Undo2, Upload, X } from 'lucide-react'
import { cambiarEstado, cancelarTrabajo, guardarClip, listarClips, listarTrabajos } from './api'
import PreviewStage from './components/PreviewStage'
import Timeline from './components/Timeline'
import TituloPanel from './components/TituloPanel'
import { clipsDemo } from './demo'
import { clamp } from './lib/num'
import { formatTime } from './lib/time'
import { useAncho } from './lib/useAncho'
import type { Clip, Estado, TituloVideo, Trabajo } from './types'

type Modo = 'cargando' | 'real' | 'demo' | 'error'
type Filtro = 'todos' | Estado

const FILTROS: Filtro[] = ['todos', 'pendiente', 'aprobado', 'descartado']
const ETIQUETA: Record<Filtro, string> = { todos: 'Todos', pendiente: 'Pend.', aprobado: 'Aprob.', descartado: 'Desc.' }
const NOMBRE: Record<Filtro, string> = {
  todos: 'Todos',
  pendiente: 'Pendientes',
  aprobado: 'Aprobados',
  descartado: 'Descartados',
}

const firma = (c: Clip) => JSON.stringify([c.inicio, c.fin, c.tituloVideo])
const recortar = (texto: string, max = 40) => (texto.length > max ? `${texto.slice(0, max - 1)}…` : texto)
const espera = (ms: number) => new Promise((ok) => setTimeout(ok, ms))

function Atajo({ children }: { children: ReactNode }) {
  return (
    <kbd className="rounded border border-current/30 px-1 text-[10px] font-medium leading-4 opacity-70">
      {children}
    </kbd>
  )
}

function Spinner() {
  return (
    <span
      aria-hidden
      className="inline-block h-3.5 w-3.5 shrink-0 rounded-full border-2 border-current border-t-transparent motion-safe:animate-spin"
    />
  )
}

function Divisor({ etiqueta, panel }: { etiqueta: string; panel: ReturnType<typeof useAncho> }) {
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={etiqueta}
      aria-valuenow={panel.ancho}
      aria-valuemin={panel.min}
      aria-valuemax={panel.max}
      tabIndex={0}
      {...panel.agarre}
      className="relative z-10 cursor-col-resize touch-none bg-line transition-colors duration-150 after:absolute after:inset-y-0 after:-left-1.5 after:-right-1.5 hover:bg-accent/60 focus-visible:bg-accent"
    />
  )
}

export default function App() {
  const [modo, setModo] = useState<Modo>('cargando')
  const [errorCarga, setErrorCarga] = useState('')
  const [clips, setClips] = useState<Clip[]>([])
  const [base, setBase] = useState<Record<string, Clip>>({}) // lo último guardado, por clip
  const [selId, setSelId] = useState<string | null>(null)
  const [filtro, setFiltro] = useState<Filtro>('todos')
  const [zonasSeguras, setZonasSeguras] = useState(false)
  const [videoLocal, setVideoLocal] = useState<string | null>(null) // solo para la demostración
  const [fps, setFps] = useState(30)
  const [ocupado, setOcupado] = useState(false) // cambios de estado, que son instantáneos
  const [trabajos, setTrabajos] = useState<Record<string, Trabajo>>({}) // regeneraciones en marcha, por clip
  const [cancelando, setCancelando] = useState<Record<string, boolean>>({})
  const [aviso, setAviso] = useState<{ tipo: 'ok' | 'error' | 'info'; texto: string } | null>(null)

  const videoRef = useRef<HTMLVideoElement>(null)
  const archivoRef = useRef<HTMLInputElement>(null)
  const izq = useAncho(300, 240, 480, true)
  const der = useAncho(320, 260, 520, false)

  // Aplica lo que informa el servidor sobre los trabajos
  const procesarTrabajos = useCallback((lista: Trabajo[]) => {
    const activos: Record<string, Trabajo> = {}
    for (const t of lista) {
      if (t.estado === 'en_cola' || t.estado === 'procesando') {
        activos[t.id] = t
      } else if (t.estado === 'listo' && t.clip) {
        const clip = t.clip
        setClips((prev) => prev.map((c) => (c.id === clip.id ? clip : c)))
        setBase((prev) => ({ ...prev, [clip.id]: clip }))
        setAviso({
          tipo: 'ok',
          texto: `«${recortar(clip.titulo)}» ${t.aprobar ? 'regenerado y aprobado' : 'regenerado'}`,
        })
      } else if (t.estado === 'error') {
        setAviso({ tipo: 'error', texto: t.mensaje || 'No se pudo regenerar el clip' })
      } else if (t.estado === 'cancelado') {
        setAviso({ tipo: 'info', texto: 'Cancelado: el clip sigue como estaba' })
      }
    }
    setTrabajos(activos)
    setCancelando((prev) => Object.fromEntries(Object.entries(prev).filter(([id]) => activos[id])))
  }, [])

  const aplicar = useCallback((lista: Clip[], nuevoModo: Modo) => {
    setClips(lista)
    setBase(Object.fromEntries(lista.map((c) => [c.id, c])))
    setSelId(lista.find((c) => c.estado === 'pendiente')?.id ?? lista[0]?.id ?? null)
    setTrabajos({})
    setCancelando({})
    setModo(nuevoModo)
    setAviso(null)
  }, [])

  const cargar = useCallback(() => {
    setModo('cargando')
    listarClips()
      .then((lista) => {
        aplicar(lista, 'real')
        // Si había regeneraciones en marcha antes de recargar la página, se retoman
        return listarTrabajos()
          .then(procesarTrabajos)
          .catch(() => {})
      })
      .catch((e: unknown) => {
        setErrorCarga(e instanceof Error ? e.message : 'No se pudo conectar con el servidor.')
        setModo('error')
      })
  }, [aplicar, procesarTrabajos])

  useEffect(() => {
    cargar()
  }, [cargar])

  // Mientras haya regeneraciones activas, se consulta al servidor cada segundo
  const hayActivos = Object.keys(trabajos).length > 0
  useEffect(() => {
    if (modo !== 'real' || !hayActivos) return
    const reloj = window.setInterval(() => {
      listarTrabajos()
        .then(procesarTrabajos)
        .catch(() => {})
    }, 1000)
    return () => window.clearInterval(reloj)
  }, [modo, hayActivos, procesarTrabajos])

  const sel = clips.find((c) => c.id === selId) ?? null
  const guardado = sel ? base[sel.id] : undefined
  const sucio = !!sel && !!guardado && firma(sel) !== firma(guardado)
  const trabajoSel = sel ? trabajos[sel.id] : undefined
  const bloqueado = !!trabajoSel // el clip se está regenerando: no se edita ni se aprueba
  const activos = Object.values(trabajos)
  const videoSrc = modo === 'demo' ? videoLocal : sel?.videoUrl || null

  const conteo: Record<Filtro, number> = {
    todos: clips.length,
    pendiente: clips.filter((c) => c.estado === 'pendiente').length,
    aprobado: clips.filter((c) => c.estado === 'aprobado').length,
    descartado: clips.filter((c) => c.estado === 'descartado').length,
  }
  const revisados = conteo.aprobado + conteo.descartado
  const visibles = filtro === 'todos' ? clips : clips.filter((c) => c.estado === filtro)

  // Si el servidor conoce los cuadros por segundo reales del video, se usan
  useEffect(() => {
    if (sel?.fps) setFps(sel.fps)
  }, [sel?.id, sel?.fps])

  const actualizarClip = (cambios: Partial<Clip>) => {
    if (!sel) return
    setClips((prev) => prev.map((c) => (c.id === sel.id ? { ...c, ...cambios } : c)))
  }

  const actualizarTitulo = (cambios: Partial<TituloVideo>) => {
    if (!sel) return
    actualizarClip({ tituloVideo: { ...sel.tituloVideo, ...cambios } })
  }

  const irAlSiguientePendiente = (idActual: string) => {
    const i = clips.findIndex((c) => c.id === idActual)
    const orden = [...clips.slice(i + 1), ...clips.slice(0, Math.max(i, 0))]
    const siguiente = orden.find((c) => c.estado === 'pendiente' && !trabajos[c.id])
    if (siguiente) setSelId(siguiente.id)
  }

  // Manda el clip a regenerarse en segundo plano (con aprobar=true se aprueba solo al terminar bien)
  const lanzar = async (aprobar: boolean) => {
    if (!sel || modo !== 'real' || !sucio || bloqueado) return
    const id = sel.id
    setAviso(null)
    try {
      const t = await guardarClip(sel, aprobar)
      setTrabajos((prev) => ({ ...prev, [id]: t }))
      if (aprobar) irAlSiguientePendiente(id) // se sigue revisando mientras tanto
    } catch (e) {
      setAviso({ tipo: 'error', texto: e instanceof Error ? e.message : 'No se pudo guardar' })
    }
  }

  const guardar = async () => {
    await lanzar(false)
  }

  const cancelar = async () => {
    if (!sel || !trabajoSel || cancelando[sel.id]) return
    const id = sel.id
    setCancelando((prev) => ({ ...prev, [id]: true }))
    try {
      // Se reintenta unas veces por si el servidor todavía no había registrado el trabajo
      for (let i = 0; i < 4; i++) {
        const r = await cancelarTrabajo(id)
        if (r.cancelado) break
        await espera(250)
      }
    } catch {
      // si no se pudo avisar al servidor, el trabajo terminará por su cuenta
    }
    // El aviso final llega con la siguiente consulta de trabajos
  }

  const deshacer = () => {
    if (!sel || !guardado || bloqueado) return
    setClips((prev) => prev.map((c) => (c.id === sel.id ? guardado : c)))
    setAviso(null)
  }

  const decidir = async (estado: Estado) => {
    if (!sel || ocupado || bloqueado) return
    if (!sucio && sel.estado === estado) return

    // Aprobar con cambios sin guardar: se regenera y se aprueba en segundo plano
    if (estado === 'aprobado' && sucio && modo === 'real') {
      await lanzar(true)
      return
    }

    const id = sel.id
    setOcupado(true)
    setAviso(null)
    try {
      if (modo === 'real') await cambiarEstado(id, estado)
      setClips((prev) => prev.map((c) => (c.id === id ? { ...c, estado } : c)))
      setBase((prev) => (prev[id] ? { ...prev, [id]: { ...prev[id], estado } } : prev))
      if (estado !== 'pendiente') irAlSiguientePendiente(id)
    } catch (e) {
      setAviso({ tipo: 'error', texto: e instanceof Error ? e.message : 'No se pudo cambiar el estado' })
    } finally {
      setOcupado(false)
    }
  }

  const mover = (delta: number) => {
    if (visibles.length === 0) return
    const i = visibles.findIndex((c) => c.id === selId)
    setSelId(visibles[clamp(i + delta, 0, visibles.length - 1)].id)
  }

  // Atajos de teclado (siempre con la versión más reciente de las funciones)
  const accionesRef = useRef({ guardar, decidir, mover, cancelar })
  useEffect(() => {
    accionesRef.current = { guardar, decidir, mover, cancelar }
  })
  useEffect(() => {
    const alTeclear = (e: KeyboardEvent) => {
      const objetivo = e.target as HTMLElement
      const escribiendo =
        ['INPUT', 'TEXTAREA', 'SELECT'].includes(objetivo.tagName) || objetivo.isContentEditable

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault()
        void accionesRef.current.guardar()
        return
      }
      if (e.key === 'Escape') {
        void accionesRef.current.cancelar()
        return
      }
      if (escribiendo || e.repeat || e.ctrlKey || e.metaKey || e.altKey) return

      switch (e.key.toLowerCase()) {
        case 'a':
          void accionesRef.current.decidir('aprobado')
          break
        case 'd':
          void accionesRef.current.decidir('descartado')
          break
        case 'u':
          void accionesRef.current.decidir('pendiente')
          break
        case ']':
          accionesRef.current.mover(1)
          break
        case '[':
          accionesRef.current.mover(-1)
          break
      }
    }
    window.addEventListener('keydown', alTeclear)
    return () => window.removeEventListener('keydown', alTeclear)
  }, [])

  // Demostración con un video local
  const alElegirArchivo = (e: ChangeEvent<HTMLInputElement>) => {
    const archivo = e.target.files?.[0]
    if (!archivo) return
    if (videoLocal) URL.revokeObjectURL(videoLocal)
    setVideoLocal(URL.createObjectURL(archivo))
    e.target.value = ''
  }

  const alVideoListo = (duracion: number) => {
    if (modo !== 'demo') return
    setClips((prev) => {
      const seg = duracion / Math.max(prev.length, 1)
      return prev.map((c, i) => ({
        ...c,
        ventana: [0, duracion] as [number, number],
        inicio: i * seg + seg * 0.15,
        fin: i * seg + seg * 0.85,
      }))
    })
  }

  const estadoConexion =
    modo === 'real'
      ? { color: 'bg-ok', texto: 'Conectado' }
      : modo === 'demo'
        ? { color: 'bg-warn', texto: 'Modo demostración' }
        : modo === 'error'
          ? { color: 'bg-bad', texto: 'Sin conexión' }
          : { color: 'bg-muted', texto: 'Conectando…' }

  const BOTON_BORDE =
    'press inline-flex items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-sm hover:bg-raised disabled:cursor-not-allowed disabled:opacity-40'

  return (
    <div className="flex h-dvh flex-col">
      {/* Barra superior */}
      <header className="flex h-12 shrink-0 items-center gap-3 border-b border-line bg-panel px-4">
        <span className="text-sm font-semibold tracking-wide">Clipping IA</span>
        <span className="flex items-center gap-1.5 text-xs text-muted">
          <span className={`h-2 w-2 rounded-full ${estadoConexion.color}`} aria-hidden />
          {estadoConexion.texto}
        </span>

        <div className="ml-2 flex items-center gap-2 text-xs text-muted">
          <div
            role="progressbar"
            aria-label="Clips revisados"
            aria-valuemin={0}
            aria-valuemax={conteo.todos}
            aria-valuenow={revisados}
            className="h-1.5 w-28 overflow-hidden rounded-full bg-raised"
          >
            <div
              className="h-full bg-ok"
              style={{ width: `${conteo.todos ? (revisados / conteo.todos) * 100 : 0}%` }}
            />
          </div>
          <span className="tnum">
            {revisados} de {conteo.todos} revisados
          </span>
        </div>

        <div className="ml-auto flex items-center gap-2">
          <span
            role="status"
            aria-live="polite"
            className={`flex items-center gap-2 text-sm ${
              activos.length > 0 || aviso?.tipo === 'info'
                ? 'text-muted'
                : aviso?.tipo === 'error'
                  ? 'text-bad'
                  : 'text-ok'
            }`}
          >
            {activos.length > 0 ? (
              <>
                <Spinner />
                {activos.length === 1 ? '1 clip regenerándose' : `${activos.length} clips regenerándose`}
              </>
            ) : (
              aviso?.texto
            )}
          </span>

          {trabajoSel && (
            <button
              type="button"
              onClick={() => void cancelar()}
              disabled={!!cancelando[sel?.id ?? '']}
              className={`${BOTON_BORDE} text-bad`}
            >
              <X size={15} aria-hidden />
              {cancelando[sel?.id ?? ''] ? 'Cancelando…' : 'Cancelar'}
              <Atajo>Esc</Atajo>
            </button>
          )}

          {sucio && !bloqueado && (
            <>
              {sel?.estado === 'aprobado' && (
                <span className="text-xs text-warn">Lo aprobado es la versión guardada</span>
              )}
              <button type="button" onClick={deshacer} className={BOTON_BORDE}>
                <Undo2 size={15} aria-hidden />
                Deshacer cambios
              </button>
              <button
                type="button"
                onClick={() => void guardar()}
                disabled={modo !== 'real'}
                title="Ctrl + S"
                className={`${BOTON_BORDE} border-accent text-accent`}
              >
                <Save size={15} aria-hidden />
                Guardar y regenerar
                <Atajo>Ctrl S</Atajo>
              </button>
            </>
          )}

          <span className="mx-1 h-5 w-px bg-line" aria-hidden />

          {sel && (sel.estado === 'pendiente' || sucio) ? (
            <>
              <button
                type="button"
                onClick={() => void decidir('descartado')}
                disabled={ocupado || bloqueado}
                className={`${BOTON_BORDE} text-bad`}
              >
                <X size={15} aria-hidden />
                Descartar
                <Atajo>D</Atajo>
              </button>
              <button
                type="button"
                onClick={() => void decidir('aprobado')}
                disabled={ocupado || bloqueado}
                className="press inline-flex items-center gap-1.5 rounded-md bg-ok px-3.5 py-1.5 text-sm font-medium text-[#06140d] disabled:cursor-not-allowed disabled:opacity-40"
              >
                <Check size={15} aria-hidden />
                {sucio && modo === 'real' ? 'Guardar y aprobar' : 'Aprobar'}
                <Atajo>A</Atajo>
              </button>
            </>
          ) : (
            sel && (
              <button
                type="button"
                onClick={() => void decidir('pendiente')}
                disabled={ocupado || bloqueado}
                className={BOTON_BORDE}
              >
                <Undo2 size={15} aria-hidden />
                Volver a pendiente
                <Atajo>U</Atajo>
              </button>
            )
          )}
        </div>
      </header>

      <div
        className="grid min-h-0 flex-1"
        style={{ gridTemplateColumns: `${izq.ancho}px 4px minmax(0,1fr) 4px ${der.ancho}px` }}
      >
        {/* Lista de clips */}
        <aside className="flex min-w-0 flex-col overflow-y-auto bg-panel p-3">
          <div className="mb-3 flex items-center justify-between gap-2 px-1">
            <h2 className="text-xs font-medium uppercase tracking-wider text-muted">
              {clips.length} {clips.length === 1 ? 'clip' : 'clips'}
            </h2>
            {modo === 'demo' ? (
              <>
                <button
                  type="button"
                  onClick={() => archivoRef.current?.click()}
                  className="press inline-flex items-center gap-1.5 rounded-md border border-line px-2.5 py-1.5 text-xs hover:bg-raised"
                >
                  <Upload size={14} aria-hidden />
                  Cargar video
                </button>
                <input ref={archivoRef} type="file" accept="video/*" className="hidden" onChange={alElegirArchivo} />
              </>
            ) : (
              <button
                type="button"
                onClick={cargar}
                aria-label="Volver a cargar los clips"
                className="press inline-flex items-center gap-1.5 rounded-md border border-line px-2.5 py-1.5 text-xs hover:bg-raised"
              >
                <RefreshCw size={14} aria-hidden />
                Recargar
              </button>
            )}
          </div>

          {clips.length > 0 && (
            <div role="group" aria-label="Filtrar clips" className="mb-3 grid grid-cols-4 gap-1 rounded-lg bg-bg p-1 text-xs">
              {FILTROS.map((f) => (
                <button
                  key={f}
                  type="button"
                  aria-pressed={filtro === f}
                  title={NOMBRE[f]}
                  onClick={() => setFiltro(f)}
                  className={`press rounded-md px-1 py-1.5 ${
                    filtro === f ? 'bg-raised text-white' : 'text-muted hover:text-white'
                  }`}
                >
                  {ETIQUETA[f]} <span className="tnum">{conteo[f]}</span>
                </button>
              ))}
            </div>
          )}

          {modo === 'error' && (
            <div className="rounded-lg border border-line p-3 text-sm">
              <p className="text-bad">No pude conectar con el servidor.</p>
              <p className="mt-1 text-xs text-muted">{errorCarga}</p>
              <p className="mt-2 text-xs text-muted">
                Arranca el backend con <code>uvicorn servidor:app --reload --port 8000</code>.
              </p>
              <button
                type="button"
                onClick={() => aplicar(clipsDemo, 'demo')}
                className="press mt-3 rounded-md border border-line px-3 py-1.5 text-xs hover:bg-raised"
              >
                Ver demostración
              </button>
            </div>
          )}

          {modo === 'real' && clips.length === 0 && (
            <p className="px-1 text-sm text-muted">
              No hay clips en la carpeta <code>salida</code>. Genera algunos con <code>main.py</code> y pulsa
              Recargar.
            </p>
          )}

          {clips.length > 0 && visibles.length === 0 && (
            <p className="px-1 text-sm text-muted">No hay clips con este filtro.</p>
          )}

          <ul className="flex flex-col gap-2">
            {visibles.map((c) => {
              const modificado = base[c.id] ? firma(c) !== firma(base[c.id]) : false
              const trabajo = trabajos[c.id]
              return (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => setSelId(c.id)}
                    aria-pressed={c.id === selId}
                    className={`press w-full min-w-0 rounded-lg border p-3 text-left ${
                      c.id === selId ? 'border-accent bg-raised' : 'border-line hover:bg-raised'
                    } ${c.estado === 'descartado' ? 'opacity-60' : ''}`}
                  >
                    <span className="line-clamp-2 wrap-break-word text-sm font-medium">{c.titulo}</span>
                    <span className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
                      <span className="rounded bg-bg px-1.5 py-0.5">{c.tipo}</span>
                      <span className="tnum">
                        {formatTime(c.inicio)}–{formatTime(c.fin)}
                      </span>
                      {trabajo && (
                        <span className="inline-flex items-center gap-1.5 text-accent">
                          <Spinner />
                          {trabajo.estado === 'en_cola' ? 'En cola' : 'Regenerando'}
                          {trabajo.aprobar && ' y aprobando'}
                        </span>
                      )}
                      {!trabajo && c.estado === 'aprobado' && (
                        <span className="inline-flex items-center gap-1 text-ok">
                          <Check size={12} aria-hidden />
                          Aprobado
                        </span>
                      )}
                      {!trabajo && c.estado === 'descartado' && (
                        <span className="inline-flex items-center gap-1 text-bad">
                          <X size={12} aria-hidden />
                          Descartado
                        </span>
                      )}
                      {modificado && !trabajo && (
                        <span
                          className="h-1.5 w-1.5 rounded-full bg-warn"
                          title="Cambios sin guardar"
                          aria-label="Cambios sin guardar"
                        />
                      )}
                      <span className="tnum ml-auto">{Math.round(c.fin - c.inicio)} s</span>
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>

          <p className="mt-auto pt-4 text-xs leading-relaxed text-muted">
            <Atajo>A</Atajo> aprobar · <Atajo>D</Atajo> descartar · <Atajo>U</Atajo> pendiente ·{' '}
            <Atajo>[</Atajo> <Atajo>]</Atajo> anterior / siguiente · <Atajo>Ctrl S</Atajo> guardar ·{' '}
            <Atajo>Esc</Atajo> cancelar
          </p>
        </aside>

        <Divisor etiqueta="Ancho de la lista de clips" panel={izq} />

        {/* Vista previa y línea de tiempo */}
        <main className="flex min-h-0 min-w-0 flex-col">
          {trabajoSel && (
            <div
              role="status"
              className="flex shrink-0 items-center gap-2 border-b border-line bg-raised px-4 py-2 text-sm"
            >
              <span className="text-accent">
                <Spinner />
              </span>
              <span>
                {trabajoSel.estado === 'en_cola'
                  ? 'En cola: este clip se regenerará cuando termine el anterior.'
                  : 'Regenerando este clip…'}
                {trabajoSel.aprobar && ' Se aprobará al terminar.'}
              </span>
              <span className="text-muted">Mientras tanto puedes revisar otros clips.</span>
            </div>
          )}

          {/* inert: el clip que se regenera no se puede tocar */}
          <div inert={bloqueado} className={`flex min-h-0 flex-1 flex-col ${bloqueado ? 'opacity-60' : ''}`}>
            <div className="flex min-h-0 flex-1 items-center justify-center p-4">
              {sel ? (
                <PreviewStage
                  titulo={sel.tituloVideo}
                  onChange={actualizarTitulo}
                  zonasSeguras={zonasSeguras}
                  videoRef={videoRef}
                  videoSrc={videoSrc}
                  onVideoListo={alVideoListo}
                />
              ) : (
                <p className="text-sm text-muted">{modo === 'cargando' ? 'Cargando clips…' : 'Selecciona un clip'}</p>
              )}
            </div>
            {sel && (
              <Timeline
                videoRef={videoRef}
                videoSrc={videoSrc}
                clipId={sel.id}
                inicio={sel.inicio}
                fin={sel.fin}
                ventana={sel.ventana}
                fps={fps}
                onFps={setFps}
                onCambio={actualizarClip}
              />
            )}
          </div>
        </main>

        <Divisor etiqueta="Ancho del panel de ajustes" panel={der} />

        {/* Ajustes */}
        <section
          inert={bloqueado}
          className={`min-w-0 overflow-y-auto bg-panel p-4 ${bloqueado ? 'opacity-60' : ''}`}
        >
          {sel && (
            <>
              <h2 className="text-xs font-medium uppercase tracking-wider text-muted">Por qué se eligió</h2>
              <p className="mb-5 mt-1.5 text-sm leading-relaxed">{sel.razon || 'Sin explicación guardada.'}</p>
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
    </div>
  )
}