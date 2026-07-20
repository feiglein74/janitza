#!/usr/bin/env python3
"""Zeichnet Messwerte eines Janitza UMG 96RM zyklisch als CSV auf.

Das Geraet bildet seine Effektivwerte ueber ein festes Fenster von 200 ms.
Deshalb wird mit 100 ms ueberabgetastet und jeder unveraenderte Block
verworfen - so wird jede Aktualisierung genau einmal aufgezeichnet, ohne
dass die Aufzeichnung mit dem internen Takt des Geraets synchron laufen
muss.

Zeitstempel kommen vom Rechner: das Grundgeraet hat keine Echtzeituhr.

Verwendung:
    python3 umg_log.py                          # nach stdout
    python3 umg_log.py -o messung.csv
    python3 umg_log.py -o messung.csv -d 3600   # eine Stunde lang
    python3 umg_log.py -o messung.csv --reset-minmax
"""

import argparse
import csv
import struct
import sys
import time
from datetime import datetime

import serial

from umg_read import PORT, SLAVE, BAUD, read_input_registers
from umg_param import read_holding, write_single

# Gelesen wird ein zusammenhaengender Block ab 19000.
BLOCK_START = 19000
BLOCK_COUNT = 122         # 19000 .. 19121, schliesst die THD-Werte ein
                          # (Modbus erlaubt max. 125 Register je Lesevorgang)

# Spaltenname -> Registeradresse (float32, Big Endian)
FELDER = [
    ("u_l1n", 19000),
    ("u_l2n", 19002),
    ("u_l3n", 19004),
    ("i_l1", 19012),
    ("i_l2", 19014),
    ("i_l3", 19016),
    ("p_l1", 19020),
    ("p_l2", 19022),
    ("p_l3", 19024),
    ("p_sum", 19026),
    ("s_sum", 19034),
    ("q_sum", 19042),
    ("cosphi_l1", 19044),
    ("frequenz", 19050),
    ("thd_u_l1", 19110),
    ("thd_i_l1", 19116),
    ("wh_gesamt", 19060),
    ("wh_bezogen", 19068),
    ("wh_geliefert", 19076),
]

# Zusaetzliche gerechnete Spalte. Der cosPhi auf 19044 ist der
# Verschiebungsfaktor der Grundschwingung; der echte Leistungsfaktor
# lambda = P/S beruecksichtigt zusaetzlich die Oberwellen. Bei nichtlinearen
# Lasten ohne PFC laufen die beiden weit auseinander.
BERECHNET = ["lambda_sum"]


def leistungsfaktor(werte):
    p, s = werte["p_sum"], werte["s_sum"]
    return p / s if abs(s) > 1e-9 else 0.0

# Min/Max-Register, am Ende einmalig gelesen (float32)
SPITZEN = [
    ("Maximalstrom L1", 3358, "A"),
    ("Maximalstrom L2", 3360, "A"),
    ("Maximalstrom L3", 3362, "A"),
    ("Max. Leistungsmittelwert", 3510, "W"),
]


def entpacke(roh, adresse):
    off = (adresse - BLOCK_START) * 2
    return struct.unpack(">f", roh[off:off + 4])[0]


def lies_spitzen(ser):
    werte = []
    for name, adr, einheit in SPITZEN:
        try:
            roh = read_input_registers(ser, SLAVE, adr, 2)
            werte.append((name, struct.unpack(">f", roh)[0], einheit))
        except IOError:
            pass
    return werte


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-o", "--output", help="CSV-Datei (Vorgabe: stdout)")
    p.add_argument("-i", "--interval", type=float, default=0.1,
                   help="Abtastintervall in Sekunden (Vorgabe 0.1)")
    p.add_argument("-d", "--duration", type=float,
                   help="Messdauer in Sekunden (Vorgabe: bis Strg-C)")
    p.add_argument("--heartbeat", type=float, default=60.0,
                   help="Auch unveraenderte Werte spaetestens alle N Sekunden "
                        "schreiben (Vorgabe 60)")
    p.add_argument("--no-dedup", action="store_true",
                   help="Jede Abtastung schreiben, auch unveraenderte")
    p.add_argument("--reset-minmax", action="store_true",
                   help="Min/Max-Werte im Geraet vor dem Start loeschen")
    args = p.parse_args()

    ziel = open(args.output, "w", newline="") if args.output else sys.stdout
    schreiber = csv.writer(ziel)
    schreiber.writerow(["zeit"] + [name for name, _ in FELDER] + BERECHNET)

    letzte_roh = None
    letzter_schreibzeitpunkt = 0.0
    zeilen = 0
    fehler = 0
    beginn = time.monotonic()

    with serial.Serial(PORT, BAUD, timeout=1.0) as ser:
        if args.reset_minmax:
            write_single(ser, SLAVE, 506, 1)
            print("Min/Max-Werte im Geraet geloescht.", file=sys.stderr)

        print("Aufzeichnung laeuft, Abbruch mit Strg-C.", file=sys.stderr)
        try:
            while True:
                runde = time.monotonic()
                if args.duration and runde - beginn >= args.duration:
                    break

                try:
                    roh = read_input_registers(ser, SLAVE,
                                               BLOCK_START, BLOCK_COUNT)
                except IOError as exc:
                    fehler += 1
                    print("Lesefehler: %s" % exc, file=sys.stderr)
                    time.sleep(args.interval)
                    continue

                neu = args.no_dedup or roh != letzte_roh
                faellig = runde - letzter_schreibzeitpunkt >= args.heartbeat

                if neu or faellig:
                    zeit = datetime.now().astimezone().isoformat(
                        timespec="milliseconds")
                    werte = {name: entpacke(roh, adr) for name, adr in FELDER}
                    schreiber.writerow(
                        [zeit]
                        + ["%.4f" % werte[name] for name, _ in FELDER]
                        + ["%.4f" % leistungsfaktor(werte)])
                    if args.output:
                        ziel.flush()
                    letzte_roh = roh
                    letzter_schreibzeitpunkt = runde
                    zeilen += 1

                rest = args.interval - (time.monotonic() - runde)
                if rest > 0:
                    time.sleep(rest)

        except KeyboardInterrupt:
            print(file=sys.stderr)

        dauer = time.monotonic() - beginn
        print("\n%d Zeilen in %.1f s (%d Lesefehler)"
              % (zeilen, dauer, fehler), file=sys.stderr)

        spitzen = lies_spitzen(ser)
        if spitzen:
            print("\nSpitzenwerte im Geraet seit dem letzten Loeschen:",
                  file=sys.stderr)
            for name, wert, einheit in spitzen:
                print("  %-26s %10.4f %s" % (name, wert, einheit),
                      file=sys.stderr)

    if args.output:
        ziel.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Fehler: %s" % exc, file=sys.stderr)
        sys.exit(1)
