import csv

ARCHIVO = "gastos.csv"

gastos = []

with open(ARCHIVO, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for fila in reader:
        fila["cantidad"] = float(fila["cantidad"])
        gastos.append(fila)

while True:
    print("\n--- GESTOR DE GASTOS ---")
    print("1. Añadir gasto")
    print("2. Ver lista de gastos")
    print("3. Ver total por categoría")
    print("4. Salir")
    opcion = input("Elige una opción: ")

    if opcion == "1":
        descripcion = input("¿En qué has gastado? ")
        try:
            cantidad = float(input("¿Cuánto? "))
        except ValueError:
            print("Eso no es un número, prueba otra vez.")
            continue
        categoria = input("¿Categoría? (comida, ocio, transporte...) ").strip().lower()
        gasto = {"descripcion": descripcion, "cantidad": cantidad, "categoria": categoria}
        gastos.append(gasto)
        with open(ARCHIVO, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["descripcion", "cantidad", "categoria"])
            writer.writerow(gasto)
        print(f"Gasto guardado: {descripcion} - {cantidad} € ({categoria})")

    elif opcion == "2":
        if len(gastos) == 0:
            print("No hay gastos todavía.")
        else:
            print("Lista de gastos:")
            numero = 1
            for gasto in gastos:
                print(f"{numero}. {gasto['descripcion']} - {gasto['cantidad']} € ({gasto['categoria']})")
                numero += 1

    elif opcion == "3":
        totales = {}
        for gasto in gastos:
            cat = gasto["categoria"]
            if cat in totales:
                totales[cat] += gasto["cantidad"]
            else:
                totales[cat] = gasto["cantidad"]

        if len(totales) == 0:
            print("No hay gastos todavía.")
        else:
            print("Total por categoría:")
            for cat in totales:
                print(f"{cat}: {totales[cat]:.2f} €")

    elif opcion == "4":
        print("Saliendo del gestor de gastos...")
        break

    else:
        print("Opción no válida, prueba otra vez.")
