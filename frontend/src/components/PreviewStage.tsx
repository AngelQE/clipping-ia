import { useRef, useState } from 'react'
import type { KeyboardEvent, PointerEvent, RefObject } from 'react'
import { clamp, redondear1 } from '../lib/num'
import type { TituloVideo } from '../types'

interface Props {
  titulo: TituloVideo
  onChange: (cambios: Partial<TituloVideo>) => void
  zonasSeguras: boolean
  videoRef: RefObject<HTMLVideoElement | null>
  videoSrc: string | null
  onVideoListo: (duracion: number) => void
}

const ANCHO_REF = 1080 // el ancho del video final
const GROSOR_BORDE = 6 // píxeles de contorno, en referencia 1080

const movimientos: Record<string, [number, number]> = {
  ArrowLeft: [-1, 0],
  ArrowRight: [1, 0],
  ArrowUp: [0, -1],
  ArrowDown: [0, 1],
}

export default function PreviewStage({
  titulo,
  onChange,
  zonasSeguras,
  videoRef,
  videoSrc,
  onVideoListo,
}: Props) {
  const escenaRef = useRef<HTMLDivElement>(null)
  const desfase = useRef({ x: 0, y: 0 })
  const [arrastrando, setArrastrando] = useState(false)
  const [guiaCentro, setGuiaCentro] = useState(false)

  const aPorcentaje = (clientX: number, clientY: number) => {
    const r = escenaRef.current!.getBoundingClientRect()
    return {
      x: ((clientX - r.left) / r.width) * 100,
      y: ((clientY - r.top) / r.height) * 100,
    }
  }

  const alPresionar = (e: PointerEvent<HTMLDivElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId)
    const p = aPorcentaje(e.clientX, e.clientY)
    desfase.current = { x: p.x - titulo.x, y: p.y - titulo.y }
    setArrastrando(true)
  }

  const alMover = (e: PointerEvent<HTMLDivElement>) => {
    if (!arrastrando) return
    const p = aPorcentaje(e.clientX, e.clientY)
    let x = clamp(p.x - desfase.current.x, 0, 100)
    const y = clamp(p.y - desfase.current.y, 0, 100)
    const centrado = Math.abs(x - 50) < 1.5 // imán al centro
    if (centrado) x = 50
    setGuiaCentro(centrado)
    onChange({ x: redondear1(x), y: redondear1(y) })
  }

  const alSoltar = () => {
    setArrastrando(false)
    setGuiaCentro(false)
  }

  // Alternativa al arrastre: flechas (Mayús = pasos grandes)
  const alTeclear = (e: KeyboardEvent<HTMLDivElement>) => {
    const mov = movimientos[e.key]
    if (!mov) return
    e.preventDefault()
    const paso = e.shiftKey ? 5 : 0.5
    onChange({
      x: redondear1(clamp(titulo.x + mov[0] * paso, 0, 100)),
      y: redondear1(clamp(titulo.y + mov[1] * paso, 0, 100)),
    })
  }

  const trazo = `${((GROSOR_BORDE * 2) / ANCHO_REF) * 100}cqw`

  return (
    <div
      ref={escenaRef}
      className="relative aspect-9/16 h-full max-h-full max-w-full overflow-hidden rounded-xl border border-line bg-[radial-gradient(ellipse_at_top,#1d2735,#07090d)] @container"
    >
      {/* Donde va el video, igual que en el formato borroso */}
      <div className="absolute inset-x-0 top-1/2 aspect-video -translate-y-1/2 bg-black">
        {videoSrc ? (
          <video
            ref={videoRef}
            src={videoSrc}
            playsInline
            preload="auto"
            onLoadedMetadata={(e) => onVideoListo(e.currentTarget.duration)}
            className="h-full w-full object-contain"
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-[#222c3a] text-xs text-muted">
            Video (demostración)
          </div>
        )}
      </div>

      {zonasSeguras && (
        <>
          <div className="pointer-events-none absolute inset-x-0 top-0 h-[8%] bg-bad/15" />
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-[20%] bg-bad/15" />
          <div className="pointer-events-none absolute bottom-[20%] right-0 top-[45%] w-[14%] bg-bad/15" />
        </>
      )}

      {guiaCentro && <div className="pointer-events-none absolute inset-y-0 left-1/2 w-px bg-accent" />}

      <div
        role="group"
        tabIndex={0}
        aria-label="Título del video. Arrastra o usa las flechas del teclado para moverlo."
        data-arrastrando={arrastrando}
        onPointerDown={alPresionar}
        onPointerMove={alMover}
        onPointerUp={alSoltar}
        onPointerCancel={alSoltar}
        onKeyDown={alTeclear}
        className="absolute max-w-[86%] cursor-grab touch-none select-none whitespace-pre-wrap wrap-break-word text-center font-bold leading-tight data-[arrastrando=true]:cursor-grabbing"
        style={{
          left: `${titulo.x}%`,
          top: `${titulo.y}%`,
          transform: 'translate(-50%, -50%)',
          fontSize: `${(titulo.tamano / ANCHO_REF) * 100}cqw`,
          color: '#fff',
          WebkitTextStroke: `${trazo} #000`,
          paintOrder: 'stroke fill',
          opacity: titulo.texto ? 1 : 0.4,
          display: titulo.visible ? undefined : 'none',
        }}
      >
        {titulo.texto || 'Escribe un título'}
      </div>
    </div>
  )
}