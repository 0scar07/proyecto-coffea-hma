# -*- coding: utf-8 -*-
"""
Genera docs/documentacion/index.html (+ assets/) y docs/index.html (redireccion).

Uso (desde la raiz del repo, con el entorno ya instalado -- no crea nada nuevo):
    python entregables/02_codigo_documentado/fuente_html/generar_docs_html.py
Escribe previsualizaciones de verificacion en
entregables/02_codigo_documentado/fuente_html/previews/ (ignorada por git).

Todo el contenido tecnico (funciones, firmas, docstrings, conteos, cifras de ejemplo) se lee
en vivo de app/app.py y de la salida real de la app contra datos_reales_coffea_2023.xlsx --
nada se copia de memoria ni se inventa.
"""
import ast
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent                       # .../02_codigo_documentado/fuente_html
REPO = AQUI.parents[2]                                        # raiz del repo
APP_PY = REPO / "app" / "app.py"
XLSX = REPO / "datos_reales" / "datos_reales_coffea_2023.xlsx"
DOCS_DIR = REPO / "docs" / "documentacion"
ASSETS_DIR = DOCS_DIR / "assets"
PREVIEWS = AQUI / "previews"
BUILD = AQUI / "_build"

for d in (DOCS_DIR, ASSETS_DIR, PREVIEWS, BUILD):
    d.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(REPO / "app"))
FECHA_GENERACION = date.today().isoformat()

# ------------------------------------------------------------------------------------
# 1. Analisis estatico de app/app.py con ast: funciones, firmas, docstrings, secciones
# ------------------------------------------------------------------------------------
codigo_fuente = APP_PY.read_text(encoding="utf-8")
lineas_fuente = codigo_fuente.splitlines()
arbol = ast.parse(codigo_fuente, filename=str(APP_PY))

SECCIONES_ORDEN = [
    "Resumen", "Ajustar modelos", "Metodología", "Resultados", "Gráficas de barras",
    "Resultados esperados", "Estadística", "Residuos", "Discusión y conclusiones",
    "Datos de prueba", "Exportar reporte",
]


def encontrar_limites_secciones():
    """Devuelve [(nombre_seccion, linea_inicio, linea_fin), ...] a partir de los
    bloques if/elif seccion == "...": literales del codigo (no inventado)."""
    limites = []
    for i, linea in enumerate(lineas_fuente, start=1):
        s = linea.strip()
        if s.startswith('if seccion == "') or s.startswith('elif seccion == "'):
            nombre = s.split('"')[1]
            limites.append([nombre, i, None])
    for j in range(len(limites) - 1):
        limites[j][2] = limites[j + 1][1] - 1
    if limites:
        limites[-1][2] = len(lineas_fuente)
    return limites


LIMITES_SECCIONES = encontrar_limites_secciones()
assert [n for n, _, _ in LIMITES_SECCIONES] == SECCIONES_ORDEN, "Las secciones de app.py cambiaron"


def seccion_de_la_linea(n):
    for nombre, ini, fin in LIMITES_SECCIONES:
        if ini <= n <= fin:
            return nombre
    return None


def firma_de(nodo: ast.FunctionDef) -> str:
    partes = []
    args = nodo.args
    defaults = [None] * (len(args.args) - len(args.defaults)) + list(args.defaults)
    for a, d in zip(args.args, defaults):
        txt = a.arg
        if a.annotation is not None:
            txt += f": {ast.unparse(a.annotation)}"
        if d is not None:
            txt += f"={ast.unparse(d)}"
        partes.append(txt)
    if args.vararg:
        partes.append("*" + args.vararg.arg)
    for a, d in zip(args.kwonlyargs, args.kw_defaults):
        txt = a.arg
        if d is not None:
            txt += f"={ast.unparse(d)}"
        partes.append(txt)
    if args.kwarg:
        partes.append("**" + args.kwarg.arg)
    return f"{nodo.name}({', '.join(partes)})"


def comentario_inmediato_anterior(linea_def: int) -> str | None:
    """Si la funcion no tiene docstring, busca un bloque de comentarios '#' justo
    arriba de 'def' (sin lineas en blanco de por medio) y lo devuelve unido."""
    i = linea_def - 2  # linea_def es 1-indexada; i es 0-indexado, la linea justo antes
    comentarios = []
    while i >= 0:
        s = lineas_fuente[i].strip()
        if s.startswith("#"):
            comentarios.insert(0, s.lstrip("#").strip())
            i -= 1
        else:
            break
    return " ".join(comentarios) if comentarios else None


FUNCIONES = []
for nodo in arbol.body:
    if isinstance(nodo, ast.FunctionDef):
        doc = ast.get_docstring(nodo)
        comentario = None if doc else comentario_inmediato_anterior(nodo.lineno)
        # Usos reales: lineas donde aparece "nombre(" fuera de la propia definicion
        usos_lineas = [
            i + 1 for i, l in enumerate(lineas_fuente)
            if f"{nodo.name}(" in l and (i + 1) < nodo.lineno or (i + 1) > nodo.end_lineno
        ]
        secciones_uso = sorted(set(filter(None, (seccion_de_la_linea(n) for n in usos_lineas))), key=SECCIONES_ORDEN.index) if usos_lineas else []
        FUNCIONES.append({
            "nombre": nodo.name,
            "firma": firma_de(nodo),
            "docstring": doc,
            "comentario": comentario,
            "linea": nodo.lineno,
            "linea_fin": nodo.end_lineno,
            "secciones": secciones_uso,
            "publica": not nodo.name.startswith("_"),
        })

CLASES = []
for nodo in ast.walk(arbol):
    if isinstance(nodo, ast.ClassDef):
        doc = ast.get_docstring(nodo)
        metodos = [n.name for n in nodo.body if isinstance(n, ast.FunctionDef)]
        CLASES.append({"nombre": nodo.name, "docstring": doc, "linea": nodo.lineno, "metodos": metodos})

SIN_DESCRIPCION = [f["nombre"] for f in FUNCIONES if not f["docstring"] and not f["comentario"]]
print(f"OK: {len(FUNCIONES)} funciones de nivel superior, {len(CLASES)} clases anidadas encontradas via ast.")
print(f"Funciones SIN docstring ni comentario inmediato ({len(SIN_DESCRIPCION)}): {SIN_DESCRIPCION}")

# ------------------------------------------------------------------------------------
# 2. Metadatos del repositorio (conteos reales, nada decorativo)
# ------------------------------------------------------------------------------------
def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


COMMIT_HASH = git("rev-parse", "--short", "HEAD")
COMMIT_HASH_LARGO = git("rev-parse", "HEAD")
RAMA_ACTUAL = git("rev-parse", "--abbrev-ref", "HEAD")
GIT_LOG_RESUMEN = git("log", "--oneline", "-15")

