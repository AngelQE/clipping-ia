import { memo, useCallback, useEffect, useRef, useState } from 'react'
import type { KeyboardEvent, PointerEvent, RefObject } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Pause,
  Play,
  SkipBack,
  SkipForward,
  ZoomIn,
  ZoomOut,
} from 'lucide-react'
import { clamp } from '../lib/num'
import { formatTime } from '../lib/time'

const DURACION_MINIMA = 1 // segundos
const FPS_OPCIONES = [24, 25, 30, 50, 60]
const PASOS_REGLA = [0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 1800, 3600]
const BOTON =
  'press inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-line hover:bg-raised'

type Lado = 'inicio' | 'fin'

interface Props {
  videoRef: RefObject<HTMLVideoElement | null>
  videoSrc: string | null
  clipId: string
  inicio: number
  fin: number
  ventana: [number, number]
  fps: number
  onFps: (fps: number) => void
  onCambio: (cambios: { inicio?: number; fin?: number }) => void
}

const aMilis = (n: number) => Math.round(n * 1000) / 1000

/** Saca fotogramas del video en el navegador. En el producto final los generará el backend con ffmpeg. */
async function generarMiniaturas(
  url: string,
  tiempos: number[],
  cancelado: () => boolean,
): Promise<string[]> {
  const v = document.createElement('video')
  v.muted = true
  v.preload = 'auto'
  v.src = url
  await new Promise<void>((ok, fallo) => {
    v.addEventListener('loadeddata', () => ok(), { once: true })
    v.addEventListener('error', () => fallo(new Error('No se pudo leer el video')), { once: true })
  })

  const ancho = 160
  const canvas = document.createElement('canvas')
  canvas.width = ancho
  canvas.height = Math.max(1, Math.round((ancho * v.videoHeight) / Math.max(v.videoWidth, 1)))
  const ctx = canvas.getContext('2d')
  const salida: string[] = []
  if (!ctx) return salida

  for (const t of tiempos) {
    if (cancelado()) break
    await new Promise<void>((ok) => {
      const plazo = window.setTimeout(ok, 2500) // por si el navegador no avisa
      v.addEventListener(
        'seeked',
        () => {
          window.clearTimeout(plazo)
          ok()
        },
        { once: true },
      )
      v.currentTime = t
    })
    ctx.drawImage(v, 0, 0, canvas.width, canvas.height)
    salida.push(canvas.toDataURL('image/jpeg', 0.6))
  }

  v.removeAttribute('src')
  v.load()
  return salida
}

const Regla = memo(function Regla({
  v0,
  v1,
  px,
  fps,
}: {
  v0: number
  v1: number
  px: number
  fps: number
}) {
  // El paso más pequeño que deje las marcas a 90 px o más (y sin pasarse de unas 1500 marcas)
  const paso =
    PASOS_REGLA.find((p) => p * px >= 90 && (v1 - v0) / p <= 1500) ?? PASOS_REGLA[PASOS_REGLA.length - 1]
  const marcas: number[] = []
  for (let k = Math.ceil(v0 / paso); k * paso <= v1; k++) marcas.push(k * paso)

  // Con mucho zoom se dibuja una rayita por cada cuadro
  const pxCuadro = px / fps
  const mostrarCuadros = pxCuadro >= 6
  const desfase = (Math.ceil(v0 * fps) / fps - v0) * px

  return (
    <div
      className="relative h-6 border-b border-line"
      style={
        mostrarCuadros
          ? {
              backgroundImage: `repeating-linear-gradient(to right, rgba(255,255,255,0.16) 0 1px, transparent 1px ${pxCuadro}px)`,
              backgroundSize: '100% 6px',
              backgroundRepeat: 'repeat-x',
              backgroundPosition: `${desfase}px 100%`,
            }
          : undefined
      }
    >
      {marcas.map((t) => (
        <div
          key={t}
          className="tnum absolute top-0 h-full border-l border-muted/40 pl-1 text-[10px] leading-6 text-muted"
          style={{ left: (t - v0) * px }}
        >
          {formatTime(t, paso < 1)}
        </div>
      ))}
    </div>
  )
})

