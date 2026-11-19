import csv
import math
import os
import re
import shutil
from datetime import date, datetime

# matplotlib es opcional: si no está instalado, el resto del programa funciona igual
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

# Todo se guarda junto a main.py, se ejecute desde la carpeta que se ejecute
CARPETA = os.path.dirname(os.path.abspath(__file__))
NOMBRE_ARCHIVO = "gastos.csv"
ARCHIVO = os.path.join(CARPETA, NOMBRE_ARCHIVO)
CAMPOS = ["descripcion", "cantidad", "categoria", "fecha"]

DESCRIPCION_POR_DEFECTO = "sin descripción"
CATEGORIA_POR_DEFECTO = "otros"
SIN_FECHA = "sin fecha"
SIN_GASTOS = "No hay gastos todavía."
CANTIDAD_GRANDE = 10_000  # a partir de aquí se pide confirmación

# Gráficos
UMBRAL_OTROS = 0.05  # en la tarta, las categorías por debajo del 5 % van a "otros"


# ---------------------------------------------------------------------------
# Archivo CSV: cargar y guardar
# ---------------------------------------------------------------------------

def guardar_todos(gastos):
    """Reescribe el CSV entero con la lista actual de gastos.
    Escribe primero en un archivo temporal y luego lo cambia por el bueno,
    así si el programa se corta a mitad el CSV original queda intacto."""
    temporal = ARCHIVO + ".tmp"
    # "utf-8-sig" añade al principio una marca (BOM) que le dice a Excel que es UTF-8;
    # sin ella Excel enseña las tildes mal ("descripciÃ³n")
    with open(temporal, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(gastos)
    os.replace(temporal, ARCHIVO)


def hacer_copia_seguridad():
    """Copia el CSV actual a un archivo con fecha y hora y devuelve su nombre."""
    nombre = f"gastos_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    shutil.copy(ARCHIVO, os.path.join(CARPETA, nombre))
    return nombre


def a_numero(texto):
    """Convierte "12.5", "12,5", "1.500" o "1.234,56" en float. Lanza ValueError si no es un número."""
    texto = texto.strip()
    if "," in texto:
        # Formato español: el punto separa miles y la coma los decimales
        texto = texto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", texto):
        # "1.500" o "12.000": puntos de miles. No pueden ser decimales porque
        # en euros nunca hay 3 decimales
        texto = texto.replace(".", "")
    return float(texto)


def a_fecha(texto):
    """Convierte "2026-11-18" o "18/11/2026" (como la guarda Excel) en "2026-11-18".
    Lanza ValueError si no es una fecha válida."""
    try:
        return date.fromisoformat(texto).isoformat()
    except ValueError:
        return datetime.strptime(texto, "%d/%m/%Y").date().isoformat()


def limpiar_fila(fila):
    """Convierte una fila del CSV en un gasto válido.
    Devuelve (gasto, reparada) o lanza ValueError si la fila no se puede usar."""
    def texto(campo):
        return (fila.get(campo) or "").strip()

    cantidad = round(a_numero(texto("cantidad")), 2)  # ValueError si no es número
    if not math.isfinite(cantidad) or cantidad <= 0:
        raise ValueError("cantidad no válida")

    reparada = False
    fecha = texto("fecha")
    if fecha == "" or fecha == SIN_FECHA:
        fecha = SIN_FECHA
    else:
        try:
            fecha = a_fecha(fecha)
        except ValueError:
            fecha = SIN_FECHA
            reparada = True

    gasto = {
        "descripcion": texto("descripcion") or DESCRIPCION_POR_DEFECTO,
        "cantidad": cantidad,
        "categoria": texto("categoria").lower() or CATEGORIA_POR_DEFECTO,
        "fecha": fecha,
    }
    return gasto, reparada


def cargar_gastos():
    """Lee el CSV sin romperse si está dañado. Devuelve la lista de gastos."""
    if not os.path.exists(ARCHIVO):
        guardar_todos([])
        return []

    try:
        try:
            # "utf-8-sig" quita el BOM del principio del archivo si lo tiene
            gastos, descartadas, reparadas, separador = leer_csv("utf-8-sig")
            codificacion = "utf-8"
        except UnicodeDecodeError:
            # Excel en español suele guardar en "ANSI" (cp1252), no en UTF-8
            gastos, descartadas, reparadas, separador = leer_csv("cp1252")
            codificacion = "cp1252"
    except (UnicodeDecodeError, csv.Error) as error:
        copia = hacer_copia_seguridad()
        print(f"\n⚠️  No se ha podido leer {NOMBRE_ARCHIVO} ({error}).")
        print(f"   Se ha guardado una copia en {copia} y se empieza con la lista vacía.")
        guardar_todos([])
        return []

    if descartadas or reparadas:
        copia = hacer_copia_seguridad()
        print(f"\n⚠️  {NOMBRE_ARCHIVO} tenía filas con problemas. Copia del original en {copia}.")
        if descartadas:
            print(f"   Filas descartadas (cantidad no válida): líneas {', '.join(map(str, descartadas))}")
        if reparadas:
            print(f"   Fechas no válidas cambiadas a '{SIN_FECHA}': líneas {', '.join(map(str, reparadas))}")

    if separador != ",":
        print(f"\nℹ️  {NOMBRE_ARCHIVO} estaba separado por ';' (Excel). Se ha convertido a comas.")
    if codificacion != "utf-8":
        print(f"\nℹ️  {NOMBRE_ARCHIVO} estaba guardado en ANSI (Excel). Se ha convertido a UTF-8.")

    # Se vuelve a guardar siempre en el formato normal (comas, UTF-8, fechas
    # AAAA-MM-DD, cantidades con punto), por si Excel lo había cambiado
    guardar_todos(gastos)
    return gastos


def leer_csv(codificacion):
    """Lee el CSV con la codificación indicada.
    Devuelve (gastos, líneas descartadas, líneas reparadas, separador).
    Lanza UnicodeDecodeError si la codificación no es la del archivo."""
    gastos = []
    descartadas = []   # números de línea que no se han podido leer
    reparadas = []     # números de línea con la fecha corregida

    with open(ARCHIVO, "r", newline="", encoding=codificacion) as f:
        # Excel en español separa las columnas con ";" en vez de ","
        separador = ";" if ";" in f.readline() else ","
        f.seek(0)
        reader = csv.DictReader(f, delimiter=separador)
        for fila in reader:
            try:
                gasto, reparada = limpiar_fila(fila)
                gastos.append(gasto)
                if reparada:
                    reparadas.append(reader.line_num)
            except ValueError:
                descartadas.append(reader.line_num)

    return gastos, descartadas, reparadas, separador


# ---------------------------------------------------------------------------
# Pedir datos al usuario
# ---------------------------------------------------------------------------

def pedir_cantidad(mensaje, permitir_vacio=False):
    """Pide una cantidad válida (> 0, con 2 decimales). Si permitir_vacio, Enter devuelve None."""
    while True:
        texto = input(mensaje).strip()
        if permitir_vacio and texto == "":
            return None
        try:
            cantidad = round(a_numero(texto), 2)
        except ValueError:
            print("Eso no es un número, prueba otra vez.")
            continue

        if not math.isfinite(cantidad):
            print("Eso no es un número válido, prueba otra vez.")
        elif cantidad <= 0:
            print("La cantidad tiene que ser mayor que 0.")
        elif cantidad >= CANTIDAD_GRANDE:
            confirmar = input(f"¿Seguro que son {cantidad:.2f} €? (s/n): ").strip().lower()
            if confirmar == "s":
                return cantidad
        else:
            return cantidad


def pedir_fecha(mensaje):
    """Pide una fecha AAAA-MM-DD o DD/MM/AAAA. Enter devuelve None."""
    while True:
        texto = input(mensaje).strip()
        if texto == "":
            return None
        try:
            return a_fecha(texto)
        except ValueError:
            print("Fecha no válida. Usa AAAA-MM-DD o DD/MM/AAAA, por ejemplo 2026-11-18 o 18/11/2026.")


def elegir_de_lista(cantidad_opciones, mensaje):
    """Pide un número entre 1 y cantidad_opciones.
    Devuelve el índice (desde 0), o None si se cancela o no es válido (ya avisa él)."""
    elegido = input(mensaje).strip()
    # isdecimal() y no isdigit(): "²".isdigit() es True pero int("²") falla
    if elegido.isdecimal() and 1 <= int(elegido) <= cantidad_opciones:
        return int(elegido) - 1
    if elegido == "":
        print("Cancelado.")
    else:
        print(f"⚠️  '{elegido}' no es un número válido.")
    return None


def elegir_gasto(gastos, accion):
    """Muestra la lista y devuelve el índice del gasto elegido, o None."""
    if len(gastos) == 0:
        print(SIN_GASTOS)
        return None
    mostrar_lista(gastos)
    return elegir_de_lista(len(gastos), f"Número del gasto a {accion} (Enter para cancelar): ")


# ---------------------------------------------------------------------------
# Mostrar y calcular
# ---------------------------------------------------------------------------

def formatear_gasto(gasto):
    return f"[{gasto['fecha']}] {gasto['descripcion']} - {gasto['cantidad']:.2f} € ({gasto['categoria']})"


def mostrar_lista(gastos):
    for numero, gasto in enumerate(gastos, start=1):
        print(f"{numero}. {formatear_gasto(gasto)}")


def totales_por_categoria(gastos):
    """Devuelve un diccionario {categoria: total} ordenado de mayor a menor."""
    totales = {}
    for gasto in gastos:
        cat = gasto["categoria"]
        totales[cat] = totales.get(cat, 0) + gasto["cantidad"]
    return dict(sorted(totales.items(), key=lambda par: par[1], reverse=True))


def agrupar_por_mes(gastos):
    """Devuelve un diccionario {"AAAA-MM": [gastos]} ("sin fecha" aparte)."""
    por_mes = {}
    for gasto in gastos:
        if gasto["fecha"] == SIN_FECHA:
            mes = SIN_FECHA
        else:
            mes = gasto["fecha"][:7]  # los 7 primeros caracteres: "AAAA-MM"
        por_mes.setdefault(mes, []).append(gasto)
    return por_mes


def ordenar_meses(por_mes):
    """Meses del más antiguo al más reciente, con "sin fecha" al final."""
    meses = sorted(m for m in por_mes if m != SIN_FECHA)
    if SIN_FECHA in por_mes:
        meses.append(SIN_FECHA)
    return meses


def mes_actual_y_anterior():
    """Devuelve ("AAAA-MM" de este mes, "AAAA-MM" del mes anterior)."""
    hoy = date.today()
    actual = f"{hoy.year}-{hoy.month:02d}"
    if hoy.month == 1:
        anterior = f"{hoy.year - 1}-12"
    else:
        anterior = f"{hoy.year}-{hoy.month - 1:02d}"
    return actual, anterior


def mostrar_mes(mes, gastos_del_mes):
    total = sum(g["cantidad"] for g in gastos_del_mes)
    print(f"\n📅 {mes} — Total: {total:.2f} €")
    for g in gastos_del_mes:
        print(f"   - {formatear_gasto(g)}")


# ---------------------------------------------------------------------------
# Opciones del menú
# ---------------------------------------------------------------------------

def anadir_gasto(gastos):
    descripcion = input("¿En qué has gastado? ").strip() or DESCRIPCION_POR_DEFECTO
    cantidad = pedir_cantidad("¿Cuánto? ")
    categoria = input(f"¿Categoría? (comida, ocio, transporte...) [Enter = {CATEGORIA_POR_DEFECTO}] ").strip().lower() or CATEGORIA_POR_DEFECTO
    fecha = pedir_fecha("¿Fecha? (AAAA-MM-DD o DD/MM/AAAA) [Enter = hoy] ") or date.today().isoformat()
    gasto = {
        "descripcion": descripcion,
        "cantidad": cantidad,
        "categoria": categoria,
        "fecha": fecha,
    }
    gastos.append(gasto)
    # Se reescribe el archivo entero: así nunca se pega a una última línea sin salto
    # ni se queda sin cabecera si alguien ha borrado el CSV con el programa abierto
    guardar_todos(gastos)
    print(f"Gasto guardado: {formatear_gasto(gasto)}")


def ver_lista(gastos):
    if len(gastos) == 0:
        print(SIN_GASTOS)
    else:
        print("Lista de gastos:")
        mostrar_lista(gastos)


def ver_total_por_categoria(gastos):
    totales = totales_por_categoria(gastos)
    if len(totales) == 0:
        print(SIN_GASTOS)
        return
    total_general = sum(totales.values())
    print("Total por categoría:")
    for cat, total in totales.items():
        print(f"{cat}: {total:.2f} € ({total / total_general:.0%})")
    print(f"TOTAL: {total_general:.2f} €")


def ver_por_mes(gastos):
    por_mes = agrupar_por_mes(gastos)
    if len(por_mes) == 0:
        print(SIN_GASTOS)
        return

    meses = ordenar_meses(por_mes)
    mes_actual, mes_anterior = mes_actual_y_anterior()

    print("\n¿Qué mes quieres ver?")
    print(f"1. Mes actual ({mes_actual})")
    print(f"2. Mes anterior ({mes_anterior})")
    print("3. Elegir un mes concreto")
    print("4. Ver todos los meses")
    eleccion = input("Elige una opción: ").strip()

    if eleccion == "1":
        meses_a_ver = [mes_actual]
    elif eleccion == "2":
        meses_a_ver = [mes_anterior]
    elif eleccion == "3":
        print("Meses con gastos:")
        for i, m in enumerate(meses, start=1):
            print(f"{i}. {m}")
        elegido = elegir_de_lista(len(meses), "Elige el número del mes (Enter para cancelar): ")
        meses_a_ver = [] if elegido is None else [meses[elegido]]
    elif eleccion == "4":
        meses_a_ver = meses
    else:
        print(f"⚠️  '{eleccion}' no es una opción válida.")
        meses_a_ver = []

    for mes in meses_a_ver:
        if mes in por_mes:
            mostrar_mes(mes, por_mes[mes])
        else:
            print(f"\nNo hay gastos en {mes}.")


def editar_gasto(gastos):
    indice = elegir_gasto(gastos, "editar")
    if indice is None:
        return
    gasto = gastos[indice]
    print("Pulsa Enter para dejar un campo como está.")

    nueva_desc = input(f"Descripción [{gasto['descripcion']}]: ").strip()
    if nueva_desc:
        gasto["descripcion"] = nueva_desc

    nueva_cantidad = pedir_cantidad(f"Cantidad [{gasto['cantidad']:.2f}]: ", permitir_vacio=True)
    if nueva_cantidad is not None:
        gasto["cantidad"] = nueva_cantidad

    nueva_cat = input(f"Categoría [{gasto['categoria']}]: ").strip().lower()
    if nueva_cat:
        gasto["categoria"] = nueva_cat

    nueva_fecha = pedir_fecha(f"Fecha AAAA-MM-DD [{gasto['fecha']}]: ")
    if nueva_fecha is not None:
        gasto["fecha"] = nueva_fecha

    guardar_todos(gastos)
    print(f"Gasto actualizado: {formatear_gasto(gasto)}")


def borrar_gasto(gastos):
    indice = elegir_gasto(gastos, "borrar")
    if indice is None:
        return
    gasto = gastos[indice]
    confirmar = input(f"¿Seguro que quieres borrar '{gasto['descripcion']}' ({gasto['cantidad']:.2f} €)? (s/n): ").strip().lower()
    if confirmar == "s":
        gastos.pop(indice)
        guardar_todos(gastos)
        print("Gasto borrado.")
    else:
        print("No se ha borrado nada.")


# ---------------------------------------------------------------------------
# Gráficos (necesitan matplotlib)
# ---------------------------------------------------------------------------

def matplotlib_disponible():
    if plt is None:
        print("\n⚠️  Para ver gráficos hace falta instalar matplotlib.")
        print("   Instálalo con:  pip install matplotlib")
        print("   y vuelve a abrir el programa.")
        return False
    return True


def agrupar_pequenas(totales, umbral=UMBRAL_OTROS):
    """Junta en "otros" las categorías que no llegan al umbral del total.
    Devuelve un diccionario nuevo ordenado de mayor a menor."""
    total = sum(totales.values())
    agrupado = {}
    for cat, cantidad in totales.items():
        destino = cat if cantidad / total >= umbral else CATEGORIA_POR_DEFECTO
        agrupado[destino] = agrupado.get(destino, 0) + cantidad
    if len(agrupado) == 1 and len(totales) > 1:
        # Todas eran pequeñas: agruparlas daría una tarta de un solo color
        agrupado = totales
    return dict(sorted(agrupado.items(), key=lambda par: par[1], reverse=True))


NOMBRES_MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
                 "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def nombre_mes(clave):
    """Convierte "2026-08" en "Agosto 2026"."""
    anio, mes = clave.split("-")
    return f"{NOMBRES_MESES[int(mes) - 1]} {anio}"


def totales_por_mes(gastos):
    """Devuelve ({"AAAA-MM": total} en orden cronológico, nº de gastos sin fecha)."""
    por_mes = agrupar_por_mes(gastos)
    sin_fecha = len(por_mes.pop(SIN_FECHA, []))
    totales = {mes: sum(g["cantidad"] for g in por_mes[mes]) for mes in sorted(por_mes)}
    return totales, sin_fecha


def mostrar_o_guardar(fig, nombre_base):
    """Pregunta si mostrar el gráfico, guardarlo como PNG o las dos cosas."""
    print("\n¿Qué quieres hacer con el gráfico?")
    print("1. Mostrarlo")
    print("2. Guardarlo como PNG")
    print("3. Guardarlo y mostrarlo")
    eleccion = input("Elige una opción [Enter = 1]: ").strip() or "1"

    if eleccion not in ("1", "2", "3"):
        print(f"⚠️  '{eleccion}' no es una opción válida.")
        plt.close(fig)
        return

    if eleccion in ("2", "3"):
        archivo = f"{nombre_base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        fig.savefig(os.path.join(CARPETA, archivo), dpi=150, bbox_inches="tight")
        print(f"Gráfico guardado en {archivo}")

    if eleccion in ("1", "3"):
        print("ℹ️  Se va a abrir el gráfico. Cierra la ventana para volver al menú.")
        plt.show()  # se queda esperando hasta que se cierra la ventana
    plt.close(fig)


def grafico_categorias(gastos):
    if not matplotlib_disponible():
        return
    if len(gastos) == 0:
        print(SIN_GASTOS)
        return

    totales = agrupar_pequenas(totales_por_categoria(gastos))
    total = sum(totales.values())

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(totales.values(), labels=totales.keys(), autopct="%1.1f%%", startangle=90, counterclock=False)
    ax.set_title(f"Gastos por categoría (total: {total:.2f} €)", pad=25)
    ax.axis("equal")  # para que la tarta sea redonda
    mostrar_o_guardar(fig, "grafico_categorias")


def grafico_meses(gastos):
    if not matplotlib_disponible():
        return
    if len(gastos) == 0:
        print(SIN_GASTOS)
        return

    totales, sin_fecha = totales_por_mes(gastos)
    if sin_fecha:
        print(f"⚠️  {sin_fecha} gasto(s) '{SIN_FECHA}' se han quedado fuera del gráfico.")
    if len(totales) == 0:
        print("Ningún gasto tiene fecha, no se puede hacer el gráfico por mes.")
        return

    # "2026-08" -> "Agosto\n2026" (el año debajo para que no se pisen las etiquetas)
    meses = [nombre_mes(m).replace(" ", "\n") for m in totales]
    cantidades = list(totales.values())

    fig, ax = plt.subplots(figsize=(max(6, len(meses) * 1.2), 5))
    barras = ax.bar(meses, cantidades)
    ax.bar_label(barras, labels=[f"{c:.2f} €" for c in cantidades], padding=3)
    ax.set_title("Gastos por mes")
    ax.set_xlabel("Mes")
    ax.set_ylabel("Euros")
    ax.margins(y=0.15)  # deja hueco arriba para las etiquetas
    if len(meses) > 6:
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()
    mostrar_o_guardar(fig, "grafico_meses")


# ---------------------------------------------------------------------------
# Menú principal
# ---------------------------------------------------------------------------

# Cada opción: (número, texto del menú, función que la ejecuta)
OPCIONES = [
    ("1", "Añadir gasto", anadir_gasto),
    ("2", "Ver lista de gastos", ver_lista),
    ("3", "Ver total por categoría", ver_total_por_categoria),
    ("4", "Ver gastos por mes", ver_por_mes),
    ("5", "Gráfico de tarta por categorías", grafico_categorias),
    ("6", "Gráfico de barras por mes", grafico_meses),
    ("7", "Editar un gasto", editar_gasto),
    ("8", "Borrar un gasto", borrar_gasto),
]
OPCION_SALIR = str(len(OPCIONES) + 1)


def mostrar_menu():
    print("\n--- GESTOR DE GASTOS ---")
    for numero, texto, _ in OPCIONES:
        print(f"{numero}. {texto}")
    print(f"{OPCION_SALIR}. Salir")


def main():
    gastos = cargar_gastos()
    acciones = {numero: funcion for numero, _, funcion in OPCIONES}

    while True:
        mostrar_menu()
        opcion = input("Elige una opción: ").strip()

        if opcion == OPCION_SALIR:
            print("Saliendo del gestor de gastos...")
            break
        elif opcion in acciones:
            acciones[opcion](gastos)
        else:
            print(f"\n⚠️  '{opcion}' no es una opción válida. Elige un número del 1 al {OPCION_SALIR}.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C o Ctrl+D/Ctrl+Z: salir sin traceback (lo ya guardado no se pierde)
        print("\nSaliendo del gestor de gastos...")