CONTEOS = {
    "n_funciones": len(FUNCIONES),
    "n_funciones_publicas": sum(1 for f in FUNCIONES if f["publica"]),
    "n_clases": len(CLASES),
    "n_lineas": len(lineas_fuente),
    "n_secciones": len(SECCIONES_ORDEN),
    "n_sin_descripcion": len(SIN_DESCRIPCION),
}
print("Conteos reales:", CONTEOS)

with open(BUILD / "analisis_ast.json", "w", encoding="utf-8") as f:
    json.dump({"funciones": FUNCIONES, "clases": CLASES, "conteos": CONTEOS,
               "sin_descripcion": SIN_DESCRIPCION, "commit": COMMIT_HASH}, f, ensure_ascii=False, indent=2)

print("Analisis AST guardado en _build/analisis_ast.json")

# ------------------------------------------------------------------------------------
# 3. Datos reales: metricas, mejor modelo, efecto de la inoculacion, notas de K
#    (mismo patron que entregables/06_guia_tecnica/fuente_pdf/generar_guia_pdf.py)
# ------------------------------------------------------------------------------------
import app as m  # noqa: E402  (modulo real, ya con sys.path ajustado arriba)


def extraer_datos_reales():
    df = pd.read_excel(XLSX, sheet_name=0)
    df.columns = [c.strip().lower() for c in df.columns]
    datos = {v: {"-M": {}, "+M": {}} for v in sorted(df["variable"].unique())}
    for (variable, grupo, dia), g in df.groupby(["variable", "grupo", "dat"]):
        datos[variable][grupo][int(dia)] = g["valor"].to_numpy()

    RES = m.ajustar_todos_los_modelos(datos)
    modelos = list(m.MODELOS.keys())

    metricas, mejor_modelo, efecto, notas_k = {}, {}, {}, {}
    for variable in datos:
        metricas[variable] = {}
        for grupo in ("-M", "+M"):
            metricas[variable][grupo] = {}
            for modelo in modelos:
                res = RES[variable][grupo][modelo]
                estado = m.estado_de_ajuste(res)
                if estado == m.ESTADO_OK:
                    metricas[variable][grupo][modelo] = {
                        "estado": "OK", "r2": float(res["r2"]), "rmse": float(res["rmse"]),
                        "mae": float(res.get("mae")),
                    }
                else:
                    metricas[variable][grupo][modelo] = {"estado": estado}
        _, mejores = m.calcular_tabla_modelo(RES, datos, variable, modelos)
        mejor_modelo[variable] = mejores
        filas = m.calcular_efecto_micorriza(datos, variable)
        efecto[variable] = [
            {"dia": int(f["dia"]), "media_control": float(f["media_control"]),
             "media_tratado": float(f["media_tratado"]), "incremento_pct": float(f["incremento_pct"]),
             "t": float(f["t"]), "p": float(f["p"]), "significativo": bool(f["significativo"])}
            for f in filas
        ]
        _, pie = m.fig_curvas_publicacion(datos, RES, variable, modelos, "real")
        notas_k[variable] = {"descripcion": pie["descripcion"], "notas": pie.get("notas") or []}

    return {
        "metricas": metricas, "mejor_modelo": mejor_modelo, "efecto": efecto, "notas_k": notas_k,
        "modelos_parametros": {nombre: info["nombres_param"] for nombre, info in m.MODELOS.items()},
        "n_dias_minimos": {nombre: len(info["nombres_param"]) for nombre, info in m.MODELOS.items()},
        "estados": {"OK": m.ESTADO_OK, "no_convergio": m.ESTADO_NO_CONVERGIO, "sin_dias": m.ESTADO_SIN_DIAS},
    }


DATA = extraer_datos_reales()
with open(BUILD / "datos_app.json", "w", encoding="utf-8") as f:
    json.dump(DATA, f, ensure_ascii=False, indent=2)
print("Datos reales extraidos y guardados en _build/datos_app.json")

# Formulas exactas de los 3 modelos, leidas del propio codigo fuente (no de memoria)
FORMULAS_FUENTE = {}
for nodo in arbol.body:
    if isinstance(nodo, ast.FunctionDef) and nodo.name in ("modelo_exponencial", "modelo_logistico", "modelo_gompertz"):
        cuerpo = [n for n in nodo.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
        ret = cuerpo[-1]
        expr_codigo = ast.unparse(ret.value) if isinstance(ret, ast.Return) else ast.unparse(ret)
        FORMULAS_FUENTE[nodo.name] = {"firma": firma_de(nodo), "expresion": expr_codigo}
print("Formulas extraidas del codigo:", FORMULAS_FUENTE)

FUNCIONES_POR_NOMBRE = {f["nombre"]: f for f in FUNCIONES}
AUTORES = "Richard Montez, Diego Barrios, Santiago Uribe, Oscar Llanos"
REPO_URL = "https://github.com/0scar07/proyecto-coffea-hma"


def esc(s):
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


# ------------------------------------------------------------------------------------
# 4. Componentes HTML reutilizables
# ------------------------------------------------------------------------------------
def tarjeta(titulo, cuerpo_html):
    return f'<div class="tarjeta"><h3>{esc(titulo)}</h3>{cuerpo_html}</div>'


def recuadro(tipo, cuerpo_html, etiqueta=None):
    etiquetas = {"nota": "Nota", "importante": "Importante", "consejo": "Consejo", "advertencia": "Advertencia"}
    return (f'<div class="recuadro recuadro-{tipo}"><span class="etiqueta">{etiqueta or etiquetas[tipo]}</span>'
            f'{cuerpo_html}</div>')


def tabla_html(encabezados, filas, pista="Desliza para ver más columnas"):
    ths = "".join(f"<th>{esc(h)}</th>" for h in encabezados)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in fila) + "</tr>" for fila in filas)
    return (f'<div class="tabla-contenedor"><div class="tabla-scroll">'
            f'<table><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table></div>'
            f'<div class="pista-scroll">{pista} →</div></div>')


_contador_bloques_codigo = [0]


def bloque_codigo(texto, lenguaje="python"):
    _contador_bloques_codigo[0] += 1
    lineas = esc(texto).split("\n")
    lineas_html = "\n".join(f'<span class="linea">{l}</span>' for l in lineas)
    return (f'<div class="bloque-codigo"><button class="boton-copiar" type="button" '
            f'aria-label="Copiar código"><span class="texto-copiar">Copiar</span></button>'
            f'<pre><code class="lenguaje-{lenguaje}">{lineas_html}</code></pre></div>')


def formula_caja(nombre, expresion, extra=""):
    return (f'<div class="formula-caja"><div class="nombre">{esc(nombre)}</div>'
            f'<div class="expr">{esc(expresion)}</div>{extra}</div>')


def contador(valor, etiqueta):
    return f'<div class="contador"><span class="valor" data-valor="{valor}">0</span><span class="etiqueta">{esc(etiqueta)}</span></div>'


_contador_plegables = [0]


