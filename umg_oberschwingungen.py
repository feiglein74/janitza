#!/usr/bin/env python3
"""Liest die Oberschwingungsanalyse des UMG 96RM aus.

Das Geraet fuehrt eine Fourieranalyse bis zur 40. Ordnung durch, fuer drei
Phasenspannungen, drei Aussenleiterspannungen und drei Stroeme.

Achtung bei der Zaehlweise: Der Index laeuft ab null, die Ordnung ab eins.
Index 0 ist die Grundschwingung, nicht die zweite Harmonische.

    Adresse = 1000 + 80 * Kanal + 2 * (Ordnung - 1)

Verwendung:

    python3 umg_oberschwingungen.py                    # I L1 und U L1-N
    python3 umg_oberschwingungen.py -k i_l1            # nur ein Kanal
    python3 umg_oberschwingungen.py -n 40              # bis zur 40. Ordnung
    python3 umg_oberschwingungen.py --json spektrum.json
    python3 umg_oberschwingungen.py --csv spektrum.csv

Die berechnete Klirrfaktorsumme wird gegen die THD-Register des Geraets
geprueft; stimmen beide ueberein, ist die Adressierung bestaetigt.
"""

import argparse
import csv
import json
import math
import struct
import sys

import serial

from umg_read import PORT, SLAVE, BAUD, read_input_registers

# Kanalname -> (Index im Block, Beschriftung, Einheit, THD-Register)
KANAELE = {
    "u_l1n":  (0, "U L1-N", "V", 836),
    "u_l2n":  (1, "U L2-N", "V", 838),
    "u_l3n":  (2, "U L3-N", "V", 840),
    "u_l1l2": (3, "U L1-L2", "V", 842),
    "u_l2l3": (4, "U L2-L3", "V", 844),
    "u_l3l1": (5, "U L3-L1", "V", 846),
    "i_l1":   (6, "I L1", "A", 908),
    "i_l2":   (7, "I L2", "A", 910),
    "i_l3":   (8, "I L3", "A", 912),
}

BASIS = 1000            # Anfang des Float-Blocks
KANAL_SCHRITT = 80      # Register je Kanal (40 Ordnungen a 2)
MAX_ORDNUNG = 40


def lies_kanal(ser, kanal, ordnungen):
    """Liest die ersten `ordnungen` Ordnungen eines Kanals."""
    start = BASIS + KANAL_SCHRITT * KANAELE[kanal][0]
    roh = read_input_registers(ser, SLAVE, start, ordnungen * 2)
    return [struct.unpack(">f", roh[i * 4:i * 4 + 4])[0]
            for i in range(ordnungen)]


def lies_thd(ser, kanal):
    roh = read_input_registers(ser, SLAVE, KANAELE[kanal][3], 2)
    return struct.unpack(">f", roh)[0]


def klirrfaktor(werte):
    """THD-F: Wurzel der Quadratsumme aller Oberschwingungen, bezogen auf
    die Grundschwingung. So rechnet auch das Geraet."""
    if not werte or werte[0] == 0:
        return 0.0
    return 100 * math.sqrt(sum(x * x for x in werte[1:])) / werte[0]


def zeige(kanal, voll, thd_geraet, ordnungen):
    """Zeigt `ordnungen` Ordnungen an; der Klirrfaktor wird immer ueber
    alle 40 gerechnet, sonst faellt die Pruefung falsch aus."""
    werte = voll[:ordnungen]
    _, label, einheit, _ = KANAELE[kanal]
    skal = 1000.0 if einheit == "A" else 1.0
    eskal = "mA" if einheit == "A" else einheit
    grund = werte[0]

    print("%s   Grundschwingung %.4f %s" % (label, grund * skal, eskal))
    print("  Ord.  %10s   %% Grund" % eskal)
    for k in range(ordnungen):
        anteil = 100 * werte[k] / grund if grund else 0.0
        balken = "#" * int(min(anteil, 150) / 3)
        marke = "  <- Grundschwingung" if k == 0 else ""
        print("  %3d.  %10.4f  %7.2f  %s%s"
              % (k + 1, werte[k] * skal, anteil, balken, marke))

    berechnet = klirrfaktor(voll)
    print()
    print("  THD aus Spektrum (alle %d Ordnungen): %8.2f %%"
          % (len(voll), berechnet))
    print("  THD aus Register:%*s %8.2f %%" % (len(str(len(voll))) + 15, "", thd_geraet))
    abw = abs(berechnet - thd_geraet)
    if abw < max(0.05, 0.005 * max(thd_geraet, 1)):
        print("  -> Adressierung bestaetigt")
    else:
        print("  -> ACHTUNG: Abweichung %.2f %% - Adressierung pruefen" % abw)
    print()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-k", "--kanal", action="append",
                   choices=sorted(KANAELE),
                   help="Kanal, mehrfach angebbar (Vorgabe: u_l1n und i_l1)")
    p.add_argument("-n", "--ordnungen", type=int, default=25,
                   help="hoechste dargestellte Ordnung, max %d (Vorgabe 25)"
                        % MAX_ORDNUNG)
    p.add_argument("--json", help="Spektrum zusaetzlich als JSON ablegen")
    p.add_argument("--csv", help="Spektrum zusaetzlich als CSV ablegen")
    args = p.parse_args()

    kanaele = args.kanal or ["u_l1n", "i_l1"]
    n = max(1, min(args.ordnungen, MAX_ORDNUNG))

    ergebnis = {}
    with serial.Serial(PORT, BAUD, timeout=1.0) as ser:
        for k in kanaele:
            # Fuer die Ablage immer alle 40 Ordnungen holen, angezeigt wird n
            voll = lies_kanal(ser, k, MAX_ORDNUNG)
            thd = lies_thd(ser, k)
            ergebnis[k] = {"label": KANAELE[k][1], "einheit": KANAELE[k][2],
                           "werte": voll, "thd_geraet": thd,
                           "thd_berechnet": klirrfaktor(voll)}
            zeige(k, voll, thd, n)

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(ergebnis, fh, indent=2)
        print("JSON: %s" % args.json)

    if args.csv:
        with open(args.csv, "w", newline="") as fh:
            s = csv.writer(fh)
            s.writerow(["ordnung"] + [ergebnis[k]["label"] for k in kanaele]
                       + ["%s_prozent" % ergebnis[k]["label"] for k in kanaele])
            for i in range(MAX_ORDNUNG):
                zeile = [i + 1]
                for k in kanaele:
                    zeile.append("%.6f" % ergebnis[k]["werte"][i])
                for k in kanaele:
                    g = ergebnis[k]["werte"][0]
                    zeile.append("%.3f" % (100 * ergebnis[k]["werte"][i] / g
                                           if g else 0))
                s.writerow(zeile)
        print("CSV: %s" % args.csv)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Fehler: %s" % exc, file=sys.stderr)
        sys.exit(1)
