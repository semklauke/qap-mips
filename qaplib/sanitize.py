import sys

def correct_matrix_file(filename):
    with open(filename, 'r') as file:
        lines = file.readlines()

    # Die erste Zeile enthält die erwartete Anzahl an Einträgen
    N = int(lines[0].strip())

    corrected_lines = []

    current_group = []

    for line in lines[2:]:  # Überspringe die erste Zeile
        stripped_line = line.strip()
        if stripped_line:  # Überprüfen, ob die Zeile nicht leer ist
            current_group += stripped_line.split()

            # Wenn wir genug Zeilen gesammelt haben, um eine vollständige Zeile zu bilden
            if len(current_group) == N:
                # Verbinde die gesammelten Zeilen und füge sie zur Liste der korrigierten Linien hinzu
                corrected_lines.append(' '.join(current_group))
                current_group = []  # Zurücksetzen für die nächste Gruppe
        else:
            corrected_lines.append("")

    # Falls noch eine unvollständige Gruppe vorhanden ist (z.B. am Ende der Datei)
    if current_group:
        print(f"Warnung: Unvollständige Gruppe gefunden: {current_group}")

    with open(filename, 'w') as file:
        file.write(f"{N}\n\n")
        file.write('\n'.join(corrected_lines))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Verwendung: python script.py <dateiname>")
        sys.exit(1)

    filename = sys.argv[1]
    correct_matrix_file(filename)