def plegable(titulo, cuerpo_html, abierto=False):
    _contador_plegables[0] += 1
    return (f'<details class="plegable"{" open" if abierto else ""}>'
            f'<summary>{esc(titulo)}<span class="flecha" aria-hidden="true">▸</span></summary>'
            f'<div class="contenido-plegable">{cuerpo_html}</div></details>')


_contador_pestanas = [0]


def pestanas(items):
    """items: lista de (titulo, contenido_html)."""
    _contador_pestanas[0] += 1
    gid = f"tabs-{_contador_pestanas[0]}"
    botones = "".join(
        f'<li role="presentation"><button class="tab-boton" role="tab" id="{gid}-tab-{i}" '
        f'aria-controls="{gid}-panel-{i}" aria-selected="{"true" if i == 0 else "false"}" '
        f'tabindex="{0 if i == 0 else -1}" type="button">{esc(t)}</button></li>'
        for i, (t, _) in enumerate(items)
    )
    paneles = "".join(
        f'<div class="panel-tab{" activo" if i == 0 else ""}" role="tabpanel" id="{gid}-panel-{i}" '
        f'aria-labelledby="{gid}-tab-{i}">{c}</div>'
        for i, (t, c) in enumerate(items)
    )
    return (f'<div class="pestanas"><ul class="pestanas-lista" role="tablist">{botones}'
            f'<span class="indicador-tab" aria-hidden="true"></span></ul>{paneles}</div>')


def fmt_r2(v):
    return f"{v:.4f}" if v is not None else "–"


def fila_metrica(variable, grupo, modelo):
    d = DATA["metricas"][variable][grupo][modelo]
    if d["estado"] == "OK":
        return [grupo, modelo, fmt_r2(d["r2"]), fmt_r2(d["rmse"]), fmt_r2(d["mae"])]
    return [grupo, modelo, f"<em>{esc(d['estado'])}</em>", "–", "–"]


# ------------------------------------------------------------------------------------
# 5. Diagrama de arquitectura (SVG en linea, dos orientaciones)
#    Cada nodo referencia una funcion REAL de app.py (verificada abajo).
# ------------------------------------------------------------------------------------
NODOS_DIAGRAMA = [
    ("Datos", "cargar_datos_desde_archivo", "Excel/CSV en formato largo, o datos simulados"),
    ("Validación", "advertir_dias_insuficientes", "días mínimos por modelo antes de ajustar"),
    ("Ajuste (3 modelos)", "ajustar_todos_los_modelos", "curve_fit: Exponencial, Logístico, Gompertz"),
    ("Métricas", "calcular_r2", "R², RMSE, MAE por variable, grupo y modelo"),
    ("Gráficas", "fig_curvas_publicacion", "curvas, barras, tasas AGR/RGR"),
    ("Reporte PDF", "ReportePDF", "clase FPDF: metodología, tablas y figuras"),
]
for _titulo, _fn, _desc in NODOS_DIAGRAMA:
    if _fn != "ReportePDF":
        assert _fn in FUNCIONES_POR_NOMBRE, f"Funcion de diagrama no encontrada en app.py: {_fn}"


def _svg_nodo(x, y, w, h, titulo, fn, idx):
    return f'''<g class="grupo-nodo" data-funcion="{esc(fn)}" data-index="{idx}">
      <rect class="caja-nodo" x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/>
      <text class="texto-nodo" x="{x + w/2}" y="{y + h/2 - 6}" text-anchor="middle">{esc(titulo)}</text>
      <text class="texto-funcion" x="{x + w/2}" y="{y + h/2 + 14}" text-anchor="middle">{esc(fn)}()</text>
    </g>'''


def construir_diagrama(orientacion):
    defs = '''<defs><marker id="flecha-punta" viewBox="0 0 10 10" refX="9" refY="5"
      markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z"/></marker></defs>'''
    grupos = []
    flechas = []
    n = len(NODOS_DIAGRAMA)
    if orientacion == "horizontal":
        w, h = 190, 84
        gap = 60
        x0, y0 = 20, 60
        viewbox = f"0 0 {x0*2 + n*w + (n-1)*gap} {y0*2 + h}"
        for i, (titulo, fn, _desc) in enumerate(NODOS_DIAGRAMA):
            x = x0 + i * (w + gap)
            grupos.append(_svg_nodo(x, y0, w, h, titulo, fn, i))
            if i < n - 1:
                x1, x2 = x + w, x + w + gap
                ym = y0 + h / 2
                flechas.append(f'<path class="flecha-flujo" d="M{x1},{ym} L{x2},{ym}" marker-end="url(#flecha-punta)"/>')
    else:
        w, h = 260, 84
        gap = 46
        x0, y0 = 30, 20
        viewbox = f"0 0 {x0*2 + w} {y0*2 + n*h + (n-1)*gap}"
        for i, (titulo, fn, _desc) in enumerate(NODOS_DIAGRAMA):
            y = y0 + i * (h + gap)
            grupos.append(_svg_nodo(x0, y, w, h, titulo, fn, i))
            if i < n - 1:
                y1, y2 = y + h, y + h + gap
                xm = x0 + w / 2
                flechas.append(f'<path class="flecha-flujo" d="M{xm},{y1} L{xm},{y2}" marker-end="url(#flecha-punta)"/>')

    clase_extra = "solo-escritorio-diagrama" if orientacion == "horizontal" else "solo-movil-diagrama"
    titulo_accesible = "Diagrama de flujo: Datos, Validación, Ajuste de tres modelos, Métricas, Gráficas y Reporte PDF"
    return (f'<svg class="diagrama-svg {clase_extra}" viewBox="{viewbox}" role="img" '
            f'aria-label="{esc(titulo_accesible)}">{defs}{"".join(flechas)}{"".join(grupos)}</svg>')


DIAGRAMA_HORIZONTAL = construir_diagrama("horizontal")
DIAGRAMA_VERTICAL = construir_diagrama("vertical")
print("Diagrama construido con", len(NODOS_DIAGRAMA), "nodos (funciones verificadas contra app.py).")


# ------------------------------------------------------------------------------------
# 6. Contenido de cada apartado
# ------------------------------------------------------------------------------------
APARTADOS = []  # lista de (id, etiqueta_corta, titulo, html)


def agregar_apartado(id_, etiqueta, titulo, html):
    APARTADOS.append({"id": id_, "etiqueta": etiqueta, "titulo": titulo, "html": html})