const Miniaturas = memo(function Miniaturas({
  imagenes,
  anchoTotal,
}: {
  imagenes: string[]
  anchoTotal: number
}) {
  if (imagenes.length === 0) return <div className="h-16 bg-[#10151b]" />
  const ancho = anchoTotal / imagenes.length
  return (
    <div className="flex h-16 bg-[#10151b]">
      {imagenes.map((src, i) => (
        <img
          key={i}
          src={src}
          alt=""
          draggable={false}
          className="h-full shrink-0 object-cover"
          style={{ width: ancho }}
        />
      ))}
    </div>
  )
})

// Se confirma al salir del campo o con Enter, para poder borrar y escribir con calma
function CampoTiempo({
  etiqueta,
  valor,
  onConfirmar,
  onPaso,
}: {
  etiqueta: string
  valor: number
  onConfirmar: (n: number) => void
  onPaso: (direccion: -1 | 1) => void
}) {
  const aplicar = (input: HTMLInputElement) => {
    const n = input.valueAsNumber
    if (Number.isNaN(n)) {
      input.value = valor.toFixed(3)
      return
    }
    onConfirmar(n)
  }

  return (
    <div className="flex flex-col gap-1.5 text-sm text-muted">
      {etiqueta}
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          aria-label={`${etiqueta}: un cuadro antes`}
          onClick={() => onPaso(-1)}
          className={BOTON}
        >
          <ChevronLeft size={16} aria-hidden />
        </button>
        <input
          key={valor.toFixed(3)}
          type="number"
          inputMode="decimal"
          step={0.001}
          defaultValue={valor.toFixed(3)}
          aria-label={`${etiqueta} en segundos`}
          onBlur={(e) => aplicar(e.currentTarget)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') aplicar(e.currentTarget)
          }}
          className="tnum min-w-0 flex-1 rounded-md border border-line bg-raised px-2 py-1.5 text-right text-white"
        />
        <button
          type="button"
          aria-label={`${etiqueta}: un cuadro después`}
          onClick={() => onPaso(1)}
          className={BOTON}
        >
          <ChevronRight size={16} aria-hidden />
        </button>
        <span className="w-3 text-xs">s</span>
      </div>
    </div>
  )
}

