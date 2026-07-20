#!/usr/bin/env python3
"""Liest und schreibt Konfigurationsparameter eines Janitza UMG 96RM.

Verwendung:
    python3 umg_param.py 45              # lesen (USHORT)
    python3 umg_param.py 45 0            # schreiben (USHORT)
    python3 umg_param.py -f 10           # lesen (FLOAT, 2 Register)
    python3 umg_param.py -f 10 100       # schreiben (FLOAT)

Parameteradressen siehe README. Achtung: Schreibzugriffe verändern die
Gerätekonfiguration dauerhaft.
"""

import argparse
import struct
import sys

import serial

from umg_read import PORT, SLAVE, BAUD, crc16

# Bekannte Parameter, nur zur Beschriftung der Ausgabe
NAMEN = {
    0: ("Modbus-Adresse", None),
    1: ("Baudrate-Code", None),
    3: ("Stoppbits/Paritaet", None),
    10: ("Stromwandler I1 primaer", "A"),
    12: ("Stromwandler I1 sekundaer", "A"),
    45: ("Ansprechschwelle Strommessung", "mA"),
    50: ("Passwort", None),
    200: ("Quelle Digitalausgang 1", None),
    506: ("Min/Max loeschen", None),
    507: ("Energiewerte loeschen", None),
}


def _transact(ser, req, erwartet):
    req += struct.pack("<H", crc16(req))
    ser.reset_input_buffer()
    ser.write(req)
    ser.flush()

    antwort = ser.read(erwartet)
    if len(antwort) < erwartet:
        raise IOError("keine oder unvollstaendige Antwort")
    if antwort[1] & 0x80:
        raise IOError("Modbus-Exception %d" % antwort[2])
    return antwort


def read_holding(ser, slave, start, count):
    """Funktionscode 03."""
    req = struct.pack(">BBHH", slave, 3, start, count)
    antwort = _transact(ser, req, 5 + 2 * count)
    return antwort[3:3 + 2 * count]


def write_single(ser, slave, addr, wert):
    """Funktionscode 06 - ein Register."""
    req = struct.pack(">BBHH", slave, 6, addr, wert)
    _transact(ser, req, 8)


def write_multiple(ser, slave, addr, daten):
    """Funktionscode 16 - mehrere Register, fuer FLOAT."""
    count = len(daten) // 2
    req = struct.pack(">BBHHB", slave, 16, addr, count, len(daten)) + daten
    _transact(ser, req, 8)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("adresse", type=int)
    p.add_argument("wert", nargs="?")
    p.add_argument("-f", "--float", action="store_true",
                   help="Parameter ist FLOAT (belegt 2 Register)")
    args = p.parse_args()

    name, einheit = NAMEN.get(args.adresse, ("unbekannt", None))
    suffix = " %s" % einheit if einheit else ""

    with serial.Serial(PORT, BAUD, timeout=1.0) as ser:
        if args.wert is not None:
            alt = read_holding(ser, SLAVE, args.adresse, 2 if args.float else 1)
            if args.float:
                write_multiple(ser, SLAVE, args.adresse,
                               struct.pack(">f", float(args.wert)))
                altwert = struct.unpack(">f", alt)[0]
            else:
                write_single(ser, SLAVE, args.adresse, int(args.wert))
                altwert = struct.unpack(">H", alt)[0]
            print("Parameter %03d (%s): %s -> %s%s"
                  % (args.adresse, name, altwert, args.wert, suffix))

        roh = read_holding(ser, SLAVE, args.adresse, 2 if args.float else 1)
        wert = struct.unpack(">f" if args.float else ">H", roh)[0]
        print("Parameter %03d (%s) = %s%s" % (args.adresse, name, wert, suffix))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Fehler: %s" % exc, file=sys.stderr)
        sys.exit(1)