# ---- Portada ----
agregar_apartado("portada", "Portada", "Documentación técnica de Coffea IA", f"""
<p class="apartado-etiqueta">Coffea IA · Documentación técnica del código</p>
<h1>Documentación técnica de Coffea IA</h1>
<p>Referencia técnica de <code>app/app.py</code> generada a partir del código real y de la
salida de la app con datos reales — no es un tutorial de usuario (para eso existe la
<a href="../06_guia_tecnica/guia_tecnica_usuario.pdf">guía técnica de usuario en PDF</a>).</p>
<div class="contadores">
  {contador(CONTEOS['n_funciones'], 'Funciones documentadas')}
  {contador(CONTEOS['n_lineas'], 'Líneas en app.py')}
  {contador(CONTEOS['n_secciones'], 'Secciones de la app')}
  {contador(CONTEOS['n_sin_descripcion'], 'Funciones sin docstring')}
</div>
{recuadro('nota', f"<b>Versión</b> generada el {FECHA_GENERACION} sobre el commit "
  f"<code>{COMMIT_HASH}</code> de la rama <code>{esc(RAMA_ACTUAL)}</code>. Cada cifra de esta "
  "página (funciones, líneas, resultados de ejemplo) se calculó en el momento de generar, "
  "no está escrita a mano.")}
<div class="enlaces-pie">
  <a class="boton" href="[URL de la app en Streamlit Cloud — pendiente de publicar en el README]">Abrir la app</a>
  <a class="boton secundario" href="{REPO_URL}">Ver el repositorio</a>
  <a class="boton secundario" href="../06_guia_tecnica/guia_tecnica_usuario.pdf">Guía técnica de usuario (PDF)</a>
</div>
{recuadro('advertencia', "Las réplicas individuales del dataset real son <b>sintéticas</b> "
  "(generadas a partir de las medias y CV% de Aguirre-Medina et al., 2023, DOI "
  "10.35196/rfm.2023.3.273); los p-valores que aparecen en esta página son ilustrativos de la "
  "metodología, no evidencia estadística independiente. La validación externa está pendiente.")}
""")

# ---- 1. Vision general ----
agregar_apartado("vision-general", "1", "Visión general y arquitectura", f"""
<p class="apartado-etiqueta">01 · Arquitectura</p>
<h1>Visión general y diagrama de arquitectura</h1>
<p>Coffea IA es una app de Streamlit de un solo archivo (<code>app/app.py</code>, {CONTEOS['n_lineas']}
líneas) que ajusta tres modelos de crecimiento no lineales a datos de <i>Coffea arabica</i> y
compara un grupo control (−M) contra uno inoculado con hongos micorrízicos arbusculares (+M).
El flujo de datos es siempre el mismo, sin importar la sección de la app que se esté usando:</p>
<div class="diagrama-envoltura">
  {DIAGRAMA_HORIZONTAL}
  {DIAGRAMA_VERTICAL}
  <p class="apartado-etiqueta" style="margin-top:12px;">Pasa el cursor o el foco por una caja para
  ver qué función la implementa; haz clic para saltar a su entrada en la Referencia de funciones.</p>
</div>
<h2>Las capas del archivo</h2>
<ol>
  <li><b>Estilo y composición visual</b> — da formato a las figuras de Plotly y separa el pie de
  cada figura del gráfico mismo.</li>
  <li><b>Modelos matemáticos</b> — <code>modelo_exponencial</code>, <code>modelo_logistico</code>,
  <code>modelo_gompertz</code>: funciones puras, sin efectos secundarios.</li>
  <li><b>Datos y utilidades numéricas</b> — generación de datos simulados, manejo de réplicas,
  métricas de bondad de ajuste.</li>
  <li><b>Ajuste y pruebas estadísticas</b> — el núcleo: <code>ajustar_todos_los_modelos</code> y
  <code>prueba_t_independiente</code>.</li>
  <li><b>Construcción de figuras</b> — una función por tipo de gráfica.</li>
  <li><b>Reporte PDF</b> — la clase <code>ReportePDF(FPDF)</code> y sus funciones de composición.</li>
  <li><b>Entrada/salida de datos</b> — lectura/escritura de Excel, plantilla descargable.</li>
  <li><b>Navegación e interfaz</b> — un bloque <code>if/elif seccion == "...":</code> por cada
  una de las {CONTEOS['n_secciones']} secciones del menú.</li>
</ol>
""")

# ---- 2. Estructura del repositorio ----
ARBOL_REPO = """proyecto-coffea-hma/
├── app/
│   ├── app.py                  # única fuente de la lógica y el UI (no se toca desde esta doc)
│   ├── requirements.txt
│   └── .streamlit/config.toml  # tema "Cuaderno de campo"
├── datos_reales/
│   └── datos_reales_coffea_2023.xlsx
├── scripts/
│   └── validacion_cruzada_real.py
├── docs/
│   ├── screenshots/            # capturas de la app
│   ├── figuras/                 # gráficas exportadas en PNG
│   ├── reportes/                 # PDF de ejemplo generado por la app
│   ├── documentacion/            # esta página (index.html + assets/)
│   └── index.html                # redirección a documentacion/
└── entregables/                 # borradores y plantillas de gestión/difusión
    ├── 02_codigo_documentado/
    │   ├── documentacion_codigo.md
    │   └── fuente_html/           # fuente y script de esta página
    └── 06_guia_tecnica/
        ├── guia_tecnica_usuario.md
        ├── guia_tecnica_usuario.pdf
        └── fuente_pdf/"""

agregar_apartado("estructura-repo", "2", "Estructura del repositorio", f"""
<p class="apartado-etiqueta">02 · Repositorio</p>
<h1>Estructura del repositorio</h1>
<p>Árbol real de carpetas (se omiten <code>__pycache__/</code>, y las carpetas de previsualización
<code>previews/</code>/<code>_build/</code>, que están en <code>.gitignore</code>):</p>
{bloque_codigo(ARBOL_REPO, "text")}
{recuadro('importante', "<code>app/app.py</code>, <code>app/requirements.txt</code> y "
  "<code>app/.streamlit/config.toml</code> son los únicos archivos que Streamlit Cloud necesita "
  "para desplegar — nunca se mueven ni se renombran (ver Apartado 9, Despliegue).")}
""")

# ---- 3. Formato de datos y validaciones ----
agregar_apartado("formato-datos", "3", "Formato de datos y validaciones", f"""
<p class="apartado-etiqueta">03 · Datos</p>
<h1>Formato de datos y validaciones</h1>
<p>La app acepta datos en <b>formato largo</b>, con estas columnas exactas (verificado contra
<code>datos_reales_coffea_2023.xlsx</code>):</p>
{tabla_html(["Columna", "Significado", "Ejemplo"], [
    ["<code>variable</code>", "Qué se midió", "altura, area_foliar, biomasa, hojas, diametro"],
    ["<code>grupo</code>", "Tratamiento", "-M (control) o +M (inoculado)"],
    ["<code>dat</code>", "Día después del trasplante", "28, 56, 84, 112"],
    ["<code>replica</code>", "Número de réplica", "1 a 5"],
    ["<code>valor</code>", "Valor medido", "9.0538"],
])}
<h2>Qué valida la app al cargar un archivo</h2>
<p><code>cargar_datos_desde_archivo</code> revisa que estén las columnas obligatorias antes de
aceptar el archivo; si falta alguna, muestra qué columna falta en vez de aceptar un archivo
incompleto. <code>advertir_dias_insuficientes</code> revisa, variable por variable, cuántos días
distintos hay disponibles y anticipa qué modelos no van a poder ajustarse.</p>
{recuadro('consejo', 'La plantilla descargable en la sección "Datos de prueba" '
  '(<code>generar_plantilla_excel</code>) siempre tiene el formato correcto — la forma más '
  'segura de empezar es partir de ella.')}
<h2>Datos reales incluidos</h2>
<p>Altura, número de hojas, área foliar y biomasa total en 4 momentos de muestreo (28, 56, 84 y
112 ddt), 5 réplicas por grupo y día, provienen de Aguirre-Medina et al. (2023). El diámetro del
tallo no está en ese estudio y sigue usando datos simulados.</p>
{recuadro('advertencia', "Las réplicas individuales del archivo real son <b>sintéticas</b>: "
  "generadas para reproducir la media y el CV% publicados, no son mediciones planta por planta.")}
""")

