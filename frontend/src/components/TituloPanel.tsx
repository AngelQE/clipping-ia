import { clamp } from '../lib/num'
import type { TituloVideo } from '../types'

interface Props {
  titulo: TituloVideo
  onChange: (cambios: Partial<TituloVideo>) => void
  zonasSeguras: boolean
  onZonasSeguras: (valor: boolean) => void
}

interface CampoProps {
  etiqueta: string
  valor: number
  min: number
  max: number
  paso: number
  unidad: string
  onChange: (n: number) => void
}

// Se confirma al salir del campo o con Enter, para poder borrar y escribir con calma
function Campo({ etiqueta, valor, min, max, paso, unidad, onChange }: CampoProps) {
  const aplicar = (input: HTMLInputElement) => {
    const n = input.valueAsNumber
    if (Number.isNaN(n)) {
      input.value = String(valor)
      return
    }
    onChange(clamp(n, min, max))
  }

  return (
    <label className="flex items-center justify-between gap-3 text-sm text-muted">
      {etiqueta}
      <span className="flex items-center gap-1.5">
        <input
          key={valor}
          type="number"
          inputMode="decimal"
          defaultValue={valor}
          min={min}
          max={max}
          step={paso}
          onBlur={(e) => aplicar(e.currentTarget)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') aplicar(e.currentTarget)
          }}
          className="tnum w-20 rounded-md border border-line bg-raised px-2 py-1.5 text-right text-white"
        />
        <span className="w-4 text-xs">{unidad}</span>
      </span>
    </label>
  )
}

export default function TituloPanel({ titulo, onChange, zonasSeguras, onZonasSeguras }: Props) {
  return (
    <div className="flex flex-col gap-4">
      <label className="flex flex-col gap-1.5 text-sm text-muted">
        Texto del título
        <textarea
          value={titulo.texto}
          onChange={(e) => onChange({ texto: e.target.value })}
          rows={3}
          className="resize-none rounded-md border border-line bg-raised px-3 py-2 text-white"
        />
      </label>

      <Campo etiqueta="Posición horizontal" valor={titulo.x} min={0} max={100} paso={0.1} unidad="%" onChange={(x) => onChange({ x })} />
      <Campo etiqueta="Posición vertical" valor={titulo.y} min={0} max={100} paso={0.1} unidad="%" onChange={(y) => onChange({ y })} />
      <Campo etiqueta="Tamaño" valor={titulo.tamano} min={20} max={200} paso={1} unidad="px" onChange={(tamano) => onChange({ tamano })} />

      <div className="flex items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-sm text-muted">
          <input type="checkbox" checked={zonasSeguras} onChange={(e) => onZonasSeguras(e.target.checked)} />
          Zonas seguras
        </label>
        <button
          type="button"
          onClick={() => onChange({ x: 50, y: 16 })}
          className="press rounded-md border border-line px-3 py-1.5 text-sm hover:bg-raised"
        >
          Restablecer
        </button>
      </div>

      <p className="text-xs leading-relaxed text-muted">
        Arrastra el título en la vista previa, o usa las flechas del teclado (con Mayús, pasos grandes). Las
        zonas seguras son aproximadas: marcan dónde las apps suelen poner sus botones.
      </p>
    </div>
  )
}