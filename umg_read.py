#!/usr/bin/env python3
"""Liest Messwerte aus einem Janitza UMG 96RM ueber Modbus RTU.

Die Registeradressen stammen aus der Janitza Modbus-Adressliste
(Dok. 1.040.034.t). Messwerte sind float32, Big Endian (High-Word zuerst).
Die hier verwendeten Adressen sind rohe Protokolladressen, nullbasiert.
"""

import struct
import sys

import serial

PORT = "/dev/ttyUSB0"
SLAVE = 2
BAUD = 38400

# Adresse -> (Bezeichnung, Einheit); alle float32 im 19000er-Block
MESSWERTE = [
    (19000, "Spannung L1-N", "V"),
    (19002, "Spannung L2-N", "V"),
    (19004, "Spannung L3-N", "V"),
    (19006, "Spannung L1-L2", "V"),
    (19008, "Spannung L2-L3", "V"),
    (19010, "Spannung L1-L3", "V"),
    (19012, "Strom L1", "A"),
    (19014, "Strom L2", "A"),
    (19016, "Strom L3", "A"),
    (19020, "Wirkleistung L1", "W"),
    (19022, "Wirkleistung L2", "W"),
    (19024, "Wirkleistung L3", "W"),
    (19026, "Wirkleistung Summe", "W"),
    (19050, "Frequenz", "Hz"),
]


def crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def _frage(ser, req):
    """Telegramm absenden und die Nutzdaten einer Leseantwort zurueckgeben.

    Gemeinsamer Teil von FC 04 und FC 23: beide antworten mit
    Adresse, Funktionscode, Byteanzahl, Daten, CRC.
    """
    req += struct.pack("<H", crc16(req))

    ser.reset_input_buffer()
    ser.write(req)
    ser.flush()

    header = ser.read(3)
    if len(header) < 3:
        raise IOError("keine Antwort vom Geraet")
    if header[1] & 0x80:
        code = ser.read(1)
        raise IOError("Modbus-Exception %d" % (code[0] if code else 0))

    nbytes = header[2]
    payload = ser.read(nbytes + 2)
    if len(payload) < nbytes + 2:
        raise IOError("unvollstaendige Antwort")

    return payload[:nbytes]


def read_input_registers(ser, slave, start, count):
    """Funktionscode 04 - der von Janitza dokumentierte."""
    return _frage(ser, struct.pack(">BBHH", slave, 4, start, count))


def read_write_registers(ser, slave, lese_start, lese_count,
                         schreib_start, daten):
    """Funktionscode 23 (0x17) - schreiben und lesen in einem Telegramm.

    Das Geraet schreibt zuerst und liest danach; zurueck kommt also der
    Zustand nach dem Schreibzugriff. Spart einen Umlauf, wenn zyklisch
    gesteuert und gemessen wird - bei rund 40 ms je Umlauf und einem
    Messfenster von 200 ms ist das der Unterschied zwischen einem und
    zwei Fuenfteln der verfuegbaren Zeit.

    `daten` ist der rohe Registerinhalt, also 2 Byte je Register,
    Big Endian - passend zu struct.pack('>f', wert) fuer FLOAT-Parameter
    oder struct.pack('>H', wert) fuer einzelne SHORT-Register.

    Achtung: Nur die Halteregister sind schreibbar. Messwerte sind
    Eingangsregister und lassen sich mit FC 23 zwar lesen, aber nicht
    beschreiben.
    """
    if len(daten) % 2:
        raise ValueError("Schreibdaten muessen eine gerade Byteanzahl haben")
    schreib_count = len(daten) // 2
    req = struct.pack(">BBHHHHB", slave, 23, lese_start, lese_count,
                      schreib_start, schreib_count, len(daten)) + daten
    return _frage(ser, req)


def main():
    with serial.Serial(PORT, BAUD, bytesize=8, parity="N",
                       stopbits=1, timeout=1.0) as ser:
        # 19000..19051 in einem Rutsch (52 Register)
        raw = read_input_registers(ser, SLAVE, 19000, 52)

        print("UMG 96RM auf %s, Adresse %d, %d baud\n" % (PORT, SLAVE, BAUD))
        for addr, name, einheit in MESSWERTE:
            off = (addr - 19000) * 2
            # Big Endian: High-Word zuerst
            wert = struct.unpack(">f", raw[off:off + 4])[0]
            print("  %-22s %12.3f %s" % (name, wert, einheit))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Fehler: %s" % exc, file=sys.stderr)
        sys.exit(1)