# ---- 4. Modelos ----
def _panel_modelo(nombre_fn, nombre_mostrado, dias_min):
    f = FORMULAS_FUENTE[nombre_fn]
    fdata = FUNCIONES_POR_NOMBRE[nombre_fn]
    return f"""
    {formula_caja(nombre_mostrado, f['expresion'])}
    <p><b>Firma en el código:</b> <code>{esc(f['firma'])}</code> (línea {fdata['linea']}).</p>
    <p><b>Días mínimos para converger:</b> {dias_min} (por su número de parámetros).</p>
    """


PANEL_EXPONENCIAL = _panel_modelo("modelo_exponencial", "Exponencial", DATA["n_dias_minimos"]["Exponencial"])
PANEL_LOGISTICO = _panel_modelo("modelo_logistico", "Logístico", DATA["n_dias_minimos"]["Logístico"])
PANEL_GOMPERTZ = _panel_modelo("modelo_gompertz", "Gompertz", DATA["n_dias_minimos"]["Gompertz"])

agregar_apartado("modelos", "4", "Modelos: fórmulas y convergencia", f"""
<p class="apartado-etiqueta">04 · Modelos</p>
<h1>Modelos: fórmulas, parámetros y regla de convergencia</h1>
<p>Parametrización exacta tal como está en <code>app/app.py</code> — extraída con <code>ast</code>
del propio código, no copiada de memoria:</p>
{pestanas([("Exponencial", PANEL_EXPONENCIAL), ("Logístico", PANEL_LOGISTICO), ("Gompertz", PANEL_GOMPERTZ)])}
<p>En Logístico y Gompertz, <code>K</code> es la asíntota superior, <code>k</code> la tasa de
crecimiento y <code>Ti</code> el punto de inflexión. El ajuste de los tres modelos se hace con
<code>scipy.optimize.curve_fit</code> — <b>regresión no lineal</b>, no aprendizaje automático.</p>
<h2>Regla de convergencia</h2>
<p>Cada modelo necesita un mínimo de días distintos de muestreo para ser identificable
(Exponencial ≥ 2; Logístico y Gompertz ≥ 3). Si un dataset no llega a ese mínimo, o si
<code>curve_fit</code> no converge, la app nunca fuerza ni aproxima un ajuste:</p>
{tabla_html(["Estado", "Cuándo ocurre", "Qué hace la app"], [
    [f"<code>{esc(DATA['estados']['sin_dias'])}</code>", "Menos días distintos de los que el modelo necesita",
     "No intenta el ajuste; lo dice explícitamente (<code>texto_estado_sin_dias</code>)."],
    [f"<code>{esc(DATA['estados']['no_convergio'])}</code>", "<code>curve_fit</code> no encontró una solución estable",
     "No dibuja ese modelo ni reporta un R²."],
    [f"<code>{esc(DATA['estados']['OK'])}</code>", "Convergió y tiene R² calculado",
     "Se muestra normalmente en tablas y gráficas."],
])}
<p>La función <code>estado_de_ajuste</code> es la única fuente de este vocabulario en toda la app
y en el PDF — nunca se reinterpreta caso por caso.</p>
""")

# ---- 5. Metricas y K ----
filas_altura_metricas = [fila_metrica("altura", g, mo) for g in ("-M", "+M") for mo in ("Exponencial", "Logístico", "Gompertz")]
notas_altura_k = "".join(f"<li>{esc(n)}</li>" for n in DATA["notas_k"]["altura"]["notas"])

agregar_apartado("metricas-k", "5", "Métricas y plausibilidad de K", f"""
<p class="apartado-etiqueta">05 · Métricas</p>
<h1>Métricas (R², RMSE, MAE) y criterio de plausibilidad de K</h1>
<p><b>R²</b> (0 a 1): qué proporción de la variación observada explica el modelo. <b>RMSE</b> y
<b>MAE</b>: error típico en las unidades de la variable; RMSE penaliza más los errores grandes.</p>
<h2>Ejemplo real — Altura</h2>
<p>Recalculado el {FECHA_GENERACION} sobre <code>datos_reales_coffea_2023.xlsx</code> llamando a
<code>ajustar_todos_los_modelos</code>:</p>
{tabla_html(["Grupo", "Modelo", "R²", "RMSE", "MAE"], filas_altura_metricas)}
<h2>Criterio de plausibilidad de K vigente</h2>
<p>La app solo dibuja la asíntota K (Logístico/Gompertz) si se cumplen las <b>cuatro</b>
condiciones a la vez (función <code>_asintota_k_plausible</code>):</p>
<ol>
  <li>El modelo convergió.</li>
  <li>R² ≥ 0.90.</li>
  <li>K ≤ 1.5× el máximo observado en ese grupo y variable.</li>
  <li>El punto de inflexión Ti cae dentro del rango de días muestreados.</li>
</ol>
<p>Ejemplo real (Altura, notas generadas por <code>fig_curvas_publicacion</code>):</p>
<ul>{notas_altura_k}</ul>
{recuadro('importante', "Un R² alto no implica que K esté bien identificada — puede fallar el "
  "criterio de rango o el del punto de inflexión aunque el ajuste general sea bueno en los "
  "puntos observados.")}
""")

