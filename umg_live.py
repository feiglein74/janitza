#!/usr/bin/env python3
"""Live-Anzeige der Messwerte im Browser.

Startet einen kleinen Webserver aus der Standardbibliothek. Ein Hintergrund-
Thread liest das UMG zyklisch aus und haelt die letzten Werte vor; die Seite
holt sie sich alle 400 ms und zeichnet Kacheln und eine rollende Kurve.

Der serielle Port ist exklusiv. Solange diese Anzeige laeuft, kann
umg_log.py nicht gleichzeitig aufzeichnen - deshalb kann die Anzeige das mit
`--csv` selbst uebernehmen, im selben Format.

    python3 umg_live.py
    python3 umg_live.py --csv messungen/live.csv
    python3 umg_live.py --host 0.0.0.0 --port 8080

Vorgabe ist 127.0.0.1: nur vom eigenen Rechner erreichbar. Mit
`--host 0.0.0.0` wird die Anzeige im ganzen Netz sichtbar - bewusst nicht die
Voreinstellung.
"""

import argparse
import csv
import json
import struct
import sys
import threading
import time
from collections import deque
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import serial

from umg_read import PORT, SLAVE, BAUD, read_input_registers
from umg_log import BLOCK_START, BLOCK_COUNT, FELDER, BERECHNET, leistungsfaktor

# Kacheln: Spaltenname, Beschriftung, Einheit, Nachkommastellen
KACHELN = [
    ("u_l1n", "Spannung L1-N", "V", 2),
    ("i_l1", "Strom L1", "A", 4),
    ("p_sum", "Wirkleistung", "W", 3),
    ("s_sum", "Scheinleistung", "VA", 3),
    ("lambda_sum", "Leistungsfaktor", "", 3),
    ("cosphi_l1", "cos phi", "", 3),
    ("thd_i_l1", "THD Strom", "%", 1),
    ("frequenz", "Frequenz", "Hz", 3),
]

PUFFER = 3000          # gespeicherte Punkte, bei 5 Hz rund 10 Minuten
zustand = {
    "werte": {},
    "verlauf": deque(maxlen=PUFFER),
    "start_wh": None,
    "wh": 0.0,
    "fehler": 0,
    "gelesen": 0,
    "zeit": None,
    "lauft": True,
}
sperre = threading.Lock()


def entpacke(roh, adresse):
    off = (adresse - BLOCK_START) * 2
    return struct.unpack(">f", roh[off:off + 4])[0]


