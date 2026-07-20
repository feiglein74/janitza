#!/usr/bin/env python3
"""Findet Lastwechsel und stabile Betriebspunkte in einer Logdatei.

Sucht in einer mit umg_log.py aufgezeichneten CSV nach Sprungstellen und
gibt die dazwischenliegenden Plateaus mit Mittelwert und Streuung aus.

Gedacht fuer Messreihen, bei denen ein Pruefling mehrere Arbeitspunkte
durchlaeuft: die Plateaus sind die Arbeitspunkte, ihre Mittelwerte die
Messergebnisse.

Verwendung:
    python3 umg_segmente.py messung.csv
    python3 umg_segmente.py messung.csv -c i_l1
    python3 umg_segmente.py messung.csv --extra cosphi_l1,lambda_sum
    python3 umg_segmente.py messung.csv -s 4 --min-plateau 10
"""

import argparse
import csv
import statistics as st
import sys
from datetime import datetime

# Verstellungen an einem Geraet erzeugen oft mehrere Spruenge kurz
# hintereinander - Ueberschwingen, Korrektur, Nachjustieren. Spruenge, die
# dichter als dieser Abstand liegen, gelten als ein Ereignis.
#
# Der Wert haengt daran, wie schnell verstellt wird: ein Kippschalter macht
# einen Sprung, ein Multiturn-Poti eine Rampe ueber zehn oder zwanzig
# Sekunden. Zu klein gewaehlt, zerfaellt eine Rampe in Scheinereignisse und
# ihre Zwischenstufen erscheinen als Plateaus.
EREIGNIS_ABSTAND_S = 8.0


def rauschen(werte):
    """Robuste Streuungsschaetzung ueber die Differenzen aufeinanderfolgender
    Werte. Unempfindlich gegen die Spruenge, die wir gerade suchen."""
    diffs = [abs(b - a) for a, b in zip(werte, werte[1:])]
    if not diffs:
        return 0.0
    return st.median(diffs) * 1.4826


def finde_spruenge(werte, fenster, schwelle):
    """Vergleicht das gleitende Mittel vor und nach jedem Punkt."""
    n = len(werte)
    roh = []
    for i in range(fenster, n - fenster):
        d = st.mean(werte[i:i + fenster]) - st.mean(werte[i - fenster:i])
        if abs(d) > schwelle:
            roh.append((abs(d), i, d))

    # Nur den staerksten Sprung je Umgebung behalten
    roh.sort(reverse=True)
    behalten = []
    for _, i, d in roh:
        if all(abs(i - j) > fenster for j, _ in behalten):
            behalten.append((i, d))
    behalten.sort()
    return behalten


def gruppiere(spruenge, zeiten, abstand=EREIGNIS_ABSTAND_S):
    """Fasst dicht beieinanderliegende Spruenge zu Ereignissen zusammen."""
    if not spruenge:
        return []
    gruppen = [[spruenge[0]]]
    for eintrag in spruenge[1:]:
        vorher = gruppen[-1][-1][0]
        if (zeiten[eintrag[0]] - zeiten[vorher]).total_seconds() \
                <= abstand:
            gruppen[-1].append(eintrag)
        else:
            gruppen.append([eintrag])
    return gruppen


