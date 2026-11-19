import glob
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime

ARCHIVO = "evaluaciones.jsonl"

VEREDICTOS = {"b": "bien", "r": "regular", "m": "mal"}

PROBLEMAS = {
    "1": "empieza tarde (falta contexto al inicio)",
    "2": "empieza a mitad de una idea",
    "3": "termina antes del final o del remate",
    "4": "termina tarde (sobra al final)",
    "5": "mezcla dos temas",
    "6": "momento aburrido o sin gracia",
    "7": "falta una parte clave (por ejemplo, el contenido original o la reacción)",
    "8": "subtítulos con errores o faltantes",
    "9": "el tipo de video detectado no era el correcto",
    "10": "otro",
}


def _clave(d):
    """Identifica un clip por su video y sus tiempos, para no calificarlo dos veces."""
    return f"{d.get('video')}|{round(d.get('inicio', 0), 1)}|{round(d.get('fin', 0), 1)}"


def _leer_evaluaciones():
    if not os.path.exists(ARCHIVO):
        return []
    evaluaciones = []
    with open(ARCHIVO, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            try:
                evaluaciones.append(json.loads(linea))
            except json.JSONDecodeError:
                pass
    return evaluaciones


def calificar(carpeta="salida", abrir=True, todos=False):
    ya = {e["clave"] for e in _leer_evaluaciones()}
    pendientes = []
    for ruta in sorted(glob.glob(os.path.join(carpeta, "*.json")), key=os.path.getmtime):
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
        if "archivo" not in d or "inicio" not in d:
            continue
        if todos or _clave(d) not in ya:
            pendientes.append(d)

    if not pendientes:
        print("No hay clips pendientes de calificar.")
        return

    print(f"{len(pendientes)} clips por calificar.\n")
    for n, d in enumerate(pendientes, 1):
        duracion = d["fin"] - d["inicio"]
        print("-" * 60)
        print(f"[{n}/{len(pendientes)}] {d.get('titulo')}")
        print(f"Tipo: {d.get('tipo', '?')} | {duracion:.0f} s | puntaje del modelo: {d.get('puntaje')}")
        print(f"Razón del modelo: {d.get('razon', '')}")
        if abrir:
            try:
                os.startfile(d["archivo"])   # abre el clip con tu reproductor (Windows)
            except Exception:
                pass

        veredicto = ""
        while veredicto not in ("b", "r", "m", "s", "q"):
            veredicto = input("¿Qué tal? [b] bien  [r] regular  [m] mal  [s] saltar  [q] salir: ").strip().lower()[:1]
        if veredicto == "q":
            break
        if veredicto == "s":
            continue

        problemas, nota = [], ""
        if veredicto in ("r", "m"):
            for numero, texto in PROBLEMAS.items():
                print(f"  {numero:>2}) {texto}")
            elegidos = input("¿Qué falló? Números separados por coma (Enter para omitir): ")
            problemas = [PROBLEMAS[x.strip()] for x in elegidos.split(",") if x.strip() in PROBLEMAS]
        nota = input("Nota opcional (Enter para omitir): ").strip()

        registro = {
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "clave": _clave(d),
            "video": d.get("video"),
            "archivo": d.get("archivo"),
            "tipo": d.get("tipo"),
            "titulo": d.get("titulo"),
            "inicio": d.get("inicio"),
            "fin": d.get("fin"),
            "duracion": round(duracion, 1),
            "puntaje_modelo": d.get("puntaje"),
            "razon_modelo": d.get("razon"),
            "veredicto": VEREDICTOS[veredicto],
            "problemas": problemas,
            "nota": nota,
        }
        with open(ARCHIVO, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")

    print("\nListo. Mira el resultado con:  python calificar.py resumen")


def _media(valores):
    valores = [v for v in valores if isinstance(v, (int, float))]
    return sum(valores) / len(valores) if valores else None


def resumen():
    ultimas = {}
    for e in _leer_evaluaciones():
        ultimas[e["clave"]] = e   # si calificaste un clip dos veces, vale la última
    if not ultimas:
        print("Todavía no hay evaluaciones.")
        return

    por_tipo = defaultdict(list)
    for e in ultimas.values():
        por_tipo[e.get("tipo") or "?"].append(e)

    for tipo, lista in sorted(por_tipo.items()):
        cuenta = Counter(e["veredicto"] for e in lista)
        total = len(lista)
        print(f"\n== {tipo} ({total} clips) ==")
        print(f"   bien: {cuenta['bien']} ({100 * cuenta['bien'] // total}%) | "
              f"regular: {cuenta['regular']} | mal: {cuenta['mal']}")

        problemas = Counter(p for e in lista for p in e.get("problemas", []))
        for problema, veces in problemas.most_common(5):
            print(f"   - {problema}: {veces}")

        buenos = [e for e in lista if e["veredicto"] == "bien"]
        malos = [e for e in lista if e["veredicto"] == "mal"]
        if buenos and malos:
            print(f"   puntaje medio del modelo: bien {_media([e['puntaje_modelo'] for e in buenos]):.1f} "
                  f"| mal {_media([e['puntaje_modelo'] for e in malos]):.1f}")
        if buenos:
            print(f"   duración media de los buenos: {_media([e['duracion'] for e in buenos]):.0f} s")

        notas = [e["nota"] for e in lista if e.get("nota") and e["veredicto"] != "bien"]
        for nota in notas[:5]:
            print(f"   nota: {nota}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "resumen" in args:
        resumen()
    else:
        calificar(abrir="--sin-abrir" not in args, todos="--todos" in args)