function LineaDeTiempo({
  videoRef,
  videoSrc,
  clipId,
  inicio,
  fin,
  ventana,
  fps,
  onFps,
  onCambio,
}: Props & { videoSrc: string }) {
  const [v0, v1] = ventana
  const duracionVentana = Math.max(v1 - v0, 0.001)

  const seccionRef = useRef<HTMLElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const contenidoRef = useRef<HTMLDivElement>(null)
  const cabezalRef = useRef<HTMLDivElement>(null)
  const lecturaRef = useRef<HTMLSpanElement>(null)
  const arrastrando = useRef(false)
  const buscando = useRef(false)
  const arrastreManija = useRef<{ lado: Lado; desfase: number } | null>(null)
  const seekPendiente = useRef<number | null>(null)
  const rafSeek = useRef(0)

  const [anchoVisible, setAnchoVisible] = useState(800)
  const [zoomRel, setZoomRel] = useState(0) // 0 = todo a la vista, 1 = máximo zoom
  const [miniaturas, setMiniaturas] = useState<string[]>([])
  const [reproduciendo, setReproduciendo] = useState(false)
  const [limitar, setLimitar] = useState(true)
  const [repetir, setRepetir] = useState(false)

  const pxMin = Math.max(anchoVisible / duracionVentana, 0.2)
  const pxMax = Math.max(pxMin * 1.01, fps * 24) // al máximo, un cuadro mide 24 px
  const px = pxMin * Math.pow(pxMax / pxMin, zoomRel)
  const anchoTotal = duracionVentana * px
  const x0 = (inicio - v0) * px
  const x1 = (fin - v0) * px

  // Copia de lo último, para el código que corre fuera de React (reproducción, rueda del ratón)
  const vivo = useRef({ inicio, fin, v0, v1, px, fps, limitar, repetir, zoomRel, pxMin, pxMax })
  useEffect(() => {
    vivo.current = { inicio, fin, v0, v1, px, fps, limitar, repetir, zoomRel, pxMin, pxMax }
  })

  // El cabezal y la lectura se mueven directo en el DOM: así no se redibuja todo en cada cuadro
  const pintar = useCallback((t: number) => {
    const { v0, px, fps } = vivo.current
    if (cabezalRef.current) cabezalRef.current.style.transform = `translateX(${(t - v0) * px}px)`
    if (lecturaRef.current) {
      lecturaRef.current.textContent = `${formatTime(t, true)} · cuadro ${Math.floor(t * fps + 1e-6)}`
    }
  }, [])

  // Un salto por cuadro de pantalla como máximo; se apunta al centro del cuadro
  // para que el navegador no muestre el anterior
  const pedirSeek = useCallback(
    (t: number) => {
      seekPendiente.current = t
      if (rafSeek.current) return
      rafSeek.current = requestAnimationFrame(() => {
        rafSeek.current = 0
        const v = videoRef.current
        const { fps, v1 } = vivo.current
        if (v && seekPendiente.current !== null) {
          v.currentTime = Math.min(seekPendiente.current + 0.5 / fps, v1)
          seekPendiente.current = null
        }
      })
    },
    [videoRef],
  )

  const buscar = useCallback(
    (t: number) => {
      const { v0, v1 } = vivo.current
      const tt = clamp(t, v0, v1)
      pintar(tt)
      pedirSeek(tt)
    },
    [pintar, pedirSeek],
  )

  // Ancho visible de la pista
  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const obs = new ResizeObserver(() => setAnchoVisible(el.clientWidth))
    obs.observe(el)
    setAnchoVisible(el.clientWidth)
    return () => obs.disconnect()
  }, [])

  // Miniaturas de la ventana
  useEffect(() => {
    let cancelado = false
    setMiniaturas([])
    const n = Math.round(clamp(duracionVentana / 1.5, 8, 60))
    const tiempos = Array.from({ length: n }, (_, i) => v0 + ((i + 0.5) * duracionVentana) / n)
    generarMiniaturas(videoSrc, tiempos, () => cancelado)
      .then((imgs) => {
        if (!cancelado) setMiniaturas(imgs)
      })
      .catch(() => {})
    return () => {
      cancelado = true
    }
  }, [videoSrc, v0, duracionVentana])

  // Bucle de reproducción: mueve el cabezal, respeta el final del clip y lo sigue si sale de la vista
  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    let raf = 0

    const bucle = () => {
      const t = v.currentTime
      pintar(t)
      const { inicio, fin, limitar, repetir, v0, px } = vivo.current
      if (limitar && t >= fin) {
        if (repetir) v.currentTime = inicio
        else {
          v.pause()
          v.currentTime = fin
        }
      }
      const sc = scrollRef.current
      if (sc && !arrastrando.current) {
        const x = (t - v0) * px
        if (x < sc.scrollLeft || x > sc.scrollLeft + sc.clientWidth - 40) {
          sc.scrollLeft = x - sc.clientWidth * 0.3
        }
      }
      raf = requestAnimationFrame(bucle)
    }
    const alPlay = () => {
      setReproduciendo(true)
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(bucle)
    }
    const alPausa = () => {
      setReproduciendo(false)
      cancelAnimationFrame(raf)
      pintar(v.currentTime)
    }
    const alSaltar = () => pintar(v.currentTime)

    v.addEventListener('play', alPlay)
    v.addEventListener('pause', alPausa)
    v.addEventListener('ended', alPausa)
    v.addEventListener('seeked', alSaltar)
    pintar(v.currentTime)
    return () => {
      v.removeEventListener('play', alPlay)
      v.removeEventListener('pause', alPausa)
      v.removeEventListener('ended', alPausa)
      v.removeEventListener('seeked', alSaltar)
      cancelAnimationFrame(raf)
    }
  }, [videoRef, videoSrc, pintar])

  // Al cambiar el zoom o el fps, recolocar el cabezal
  useEffect(() => {
    const v = videoRef.current
    if (v) pintar(v.currentTime)
  }, [px, v0, fps, pintar, videoRef])

  // Al cambiar de clip (o cuando cambia su ventana), ir al inicio del clip
  useEffect(() => {
    const v = videoRef.current
    const { inicio, fps, v0, px } = vivo.current
    if (v) {
      v.pause()
      v.currentTime = inicio + 0.5 / fps
    }
    scrollRef.current?.scrollTo({ left: Math.max(0, (inicio - v0) * px - 60) })
  }, [clipId, v0, v1, videoRef])

  // Ctrl + rueda (o pellizco en el trackpad) = zoom, manteniendo fijo el instante bajo el puntero
  useEffect(() => {
    const sc = scrollRef.current
    if (!sc) return
    const alRueda = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return
      e.preventDefault()
      const { v0, px, pxMin, pxMax, zoomRel } = vivo.current
      const xp = e.clientX - sc.getBoundingClientRect().left
      const tBajo = v0 + (sc.scrollLeft + xp) / px
      const nuevo = clamp(zoomRel - e.deltaY * 0.003, 0, 1)
      const nuevoPx = pxMin * Math.pow(pxMax / pxMin, nuevo)
      setZoomRel(nuevo)
      requestAnimationFrame(() => {
        sc.scrollLeft = (tBajo - v0) * nuevoPx - xp
      })
    }
    sc.addEventListener('wheel', alRueda, { passive: false })
    return () => sc.removeEventListener('wheel', alRueda)
  }, [])

  const cambiarZoom = (delta: number) => {
    const sc = scrollRef.current
    const nuevo = clamp(zoomRel + delta, 0, 1)
    if (!sc) {
      setZoomRel(nuevo)
      return
    }
    const centro = sc.clientWidth / 2
    const tCentro = v0 + (sc.scrollLeft + centro) / px
    const nuevoPx = pxMin * Math.pow(pxMax / pxMin, nuevo)
    setZoomRel(nuevo)
    requestAnimationFrame(() => {
      sc.scrollLeft = (tCentro - v0) * nuevoPx - centro
    })
  }

  const tiempoDesdePuntero = (clientX: number) => {
    const r = contenidoRef.current!.getBoundingClientRect()
    return v0 + (clientX - r.left) / px
  }

  // Mueve una manija: se ajusta a cuadros (salvo que lo escribas a mano), sin cruzarse con la otra
  const aplicarManija = (lado: Lado, t: number, ajustar = true) => {
    const f = 1 / fps
    const valor = aMilis(ajustar ? Math.round(t / f) * f : t)
    if (lado === 'inicio') {
      const nuevo = clamp(valor, v0, fin - DURACION_MINIMA)
      onCambio({ inicio: nuevo })
      buscar(nuevo)
    } else {
      const nuevo = clamp(valor, inicio + DURACION_MINIMA, v1)
      onCambio({ fin: nuevo })
      buscar(nuevo)
    }
  }

  const alPresionarManija = (lado: Lado, e: PointerEvent<HTMLDivElement>) => {
    e.stopPropagation()
    e.currentTarget.setPointerCapture(e.pointerId)
    videoRef.current?.pause()
    arrastrando.current = true
    arrastreManija.current = {
      lado,
      desfase: tiempoDesdePuntero(e.clientX) - (lado === 'inicio' ? inicio : fin),
    }
  }

  const alMoverManija = (e: PointerEvent<HTMLDivElement>) => {
    const a = arrastreManija.current
    if (!a) return
    aplicarManija(a.lado, tiempoDesdePuntero(e.clientX) - a.desfase)
  }

  const alSoltarManija = () => {
    arrastreManija.current = null
    arrastrando.current = false
  }

  const alTeclearManija = (lado: Lado, e: KeyboardEvent<HTMLDivElement>) => {
    const valor = lado === 'inicio' ? inicio : fin
    const paso = e.shiftKey ? 1 : 1 / fps
    if (e.key === 'ArrowLeft') {
      e.preventDefault()
      aplicarManija(lado, valor - paso)
    } else if (e.key === 'ArrowRight') {
      e.preventDefault()
      aplicarManija(lado, valor + paso)
    }
  }

  // Buscar con el puntero: en la regla con cualquier dedo o ratón; en las miniaturas solo con ratón
  // (con el dedo, las miniaturas se desplazan)
  const alPresionarPista = (e: PointerEvent<HTMLDivElement>, enRegla: boolean) => {
    if (e.button !== 0) return
    if (e.pointerType !== 'mouse' && !enRegla) return
    e.currentTarget.setPointerCapture(e.pointerId)
    seccionRef.current?.focus({ preventScroll: true })
    buscando.current = true
    arrastrando.current = true
    videoRef.current?.pause()
    buscar(tiempoDesdePuntero(e.clientX))
  }

  const alMoverPista = (e: PointerEvent<HTMLDivElement>) => {
    if (buscando.current) buscar(tiempoDesdePuntero(e.clientX))
  }

  const alSoltarPista = () => {
    buscando.current = false
    arrastrando.current = false
  }

  const alternar = () => {
    const v = videoRef.current
    if (!v) return
    if (!v.paused) {
      v.pause()
      return
    }
    const { inicio: i, fin: f, limitar: l } = vivo.current
    if (l && (v.currentTime < i - 0.05 || v.currentTime >= f - 0.02)) v.currentTime = i
    v.play().catch(() => {})
  }

  const pasarFotograma = (n: number) => {
    const v = videoRef.current
    if (!v) return
    v.pause()
    const f = 1 / fps
    const actual = Math.floor(v.currentTime / f + 1e-6)
    buscar((actual + n) * f)
  }

  const alTeclear = (e: KeyboardEvent<HTMLElement>) => {
    const objetivo = e.target as HTMLElement
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(objetivo.tagName)) return
    if (e.key === ',') pasarFotograma(-1)
    else if (e.key === '.') pasarFotograma(1)
    else if (e.key === ' ' && objetivo.tagName !== 'BUTTON') {
      e.preventDefault()
      alternar()
    }
  }

  const manija = (lado: Lado) => {
    const valor = lado === 'inicio' ? inicio : fin
    const x = (valor - v0) * px

    return (
      <div
        role="slider"
        tabIndex={0}
        aria-label={lado === 'inicio' ? 'Inicio del clip' : 'Final del clip'}
        aria-orientation="horizontal"
        aria-valuemin={lado === 'inicio' ? v0 : inicio + DURACION_MINIMA}
        aria-valuemax={lado === 'inicio' ? fin - DURACION_MINIMA : v1}
        aria-valuenow={valor}
        aria-valuetext={formatTime(valor, true)}
        onPointerDown={(e) => alPresionarManija(lado, e)}
        onPointerMove={alMoverManija}
        onPointerUp={alSoltarManija}
        onPointerCancel={alSoltarManija}
        onKeyDown={(e) => alTeclearManija(lado, e)}
        className="pointer-events-auto absolute inset-y-0 z-20 flex w-7 cursor-ew-resize touch-none items-stretch"
        style={{ left: lado === 'inicio' ? x - 8 : x - 20 }}
      >
        <div
          className={`flex w-2.5 items-center justify-center bg-accent ${
            lado === 'inicio' ? 'ml-2 rounded-l-md' : 'ml-2.5 rounded-r-md'
          }`}
        >
          <span className="h-5 w-px bg-black/50" />
        </div>
      </div>
    )
  }

  const opcionesFps = FPS_OPCIONES.includes(fps)
    ? FPS_OPCIONES
    : [...FPS_OPCIONES, fps].sort((a, b) => a - b)

  return (
    <section
      ref={seccionRef}
      tabIndex={-1}
      onKeyDown={alTeclear}
      className="shrink-0 border-t border-line bg-panel p-3 outline-none"
    >
      {/* Controles */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <button type="button" aria-label="Ir al inicio del clip" onClick={() => buscar(inicio)} className={BOTON}>
          <SkipBack size={16} aria-hidden />
        </button>
        <button type="button" aria-label="Un cuadro atrás (coma)" onClick={() => pasarFotograma(-1)} className={BOTON}>
          <ChevronLeft size={16} aria-hidden />
        </button>
        <button
          type="button"
          aria-label={reproduciendo ? 'Pausar' : 'Reproducir'}
          onClick={alternar}
          className={`${BOTON} w-11 border-accent bg-accent/15`}
        >
          {reproduciendo ? <Pause size={18} aria-hidden /> : <Play size={18} aria-hidden />}
        </button>
        <button type="button" aria-label="Un cuadro adelante (punto)" onClick={() => pasarFotograma(1)} className={BOTON}>
          <ChevronRight size={16} aria-hidden />
        </button>
        <button type="button" aria-label="Ir al final del clip" onClick={() => buscar(fin)} className={BOTON}>
          <SkipForward size={16} aria-hidden />
        </button>

        <span ref={lecturaRef} className="tnum ml-1 text-sm">
          00:00.000 · cuadro 0
        </span>

        <label className="ml-2 flex items-center gap-1.5 text-sm text-muted">
          <input type="checkbox" checked={limitar} onChange={(e) => setLimitar(e.target.checked)} />
          Solo el clip
        </label>
        <label className="flex items-center gap-1.5 text-sm text-muted">
          <input type="checkbox" checked={repetir} onChange={(e) => setRepetir(e.target.checked)} />
          Repetir
        </label>

        <div className="ml-auto flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-sm text-muted">
            fps
            <select
              value={fps}
              onChange={(e) => onFps(Number(e.target.value))}
              className="rounded-md border border-line bg-raised px-2 py-1.5 text-white"
            >
              {opcionesFps.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </label>
          <button type="button" aria-label="Alejar" onClick={() => cambiarZoom(-0.15)} className={BOTON}>
            <ZoomOut size={16} aria-hidden />
          </button>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={zoomRel}
            aria-label="Zoom de la línea de tiempo"
            onChange={(e) => cambiarZoom(Number(e.target.value) - zoomRel)}
            className="w-24 accent-accent"
          />
          <button type="button" aria-label="Acercar" onClick={() => cambiarZoom(0.15)} className={BOTON}>
            <ZoomIn size={16} aria-hidden />
          </button>
          <button type="button" aria-label="Ver toda la ventana" onClick={() => cambiarZoom(-1)} className={BOTON}>
            <Maximize2 size={16} aria-hidden />
          </button>
        </div>
      </div>

      {/* Pista */}
      <div ref={scrollRef} className="overflow-x-auto rounded-lg border border-line bg-bg">
        <div
          ref={contenidoRef}
          className="relative select-none"
          style={{ width: anchoTotal }}
          onPointerMove={alMoverPista}
          onPointerUp={alSoltarPista}
          onPointerCancel={alSoltarPista}
        >
          <div className="touch-none" onPointerDown={(e) => alPresionarPista(e, true)}>
            <Regla v0={v0} v1={v1} px={px} fps={fps} />
          </div>
          <div onPointerDown={(e) => alPresionarPista(e, false)}>
            <Miniaturas imagenes={miniaturas} anchoTotal={anchoTotal} />
          </div>

          {/* Selección: lo de afuera se oscurece */}
          <div className="pointer-events-none absolute inset-x-0 bottom-0 top-6">
            <div className="absolute inset-y-0 left-0 bg-black/60" style={{ width: Math.max(x0, 0) }} />
            <div
              className="absolute inset-y-0 bg-black/60"
              style={{ left: x1, width: Math.max(anchoTotal - x1, 0) }}
            />
            <div className="absolute inset-y-0 border-y-2 border-accent" style={{ left: x0, width: x1 - x0 }} />
            {manija('inicio')}
            {manija('fin')}
          </div>

          {/* Cabezal */}
          <div ref={cabezalRef} className="pointer-events-none absolute inset-y-0 left-0 z-30 w-px bg-white">
            <div className="absolute -left-1.25 -top-0.5 h-2.5 w-2.75 rounded-sm bg-white" />
          </div>
        </div>
      </div>

      {/* Tiempos exactos */}
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <CampoTiempo
          etiqueta="Inicio"
          valor={inicio}
          onConfirmar={(n) => aplicarManija('inicio', n, false)}
          onPaso={(d) => aplicarManija('inicio', inicio + d / fps)}
        />
        <CampoTiempo
          etiqueta="Final"
          valor={fin}
          onConfirmar={(n) => aplicarManija('fin', n, false)}
          onPaso={(d) => aplicarManija('fin', fin + d / fps)}
        />
        <CampoTiempo
          etiqueta="Duración"
          valor={fin - inicio}
          onConfirmar={(n) => aplicarManija('fin', inicio + n, false)}
          onPaso={(d) => aplicarManija('fin', fin + d / fps)}
        />
      </div>

      <p className="mt-3 text-xs leading-relaxed text-muted">
        Arrastra las manijas, o enfócalas con Tab y usa las flechas (Mayús = 1 segundo). Coma y punto avanzan un
        cuadro; la barra espaciadora reproduce. Ctrl + rueda hace zoom. Arrastra sobre la regla para recorrer el
        video.
      </p>
    </section>
  )
}

export default function Timeline(props: Props) {
  if (!props.videoSrc) {
    return (
      <div className="shrink-0 border-t border-line bg-panel p-4 text-sm text-muted">
        Carga un video de prueba para usar la línea de tiempo.
      </div>
    )
  }
  return <LineaDeTiempo {...props} videoSrc={props.videoSrc} />
}