def sampler(args):
    """Einziger Besitzer des seriellen Ports."""
    schreiber = None
    datei = None
    if args.csv:
        datei = open(args.csv, "w", newline="")
        schreiber = csv.writer(datei)
        schreiber.writerow(["zeit"] + [n for n, _ in FELDER] + BERECHNET)

    t0 = time.monotonic()
    letzte_roh = None

    try:
        with serial.Serial(PORT, BAUD, timeout=1.0) as ser:
            while zustand["lauft"]:
                runde = time.monotonic()
                try:
                    roh = read_input_registers(ser, SLAVE, BLOCK_START, BLOCK_COUNT)
                except IOError:
                    with sperre:
                        zustand["fehler"] += 1
                    time.sleep(args.interval)
                    continue

                werte = {n: entpacke(roh, a) for n, a in FELDER}
                werte["lambda_sum"] = leistungsfaktor(werte)
                t = round(runde - t0, 2)

                with sperre:
                    if zustand["start_wh"] is None:
                        zustand["start_wh"] = werte["wh_bezogen"]
                    zustand["wh"] = werte["wh_bezogen"] - zustand["start_wh"]
                    zustand["werte"] = werte
                    zustand["zeit"] = datetime.now().astimezone().isoformat(
                        timespec="seconds")
                    zustand["gelesen"] += 1
                    zustand["verlauf"].append((t, round(werte["p_sum"], 4)))

                # Aufzeichnung nur bei tatsaechlicher Aktualisierung, wie im Logger
                if schreiber is not None and roh != letzte_roh:
                    schreiber.writerow(
                        [datetime.now().astimezone().isoformat(timespec="milliseconds")]
                        + ["%.4f" % werte[n] for n, _ in FELDER]
                        + ["%.4f" % werte[n] for n in BERECHNET])
                    datei.flush()
                    letzte_roh = roh

                rest = args.interval - (time.monotonic() - runde)
                if rest > 0:
                    time.sleep(rest)
    except Exception as exc:
        print("Sampler beendet: %s" % exc, file=sys.stderr)
        zustand["lauft"] = False
    finally:
        if datei:
            datei.close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass                                   # keine Zugriffszeilen im Terminal

    def _send(self, typ, inhalt):
        roh = inhalt.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", typ + "; charset=utf-8")
        self.send_header("Content-Length", str(len(roh)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(roh)

    def do_GET(self):
        pfad = urlparse(self.path)
        if pfad.path == "/":
            self._send("text/html", SEITE)
            return
        if pfad.path == "/daten":
            seit = float((parse_qs(pfad.query).get("seit") or ["-1"])[0])
            with sperre:
                neu = [[t, v] for t, v in zustand["verlauf"] if t > seit]
                antwort = {
                    "werte": {k: round(v, 6) for k, v in zustand["werte"].items()},
                    "neu": neu,
                    "wh": round(zustand["wh"], 6),
                    "fehler": zustand["fehler"],
                    "gelesen": zustand["gelesen"],
                    "zeit": zustand["zeit"],
                    "lauft": zustand["lauft"],
                }
            self._send("application/json", json.dumps(antwort))
            return
        self.send_error(404)


SEITE = """<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UMG 96RM · live</title>
<style>
  :root {
    color-scheme: light dark;
    --paper:#F2F4F6; --surface:#FFFFFF;
    --ink:#14181D; --ink2:#5A646E; --ink3:#98A2AC;
    --rule:#C9D1D8; --rule2:#E6EAEE; --grid:#E9EDF1;
    --accent:#C2700B; --linie:#2a78d6; --gut:#0ca30c; --schlecht:#d03b3b;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --paper:#0D1116; --surface:#141A21;
      --ink:#DDE3E9; --ink2:#94A0AC; --ink3:#626F7B;
      --rule:#2C3641; --rule2:#1E262E; --grid:#1F2831;
      --accent:#E9A44F; --linie:#3987e5; --gut:#0ca30c; --schlecht:#ff7a6e;
    }
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--paper); color:var(--ink);
         font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
         -webkit-font-smoothing:antialiased; }
  .wrap { max-width:1000px; margin:0 auto; padding:26px 20px 60px;
          display:flex; flex-direction:column; gap:22px; }
  header { display:flex; align-items:baseline; justify-content:space-between;
           flex-wrap:wrap; gap:10px; }
  h1 { margin:0; font-size:20px; font-weight:600; letter-spacing:-0.01em; }
  .status { font-family: ui-monospace, Menlo, monospace; font-size:12px;
            color:var(--ink2); display:flex; align-items:center; gap:8px; }
  .punkt { width:8px; height:8px; border-radius:50%; background:var(--gut); flex:none; }
  .punkt.tot { background:var(--schlecht); }

  .kacheln { display:grid; gap:2px;
             grid-template-columns:repeat(auto-fit, minmax(168px, 1fr));
             background:var(--rule2); border:1px solid var(--rule); border-radius:3px;
             overflow:hidden; }
  .kachel { background:var(--surface); padding:14px 16px;
            display:flex; flex-direction:column; gap:2px; }
  .kachel .wert { font-size:26px; font-weight:600; letter-spacing:-0.02em;
                  font-variant-numeric:tabular-nums; }
  .kachel .einheit { font-size:14px; font-weight:400; color:var(--ink2); }
  .kachel .label { font-family: ui-monospace, Menlo, monospace; font-size:11px;
                   letter-spacing:0.06em; text-transform:uppercase; color:var(--ink3); }

  .chart { background:var(--surface); border:1px solid var(--rule);
           border-radius:3px; padding:16px 16px 8px; }
  .chart h2 { margin:0 0 10px; font-size:13px; font-weight:600; color:var(--ink2); }
  svg { display:block; width:100%; height:auto; }
  footer { font-family: ui-monospace, Menlo, monospace; font-size:12px;
           color:var(--ink3); display:flex; gap:24px; flex-wrap:wrap; }
</style></head><body>
<div class="wrap">
  <header>
    <h1>UMG 96RM · live</h1>
    <div class="status"><i class="punkt" id="punkt"></i><span id="stat">verbinde…</span></div>
  </header>
  <div class="kacheln" id="kacheln"></div>
  <div class="chart">
    <h2>Wirkleistung, letzte <span id="fenster">120</span> s</h2>
    <svg id="plot" viewBox="0 0 1000 260" preserveAspectRatio="none"></svg>
  </div>
  <footer>
    <span id="arbeit">Arbeit seit Start: —</span>
    <span id="zaehler">—</span>
  </footer>
</div>
<script>
const KACHELN = __KACHELN__;
const NS = "http://www.w3.org/2000/svg";
const FENSTER = 120;                       // Sekunden im Diagramm
let daten = [], letzte = -1;

const de = (v, n) => v.toFixed(n).replace(".", ",");

const kacheln = document.getElementById("kacheln");
KACHELN.forEach(([k]) => {
  const d = document.createElement("div");
  d.className = "kachel";
  d.innerHTML = '<div class="wert" id="w_' + k + '">—</div>'
              + '<div class="label" id="l_' + k + '"></div>';
  kacheln.appendChild(d);
});

function el(n, a) {
  const e = document.createElementNS(NS, n);
  for (const k in a) e.setAttribute(k, a[k]);
  return e;
}

function zeichne() {
  const svg = document.getElementById("plot");
  svg.textContent = "";
  if (daten.length < 2) return;
  const L = 56, R = 12, T = 12, B = 26, W = 1000, H = 260;
  const tEnd = daten[daten.length - 1][0];
  const sicht = daten.filter(p => p[0] >= tEnd - FENSTER);
  if (sicht.length < 2) return;
  const t0 = tEnd - FENSTER;
  let vmax = Math.max(...sicht.map(p => p[1]), 0.001);
  const stufe = Math.pow(10, Math.floor(Math.log10(vmax)));
  vmax = Math.ceil(vmax / stufe * 2) / 2 * stufe;
  const px = t => L + (W - L - R) * (t - t0) / FENSTER;
  const py = v => H - B - (H - T - B) * Math.max(0, Math.min(v, vmax)) / vmax;

  for (let i = 0; i <= 4; i++) {
    const v = vmax * i / 4;
    svg.appendChild(el("line", { x1: L, y1: py(v), x2: W - R, y2: py(v),
      stroke: "var(--grid)", "stroke-width": 1 }));
    const tx = el("text", { x: L - 8, y: py(v) + 4, "text-anchor": "end",
      "font-size": 12, fill: "var(--ink3)", "font-family": "ui-monospace, Menlo, monospace" });
    tx.textContent = de(v, vmax < 1 ? 2 : vmax < 10 ? 1 : 0);
    svg.appendChild(tx);
  }
  for (let s = 0; s <= FENSTER; s += 30) {
    const tx = el("text", { x: px(t0 + s), y: H - 8, "text-anchor": "middle",
      "font-size": 12, fill: "var(--ink3)", "font-family": "ui-monospace, Menlo, monospace" });
    tx.textContent = "-" + (FENSTER - s) + " s";
    svg.appendChild(tx);
  }
  let d = "";
  sicht.forEach((p, i) => { d += (i ? "L" : "M") + px(p[0]).toFixed(1) + "," + py(p[1]).toFixed(1); });
  svg.appendChild(el("path", { d, fill: "none", stroke: "var(--linie)",
    "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }));
  const l = sicht[sicht.length - 1];
  svg.appendChild(el("circle", { cx: px(l[0]), cy: py(l[1]), r: 4, fill: "var(--linie)" }));
}

async function tick() {
  try {
    const r = await fetch("/daten?seit=" + letzte);
    const j = await r.json();
    KACHELN.forEach(([k, label, einheit, n]) => {
      const v = j.werte[k];
      if (v === undefined) return;
      document.getElementById("w_" + k).innerHTML =
        de(v, n) + (einheit ? ' <span class="einheit">' + einheit + "</span>" : "");
      document.getElementById("l_" + k).textContent = label;
    });
    if (j.neu.length) {
      daten = daten.concat(j.neu);
      letzte = daten[daten.length - 1][0];
      if (daten.length > 4000) daten = daten.slice(-3000);
      zeichne();
    }
    document.getElementById("punkt").className = "punkt" + (j.lauft ? "" : " tot");
    document.getElementById("stat").textContent =
      j.lauft ? (j.gelesen + " Messungen · " + j.fehler + " Fehler") : "Sampler gestoppt";
    document.getElementById("arbeit").textContent =
      "Arbeit seit Start: " + de(j.wh, 5) + " Wh";
    document.getElementById("zaehler").textContent = j.zeit || "";
  } catch (e) {
    document.getElementById("punkt").className = "punkt tot";
    document.getElementById("stat").textContent = "keine Verbindung";
  }
}
document.getElementById("fenster").textContent = FENSTER;
tick();
setInterval(tick, 400);
</script></body></html>
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1",
                   help="Bindeadresse (Vorgabe 127.0.0.1, nur lokal)")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("-i", "--interval", type=float, default=0.1,
                   help="Abtastintervall in Sekunden (Vorgabe 0.1)")
    p.add_argument("--csv", help="parallel in diese Datei aufzeichnen")
    args = p.parse_args()

    global SEITE
    SEITE = SEITE.replace("__KACHELN__", json.dumps(KACHELN))

    t = threading.Thread(target=sampler, args=(args,), daemon=True)
    t.start()

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    ziel = "http://%s:%d/" % ("localhost" if args.host == "127.0.0.1" else args.host,
                              args.port)
    print("Live-Anzeige auf %s" % ziel)
    if args.csv:
        print("zeichnet zusaetzlich nach %s auf" % args.csv)
    if args.host != "127.0.0.1":
        print("Achtung: im Netz erreichbar, nicht nur lokal.")
    print("Beenden mit Strg-C")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbeendet.")
    finally:
        zustand["lauft"] = False
        srv.server_close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Fehler: %s" % exc, file=sys.stderr)
        sys.exit(1)