def main():
    p = argparse.ArgumentParser()
    p.add_argument("datei")
    p.add_argument("-c", "--column", default="p_sum",
                   help="auszuwertende Spalte (Vorgabe p_sum)")
    p.add_argument("-w", "--window", type=int, default=10,
                   help="Fensterbreite in Messpunkten (Vorgabe 10)")
    p.add_argument("-s", "--sigma", type=float, default=6.0,
                   help="Ansprechschwelle in Sigma (Vorgabe 6)")
    p.add_argument("--min-plateau", type=float, default=3.0,
                   help="Plateaus kuerzer als N Sekunden verschweigen")
    p.add_argument("-g", "--gap", type=float, default=EREIGNIS_ABSTAND_S,
                   help="Spruenge im Abstand unter N Sekunden gelten als ein "
                        "Ereignis (Vorgabe %.0f). Bei langsamer Verstellung, "
                        "etwa mit Multiturn-Poti, hochsetzen."
                        % EREIGNIS_ABSTAND_S)
    p.add_argument("--extra", default="",
                   help="weitere Spalten, je Plateau gemittelt, kommagetrennt")
    args = p.parse_args()

    with open(args.datei) as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        print("Datei enthaelt keine Daten.", file=sys.stderr)
        return 1
    if args.column not in rows[0]:
        print("Spalte '%s' nicht vorhanden. Verfuegbar: %s"
              % (args.column, ", ".join(rows[0])), file=sys.stderr)
        return 1

    zeiten = [datetime.fromisoformat(r["zeit"]) for r in rows]
    werte = [float(r[args.column]) for r in rows]
    extra = [s.strip() for s in args.extra.split(",") if s.strip()]
    n = len(werte)

    sigma = rauschen(werte) or 1e-6
    schwelle = args.sigma * sigma
    spruenge = finde_spruenge(werte, args.window, schwelle)
    ereignisse = gruppiere(spruenge, zeiten, args.gap)

    dauer = (zeiten[-1] - zeiten[0]).total_seconds()
    print("%s: %d Messpunkte ueber %.1f s, Spalte '%s'"
          % (args.datei, n, dauer, args.column))
    print("Rauschen sigma = %.4f, Ansprechschwelle = %.4f (%.0f sigma)"
          % (sigma, schwelle, args.sigma))
    print()

    if ereignisse:
        print("%d Ereignis(se), %d Sprungstelle(n):"
              % (len(ereignisse), len(spruenge)))
        for k, gruppe in enumerate(ereignisse, 1):
            von, bis = zeiten[gruppe[0][0]], zeiten[gruppe[-1][0]]
            netto = werte[min(gruppe[-1][0] + args.window, n - 1)] \
                - werte[max(gruppe[0][0] - args.window, 0)]
            print("  %d)  %s  %.1f s, %d Schritte, netto %+.3f"
                  % (k, von.strftime("%H:%M:%S"),
                     (bis - von).total_seconds(), len(gruppe), netto))
            for i, d in gruppe:
                print("        %s  %+8.3f  (%.0f sigma)"
                      % (zeiten[i].strftime("%H:%M:%S.%f")[:-3],
                         d, abs(d) / sigma))
    else:
        print("Keine Sprungstellen - Verlauf durchgehend stabil.")
    print()

    # Plateaus liegen zwischen den Ereignissen; die Fensterbreite an den
    # Raendern wird verworfen, weil dort noch gemischt gemittelt wird.
    grenzen = [0]
    for gruppe in ereignisse:
        grenzen += [gruppe[0][0], gruppe[-1][0]]
    grenzen.append(n - 1)

    print("Stabile Betriebspunkte:")
    kopf = "  %-8s %-8s %7s %10s %9s %6s" % (
        "von", "bis", "Dauer", "Mittel", "sigma", "n")
    for name in extra:
        kopf += " %9s" % name[:9]
    print(kopf)

    gefunden = 0
    for a, b in zip(grenzen[::2], grenzen[1::2]):
        lo = a + (args.window if a else 0)
        hi = b - (args.window if b < n - 1 else 0)
        if hi - lo < 3:
            continue
        sek = (zeiten[hi] - zeiten[lo]).total_seconds()
        if sek < args.min_plateau:
            continue
        seg = werte[lo:hi]
        zeile = "  %-8s %-8s %6.1fs %10.4f %9.4f %6d" % (
            zeiten[lo].strftime("%H:%M:%S"), zeiten[hi].strftime("%H:%M:%S"),
            sek, st.mean(seg), st.pstdev(seg), len(seg))
        for name in extra:
            if name in rows[0]:
                zeile += " %9.4f" % st.mean(
                    [float(r[name]) for r in rows[lo:hi]])
            else:
                zeile += " %9s" % "-"
        print(zeile)
        gefunden += 1

    if not gefunden:
        print("  (keine Abschnitte laenger als %.0f s)" % args.min_plateau)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("Fehler: %s" % exc, file=sys.stderr)
        sys.exit(1)