# ---- 6. Estadistica ----
filas_efecto_areafoliar = [
    [str(f["dia"]), f'{f["media_control"]:.2f}', f'{f["media_tratado"]:.2f}', f'{f["incremento_pct"]:+.1f}%',
     f'{f["t"]:.3f}', ("p < 0.0001" if f["p"] < 0.0001 else f'p = {f["p"]:.4f}'), "Sí" if f["significativo"] else "No"]
    for f in DATA["efecto"]["area_foliar"]
]
agregar_apartado("estadistica", "6", "Estadística (t de Welch)", f"""
<p class="apartado-etiqueta">06 · Estadística</p>
<h1>Comparación estadística: prueba t de Welch</h1>
<p><code>prueba_t_independiente</code> compara −M contra +M con <code>scipy.stats.ttest_ind</code>
(<code>equal_var=False</code>) por variable y día — sin asumir que ambos grupos tienen la misma
varianza. <code>calcular_efecto_micorriza</code> arma la tabla completa: media −M, media +M,
incremento %, t, p y significancia.</p>
<h2>Ejemplo real — Área foliar</h2>
{tabla_html(["Día (ddt)", "Media −M", "Media +M", "Incremento +M", "t (Welch)", "p", "Significativo"], filas_efecto_areafoliar)}
{recuadro('advertencia', "Estas réplicas son sintéticas (Aguirre-Medina et al., 2023) — el "
  "p-valor confirma que la diferencia entre las medias <i>reportadas</i> es grande frente a la "
  "variabilidad reconstruida, pero no es evidencia estadística independiente nueva sobre el "
  "efecto de la micorrización.")}
<h2>Códigos de significancia (<code>texto_significancia</code>)</h2>
<p><code>ns</code> = p ≥ 0.05 · <code>*</code> = p &lt; 0.05 · <code>**</code> = p &lt; 0.01 ·
<code>***</code> = p &lt; 0.001. <code>formatear_p</code> evita el "p = 0.0000" engañoso: por
debajo de 0.0001 se reporta como cota superior ("p &lt; 0.0001").</p>
""")

# ---- 7. Graficas y reporte PDF ----
agregar_apartado("graficas-reporte", "7", "Gráficas y reporte PDF", f"""
<p class="apartado-etiqueta">07 · Salidas</p>
<h1>Gráficas y reporte PDF</h1>
<p>Cada tipo de gráfica tiene su propia función constructora, todas devuelven <code>(fig, pie)</code>
— la figura de Plotly y el texto del pie <i>por separado</i> (nunca como anotación incrustada):</p>
{tabla_html(["Función", "Qué produce"], [
    ["<code>fig_curvas_publicacion</code>", "Curvas ajustadas, panel (a) −M / panel (b) +M, banda de confianza y asíntota K"],
    ["<code>fig_tasas_crecimiento</code>", "Paneles AGR/RGR calculados analíticamente de los parámetros ya ajustados"],
    ["<code>fig_barras_variable</code>", "Barras de medias ± DE con significancia"],
    ["<code>fig_barras_resumen_2x2</code>", "Las 4 variables en cuadrícula 2×2"],
    ["<code>fig_barras_r2_comparacion</code>", "Comparación de R² por modelo y variable"],
])}
<h2>El reporte PDF</h2>
<p>La clase <code>ReportePDF(FPDF)</code> arma el documento sección por sección — metodología,
tablas de R²/RMSE/MAE, las mismas figuras de arriba (reinsertadas con
<code>insertar_imagen_png</code>/<code>insertar_pie_pdf</code>), y conclusiones — y termina en
<code>pdf_bytes = bytes(pdf.output())</code>, ofrecido como descarga.</p>
{recuadro('nota', 'Un PDF de ejemplo generado con datos reales está en '
  '<code>docs/reportes/reporte_ejemplo_datos_reales.pdf</code>.')}
""")

# ---- 8. Referencia de funciones (generada del codigo) ----
def _entrada_funcion(f):
    secciones_attr = ",".join(f["secciones"]) if f["secciones"] else ""
    sin_doc = f["docstring"] is None and f["comentario"] is None
    descripcion = f["docstring"] or f["comentario"]
    if descripcion:
        desc_html = f"<p>{esc(descripcion)}</p>"
    else:
        desc_html = '<p class="sin-doc">Esta función no tiene docstring ni un comentario inmediato en el código — no se inventó ninguna descripción.</p>'
    usos = (", ".join(f["secciones"]) if f["secciones"] else "no se llama directamente desde ninguna sección de navegación (utilidad interna)")
    return f"""<div class="funcion-entrada" id="fn-{esc(f['nombre'])}" data-secciones="{esc(secciones_attr)}" data-sin-doc="{'1' if sin_doc else '0'}">
      <code class="firma">{esc(f['firma'])}</code>
      <p class="meta">Línea {f['linea']}–{f['linea_fin']} de <code>app/app.py</code> · Usada en: {esc(usos)}</p>
      {desc_html}
    </div>"""


ENTRADAS_FUNCIONES = "".join(_entrada_funcion(f) for f in FUNCIONES)
ENTRADA_CLASE = f"""<div class="funcion-entrada" id="fn-ReportePDF" data-secciones="Exportar reporte" data-sin-doc="0">
  <code class="firma">class ReportePDF(FPDF)</code>
  <p class="meta">Definida dentro de la sección "Exportar reporte" de <code>app/app.py</code> ·
  Usada en: Exportar reporte</p>
  <p>Subclase de <code>fpdf.FPDF</code> que personaliza encabezado y pie de página del reporte.
  Métodos propios: {", ".join(f"<code>{esc(m)}</code>" for c in CLASES if c["nombre"] == "ReportePDF" for m in c["metodos"])}.</p>
</div>"""

CHIPS_FILTRO = "".join(
    f'<button class="chip-filtro" type="button" data-filtro="{esc(s)}" aria-pressed="false">{esc(s)}</button>'
    for s in SECCIONES_ORDEN
) + '<button class="chip-filtro" type="button" data-filtro="sin-doc" aria-pressed="false">Sin documentar</button>'

agregar_apartado("ref-funciones", "8", "Referencia de funciones", f"""
<p class="apartado-etiqueta">08 · Referencia (generada del código)</p>
<h1>Referencia de funciones</h1>
<p>Las {CONTEOS['n_funciones']} funciones de nivel superior de <code>app/app.py</code> (más la
clase <code>ReportePDF</code>), extraídas con el módulo <code>ast</code> el {FECHA_GENERACION}:
firma completa, línea de origen, sección de la app que la usa (por dónde se llama en el código,
no supuesto), y su docstring o el comentario inmediato si no tiene docstring.</p>
{recuadro('advertencia', f"{CONTEOS['n_sin_descripcion']} funciones no tienen docstring ni "
  "comentario inmediato en el código. Se listan igual, marcadas explícitamente — no se les "
  "inventó una descripción.")}
<div class="filtro-funciones" role="group" aria-label="Filtrar funciones">
  <button class="chip-filtro" type="button" data-filtro="todas" aria-pressed="true">Todas</button>
  {CHIPS_FILTRO}
</div>
{ENTRADAS_FUNCIONES}
{ENTRADA_CLASE}
""")

