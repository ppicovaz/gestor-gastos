import csv
import math
import os
import shutil
from datetime import date, datetime

ARCHIVO = "gastos.csv"
CAMPOS = ["descripcion", "cantidad", "categoria", "fecha"]
DESCRIPCION_POR_DEFECTO = "sin descripción"
CATEGORIA_POR_DEFECTO = "otros"
SIN_FECHA = "sin fecha"


# ---------------------------------------------------------------------------
# Archivo CSV: cargar y guardar
# ---------------------------------------------------------------------------

def guardar_todos(gastos):
    """Reescribe el CSV entero con la lista actual de gastos."""
    with open(ARCHIVO, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(gastos)


def guardar_gasto(gasto):
    """Añade un solo gasto al final del CSV."""
    with open(ARCHIVO, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS)
        writer.writerow(gasto)


def hacer_copia_seguridad():
    """Copia el CSV actual a un archivo con fecha y hora y devuelve su nombre."""
    nombre = f"gastos_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    shutil.copy(ARCHIVO, nombre)
    return nombre


def limpiar_fila(fila):
    """Convierte una fila del CSV en un gasto válido.
    Devuelve (gasto, reparada) o lanza ValueError si la fila no se puede usar."""
    def texto(campo):
        return (fila.get(campo) or "").strip()

    cantidad = float(texto("cantidad").replace(",", "."))  # ValueError si no es número
    if not math.isfinite(cantidad) or cantidad <= 0:
        raise ValueError("cantidad no válida")

    reparada = False
    fecha = texto("fecha")
    if fecha == "" or fecha == SIN_FECHA:
        fecha = SIN_FECHA
    else:
        try:
            fecha = date.fromisoformat(fecha).isoformat()
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

    gastos = []
    descartadas = []   # números de línea que no se han podido leer
    reparadas = []     # números de línea con la fecha corregida

    try:
        # "utf-8-sig" quita el BOM que añade Excel al principio del archivo
        with open(ARCHIVO, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            cabecera_vieja = reader.fieldnames != CAMPOS
            for fila in reader:
                try:
                    gasto, reparada = limpiar_fila(fila)
                    gastos.append(gasto)
                    if reparada:
                        reparadas.append(reader.line_num)
                except ValueError:
                    descartadas.append(reader.line_num)
    except (UnicodeDecodeError, csv.Error) as error:
        copia = hacer_copia_seguridad()
        print(f"\n⚠️  No se ha podido leer {ARCHIVO} ({error}).")
        print(f"   Se ha guardado una copia en {copia} y se empieza con la lista vacía.")
        guardar_todos([])
        return []

    if descartadas or reparadas:
        copia = hacer_copia_seguridad()
        print(f"\n⚠️  {ARCHIVO} tenía filas con problemas. Copia del original en {copia}.")
        if descartadas:
            print(f"   Filas descartadas (cantidad no válida): líneas {', '.join(map(str, descartadas))}")
        if reparadas:
            print(f"   Fechas no válidas cambiadas a '{SIN_FECHA}': líneas {', '.join(map(str, reparadas))}")
        guardar_todos(gastos)
    elif cabecera_vieja:
        # El CSV tenía la cabecera antigua (sin fecha): lo reescribimos con la nueva
        guardar_todos(gastos)

    return gastos


# ---------------------------------------------------------------------------
# Pedir datos al usuario
# ---------------------------------------------------------------------------

def pedir_cantidad(mensaje, permitir_vacio=False):
    """Pide una cantidad válida (> 0). Si permitir_vacio, Enter devuelve None."""
    while True:
        texto = input(mensaje).strip().replace(",", ".")
        if permitir_vacio and texto == "":
            return None
        try:
            cantidad = float(texto)
            if not math.isfinite(cantidad):
                print("Eso no es un número válido, prueba otra vez.")
            elif cantidad <= 0:
                print("La cantidad tiene que ser mayor que 0.")
            else:
                return cantidad
        except ValueError:
            print("Eso no es un número, prueba otra vez.")


def pedir_fecha(mensaje):
    """Pide una fecha AAAA-MM-DD. Enter devuelve None."""
    while True:
        texto = input(mensaje).strip()
        if texto == "":
            return None
        try:
            return date.fromisoformat(texto).isoformat()
        except ValueError:
            print("Fecha no válida. Usa el formato AAAA-MM-DD, por ejemplo 2026-11-18.")


def elegir_de_lista(cantidad_opciones, mensaje):
    """Pide un número entre 1 y cantidad_opciones.
    Si es válido devuelve el índice (int, desde 0); si no, el texto escrito (str)."""
    elegido = input(mensaje).strip()
    # isdecimal() y no isdigit(): "²".isdigit() es True pero int("²") falla
    if elegido.isdecimal() and 1 <= int(elegido) <= cantidad_opciones:
        return int(elegido) - 1
    return elegido  # devolvemos el texto para poder mostrarlo en el aviso


def elegir_gasto(gastos, accion):
    """Muestra la lista y devuelve el índice del gasto elegido, o None."""
    if len(gastos) == 0:
        print("No hay gastos todavía.")
        return None
    mostrar_lista(gastos)
    elegido = elegir_de_lista(len(gastos), f"Número del gasto a {accion} (Enter para cancelar): ")
    if isinstance(elegido, int):
        return elegido
    if elegido == "":
        print("Cancelado.")
    else:
        print(f"⚠️  '{elegido}' no es un número de gasto válido.")
    return None


# ---------------------------------------------------------------------------
# Mostrar y calcular
# ---------------------------------------------------------------------------

def formatear_gasto(gasto):
    return f"[{gasto['fecha']}] {gasto['descripcion']} - {gasto['cantidad']:.2f} € ({gasto['categoria']})"


def mostrar_lista(gastos):
    for numero, gasto in enumerate(gastos, start=1):
        print(f"{numero}. {formatear_gasto(gasto)}")


def totales_por_categoria(gastos):
    """Devuelve un diccionario {categoria: total}."""
    totales = {}
    for gasto in gastos:
        cat = gasto["categoria"]
        totales[cat] = totales.get(cat, 0) + gasto["cantidad"]
    return totales


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
    gasto = {
        "descripcion": descripcion,
        "cantidad": cantidad,
        "categoria": categoria,
        "fecha": date.today().isoformat(),
    }
    gastos.append(gasto)
    guardar_gasto(gasto)
    print(f"Gasto guardado: {descripcion} - {cantidad:.2f} € ({categoria})")


def ver_lista(gastos):
    if len(gastos) == 0:
        print("No hay gastos todavía.")
    else:
        print("Lista de gastos:")
        mostrar_lista(gastos)


def ver_total_por_categoria(gastos):
    totales = totales_por_categoria(gastos)
    if len(totales) == 0:
        print("No hay gastos todavía.")
    else:
        print("Total por categoría:")
        for cat, total in totales.items():
            print(f"{cat}: {total:.2f} €")


def ver_por_mes(gastos):
    por_mes = agrupar_por_mes(gastos)
    if len(por_mes) == 0:
        print("No hay gastos todavía.")
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
        elegido = elegir_de_lista(len(meses), "Elige el número del mes: ")
        if isinstance(elegido, int):
            meses_a_ver = [meses[elegido]]
        else:
            print(f"⚠️  '{elegido}' no es un mes válido.")
            meses_a_ver = []
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
# Menú principal
# ---------------------------------------------------------------------------

# Cada opción: (número, texto del menú, función que la ejecuta)
OPCIONES = [
    ("1", "Añadir gasto", anadir_gasto),
    ("2", "Ver lista de gastos", ver_lista),
    ("3", "Ver total por categoría", ver_total_por_categoria),
    ("4", "Ver gastos por mes", ver_por_mes),
    ("5", "Editar un gasto", editar_gasto),
    ("6", "Borrar un gasto", borrar_gasto),
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
    main()