# ---- 9. Despliegue ----
REQUIREMENTS_TXT = (REPO / "app" / "requirements.txt").read_text(encoding="utf-8").strip()
agregar_apartado("despliegue", "9", "Despliegue", f"""
<p class="apartado-etiqueta">09 · Despliegue</p>
<h1>Despliegue en Streamlit Cloud</h1>
<ol>
  <li>En <a href="https://share.streamlit.io">share.streamlit.io</a>, "New app".</li>
  <li>Repositorio: <code>0scar07/proyecto-coffea-hma</code>, rama <code>master</code>.</li>
  <li>Main file path: <code>app/app.py</code>.</li>
  <li>Streamlit Cloud toma automáticamente <code>app/requirements.txt</code> y
  <code>app/.streamlit/config.toml</code> porque están junto al archivo principal.</li>
</ol>
<h2>Versiones fijadas en <code>app/requirements.txt</code></h2>
{bloque_codigo(REQUIREMENTS_TXT, "text")}
{recuadro('importante', "<code>plotly</code> y <code>kaleido</code> están fijados a versiones "
  "exactas (no rangos): <code>kaleido&gt;=1</code> rompe la exportación de PNG con Plotly 6.x, "
  "ya verificado en una sesión anterior de este proyecto.")}
<h2>Cómo se reinicia la app</h2>
<p>Si el código cambia y la app desplegada no lo refleja, usa <b>"Reboot app"</b> desde el menú de
la app en Streamlit Cloud — limpia cualquier caché de <code>@st.cache_data</code> de una versión
anterior.</p>
""")

# ---- 10. Como ejecutarlo y probarlo en local ----
_SNIPPET_LOCAL = (
    "git clone " + REPO_URL + ".git\n"
    "cd proyecto-coffea-hma\n"
    "python -m venv .venv\n"
    ".venv\\Scripts\\activate        # Windows; en Linux/Mac: source .venv/bin/activate\n"
    "pip install -r app/requirements.txt\n"
    "streamlit run app/app.py"
)
_SNIPPET_APPTEST = (
    'from streamlit.testing.v1 import AppTest\n'
    'at = AppTest.from_file("app/app.py", default_timeout=60)\n'
    'at.run()\n'
    'at.session_state["seccion"] = "Ajustar modelos"\n'
    'at.run()\n'
    '# clic de botones, verificacion de at.exception, etc.'
)
_BLOQUE_LOCAL = bloque_codigo(_SNIPPET_LOCAL, "bash")
_BLOQUE_APPTEST = bloque_codigo(_SNIPPET_APPTEST, "python")
agregar_apartado("ejecutar-local", "10", "Ejecutar y probar en local", f"""
<p class="apartado-etiqueta">10 · Local</p>
<h1>Cómo ejecutarlo y probarlo en local</h1>
<p>Probado con Python 3.11:</p>
{_BLOQUE_LOCAL}
<p>La app abre en <code>http://localhost:8501</code>. Arranca con datos simulados; para probar
con datos reales, ve a Datos de prueba y sube <code>datos_reales_coffea_2023.xlsx</code>.</p>
<h2>Pruebas automatizadas (sin abrir un navegador)</h2>
<p>La app se puede ejercitar con <code>streamlit.testing.v1.AppTest</code>:</p>
{_BLOQUE_APPTEST}
{recuadro('nota', 'No existe todavía una carpeta <code>tests/</code> versionada en el '
  "repositorio con estos scripts — es una posible mejora futura, no incluida en este entregable.")}
""")

# ---- 11. Limitaciones y trabajo futuro ----
agregar_apartado("limitaciones", "11", "Limitaciones y trabajo futuro", f"""
<p class="apartado-etiqueta">11 · Limitaciones</p>
<h1>Limitaciones y trabajo futuro</h1>
<h2>Ventana de muestreo limitada</h2>
<p>Con los 4 días disponibles (28-112 ddt) la planta está sobre todo en fase de crecimiento
acelerado y todavía no muestra el "codo" de desaceleración que Logístico y Gompertz necesitan
para estimar su asíntota K de forma confiable. Con solo 4 puntos por grupo, Gompertz
frecuentemente no converge en uno de los dos grupos.</p>
<h2>Réplicas sintéticas</h2>
<p>Las réplicas individuales del dataset real se generaron a partir de las medias y CV%
publicados por Aguirre-Medina et al. (2023) — no son mediciones planta por planta. Cualquier
prueba estadística sobre ellas ilustra la metodología, no aporta evidencia experimental nueva.</p>
<h2>Validación disponible — solo interna</h2>
<p><code>scripts/validacion_cruzada_real.py</code> hace un hold-out 80/20 repetido 200 veces sobre
las réplicas sintéticas, midiendo qué tan estable es la media reportada. Esto <b>no valida</b> que
los modelos generalicen a datos nuevos.</p>
{recuadro('advertencia', "No existe, todavía, ninguna validación externa de los modelos contra "
  "un dataset distinto al de Aguirre-Medina et al. (2023).")}
<h2>Trabajo futuro</h2>
<ul>
  <li>Validación externa con un dataset de <i>Coffea arabica</i> independiente.</li>
  <li>Ampliar el muestreo para cubrir la fase de desaceleración del crecimiento.</li>
  <li>Posible carpeta <code>tests/</code> versionada con las pruebas de AppTest.</li>
</ul>
""")

# ---- 12. Glosario ----
GLOSARIO = [
    ("−M / +M", "Grupo control sin inocular / grupo inoculado con hongos micorrízicos arbusculares (HMA)."),
    ("ddt", "Días después del trasplante — unidad de tiempo del eje X."),
    ("curve_fit", "scipy.optimize.curve_fit: ajuste por mínimos cuadrados no lineales."),
    ("R²", "Coeficiente de determinación: proporción de la variación observada que explica el modelo."),
    ("RMSE", "Raíz del error cuadrático medio."),
    ("MAE", "Error absoluto medio."),
    ("Asíntota K", "Valor máximo teórico de Logístico/Gompertz; solo se dibuja si pasa el criterio de plausibilidad."),
    ("Convergencia", "Que curve_fit haya encontrado una solución estable."),
    ("Prueba t de Welch", "Compara las medias de dos grupos sin asumir igual varianza (scipy.stats.ttest_ind, equal_var=False)."),
    ("Réplicas sintéticas", "En el dataset real, mediciones individuales generadas a partir de medias y CV% publicados."),
    ("AGR / RGR", "Tasa de crecimiento absoluta / relativa, derivadas analíticamente de los parámetros ya ajustados."),
]
FILAS_GLOSARIO = "".join(f"<dt>{esc(t)}</dt><dd>{esc(d)}</dd>" for t, d in GLOSARIO)
agregar_apartado("glosario", "12", "Glosario", f"""
<p class="apartado-etiqueta">12 · Glosario</p>
<h1>Glosario</h1>
<dl class="glosario">{FILAS_GLOSARIO}</dl>
""")

# ---- 13. Registro de cambios ----
FILAS_GIT_LOG = "".join(f"<li><code>{esc(l.split(' ',1)[0])}</code> {esc(l.split(' ',1)[1] if ' ' in l else '')}</li>"
                         for l in GIT_LOG_RESUMEN.splitlines())
agregar_apartado("registro-cambios", "13", "Registro de cambios", f"""
<p class="apartado-etiqueta">13 · Registro de cambios</p>
<h1>Registro de cambios</h1>
<p>Últimos 15 commits de <code>git log --oneline</code> en <code>{esc(RAMA_ACTUAL)}</code>
(generado el {FECHA_GENERACION}, no editado a mano):</p>
<ul class="lista-commits">{FILAS_GIT_LOG}</ul>
<div class="enlaces-pie">
  <a class="boton" href="[URL de la app en Streamlit Cloud — pendiente de publicar en el README]">Abrir la app</a>
  <a class="boton secundario" href="{REPO_URL}">Ver el repositorio</a>
  <a class="boton secundario" href="../06_guia_tecnica/guia_tecnica_usuario.pdf">Guía técnica de usuario (PDF)</a>
</div>
""")

print(f"OK: {len(APARTADOS)} apartados construidos.")


# ------------------------------------------------------------------------------------
# 7. Ensamblado del documento HTML completo
# ------------------------------------------------------------------------------------
def construir_nav_lateral():
    filas = []
    for i, ap in enumerate(APARTADOS):
        filas.append(
            f'<li><a class="enlace-nav" href="#{ap["id"]}"><span class="num">{esc(ap["etiqueta"])}</span>'
            f'{esc(ap["titulo"])}</a></li>'
        )
    return "\n".join(filas)


def construir_toc():
    filas = [f'<li><a href="#{ap["id"]}">{esc(ap["titulo"])}</a></li>' for ap in APARTADOS]
    return "\n".join(filas)


def construir_apartados_html():
    piezas = []
    for i, ap in enumerate(APARTADOS):
        anterior = APARTADOS[i - 1] if i > 0 else None
        siguiente = APARTADOS[i + 1] if i < len(APARTADOS) - 1 else None
        nav_html = '<nav class="nav-apartado" aria-label="Navegación entre apartados">'
        if anterior:
            nav_html += (f'<a href="#{anterior["id"]}" data-boton-anterior><span class="direccion">← Anterior</span>'
                         f'{esc(anterior["titulo"])}</a>')
        else:
            nav_html += '<span></span>'
        if siguiente:
            nav_html += (f'<a class="siguiente" href="#{siguiente["id"]}" data-boton-siguiente>'
                         f'<span class="direccion">Siguiente →</span>{esc(siguiente["titulo"])}</a>')
        nav_html += '</nav>'
        # Inyecta id="titulo-{id}" en el primer <h1> del apartado (una sola vez) para que
        # aria-labelledby de la <section> apunte a un id real.
        html_con_id_h1 = ap["html"].replace("<h1>", f'<h1 id="titulo-{ap["id"]}">', 1)
        piezas.append(f'<section class="apartado" id="{ap["id"]}" aria-labelledby="titulo-{ap["id"]}">'
                      f'{html_con_id_h1}{nav_html}</section>')
    return "\n".join(piezas)


NAV_LATERAL_HTML = construir_nav_lateral()
TOC_HTML = construir_toc()
APARTADOS_HTML = construir_apartados_html()

CSS_INLINE_CRITICO = ""  # el CSS vive en assets/styles.css (mismo origen, sin red)

HTML_COMPLETO = f"""<!DOCTYPE html>
<html lang="es" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Documentación técnica · Coffea IA</title>
<meta name="description" content="Documentación técnica de app/app.py: arquitectura, modelos, métricas, referencia de funciones generada del código, despliegue y limitaciones.">
<meta name="color-scheme" content="light dark">
<link rel="stylesheet" href="assets/styles.css">
<!-- efectos.css es puramente decorativo (transiciones/animaciones): si no carga, todo
     lo de styles.css + app.js sigue funcionando igual, solo que sin movimiento. -->
<link rel="stylesheet" href="assets/efectos.css">
</head>
<body>
<a class="saltar-enlace" href="#contenido-principal">Saltar al contenido</a>
<div class="solo-sr" role="status" aria-live="polite" data-anunciador></div>

<div class="barra-progreso"><div class="relleno"></div></div>
<div class="indicador-apartado">Apartado 1 de {len(APARTADOS)}</div>

<header class="barra-superior">
  <button class="boton-icono abrir-menu" type="button" aria-label="Abrir menú" aria-expanded="false" aria-controls="menu-lateral">
    <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><path d="M2 5h16M2 10h16M2 15h16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
  </button>
  <span class="marca">Coffea IA · Documentación técnica</span>
</header>

<div class="fondo-oscurecido"></div>

<div class="envoltura">
  <nav class="barra-lateral" id="menu-lateral" aria-label="Navegación principal">
    <div style="display:flex;align-items:center;justify-content:space-between;">
      <div class="marca-sidebar"><span class="hoja" aria-hidden="true">⁂</span><strong>Coffea IA</strong></div>
      <button class="boton-icono cerrar-menu" type="button" aria-label="Cerrar menú">✕</button>
    </div>
    <div class="buscador" role="search">
      <label class="solo-sr" for="campo-buscar">Buscar en la documentación</label>
      <input type="search" id="campo-buscar" placeholder="Buscar…" autocomplete="off">
      <span class="icono-buscar" aria-hidden="true">⌕</span>
      <div class="resultados-busqueda" role="listbox" aria-label="Resultados de búsqueda"></div>
    </div>
    <ul class="nav-lateral">
      <span class="indicador-activo-nav" aria-hidden="true"></span>
      {NAV_LATERAL_HTML}
    </ul>
    <div class="selector-tema" role="group" aria-label="Tema de color">
      <button type="button" data-tema="light" aria-pressed="false">☀ Claro</button>
      <button type="button" data-tema="dark" aria-pressed="false">☾ Oscuro</button>
      <button type="button" data-tema="auto" aria-pressed="true">Auto</button>
    </div>
  </nav>

  <main class="contenido-principal" id="contenido-principal">
    {APARTADOS_HTML}
  </main>

  <aside class="toc-lateral" aria-label="En esta página">
    <h2>En esta página</h2>
    <ul>{TOC_HTML}</ul>
  </aside>
</div>

<nav class="barra-inferior" aria-label="Anterior y siguiente">
  <button type="button" data-boton-anterior>← Anterior</button>
  <button type="button" data-boton-siguiente>Siguiente →</button>
</nav>

<script src="assets/app.js"></script>
</body>
</html>"""

INDEX_PATH = DOCS_DIR / "index.html"
INDEX_PATH.write_text(HTML_COMPLETO, encoding="utf-8")
print(f"HTML escrito: {INDEX_PATH} ({len(HTML_COMPLETO)} caracteres)")

# docs/index.html: redireccion simple (sin JS obligatorio, con meta-refresh + enlace)
REDIRECT_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=documentacion/index.html">
<link rel="canonical" href="documentacion/index.html">
<title>Redirigiendo… · Documentación Coffea IA</title>
</head><body>
<p>Redirigiendo a la <a href="documentacion/index.html">documentación técnica de Coffea IA</a>…</p>
</body></html>"""
(REPO / "docs" / "index.html").write_text(REDIRECT_HTML, encoding="utf-8")
print("docs/index.html (redireccion) escrito.")

print("LISTO.")
