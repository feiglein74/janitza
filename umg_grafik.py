#!/usr/bin/env python3
"""Erzeugt eigenstaendige HTML-Grafiken aus den Messreihen.

Zwei Diagrammarten:

    verlauf    Zeitverlauf einer Groesse aus einer Logdatei von umg_log.py
    vergleich  Gestapelte Balken aus einer Beschreibung der Arbeitspunkte

Die Ausgabe ist jeweils eine einzelne HTML-Datei ohne externe Abhaengigkeiten
- CSS und JavaScript inline, Daten einkopiert. Sie laesst sich lokal im
Browser oeffnen und ohne Netz weitergeben.

Beispiele:

    python3 umg_grafik.py verlauf messungen/usb_vergleich.csv \\
        -o verlauf_usb.html --phasen messungen/usb_phasen.json \\
        --titel "Vier USB-Netzteile, aufgezeichnet" --zoom 0.3

    python3 umg_grafik.py vergleich messungen/wirkungsgrad.json \\
        -o wirkungsgrad.html

Format der Phasendatei (optional, hinterlegt die Plateaus grau):

    [{"von": "18:32:23", "bis": "18:33:25", "label": "1"}, ...]

Format der Vergleichsdatei:

    {
      "titel": "...", "untertitel": "...",
      "max": 121.49, "ticks": [0, 30, 60, 90, 120],
      "reihen": ["Nutzleistung", "Verluste", "Grundlast"],
      "gruppen": [
        {"titel": "20 W Abgabe",
         "zeilen": [{"name": "Linearnetzteil", "werte": [20, 33.12], "hl": false}]}
      ]
    }

Der Wirkungsgrad wird als erster Wert geteilt durch die Summe aller Werte
gerechnet - die erste Reihe muss also die Nutzleistung sein. Ist der erste
Wert 0, entfaellt die Angabe.
"""

import argparse
import csv
import json
import pathlib
import statistics as st
import sys
from datetime import datetime

# Kategoriale Palette, gegen Farbfehlsichtigkeit und Kontrast geprueft.
# Reihenfolge ist Teil der Pruefung - nicht umsortieren.
PALETTE_HELL = ["#2a78d6", "#008300", "#e87ba4", "#eda100"]
PALETTE_DUNKEL = ["#3987e5", "#008300", "#d55181", "#c98500"]

KOPF = """<title>{titel}</title>

<style>
  .viz-root {{
    color-scheme: light;
    --paper:#F2F4F6; --surface-1:#FFFFFF;
    --text-primary:#14181D; --text-secondary:#5A646E; --text-muted:#98A2AC;
    --rule:#C9D1D8; --rule-soft:#E6EAEE; --grid:#E9EDF1;
    --accent:#C2700B; --band:#F4F6F8;
{vars_hell}
  }}
  @media (prefers-color-scheme: dark) {{
    :root:where(:not([data-theme="light"])) .viz-root {{
      color-scheme: dark;
      --paper:#0D1116; --surface-1:#141A21;
      --text-primary:#DDE3E9; --text-secondary:#94A0AC; --text-muted:#626F7B;
      --rule:#2C3641; --rule-soft:#1E262E; --grid:#1F2831;
      --accent:#E9A44F; --band:#1A222A;
{vars_dunkel}
    }}
  }}
  :root[data-theme="dark"] .viz-root {{
    color-scheme: dark;
    --paper:#0D1116; --surface-1:#141A21;
    --text-primary:#DDE3E9; --text-secondary:#94A0AC; --text-muted:#626F7B;
    --rule:#2C3641; --rule-soft:#1E262E; --grid:#1F2831;
    --accent:#E9A44F; --band:#1A222A;
{vars_dunkel}
  }}

  * {{ box-sizing: border-box; }}
  body {{
    margin:0; background:var(--paper); color:var(--text-primary);
    font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    line-height:1.6; -webkit-font-smoothing:antialiased;
  }}
  .viz-root {{ background:var(--paper); min-height:100vh; }}
  .wrap {{ max-width:1040px; margin:0 auto; padding:40px 24px 96px;
           display:flex; flex-direction:column; gap:32px; }}
  header {{ display:flex; flex-direction:column; gap:10px; }}
  .eyebrow {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
              font-size:11px; letter-spacing:0.16em; text-transform:uppercase;
              color:var(--accent); }}
  h1 {{ margin:0; font-size:clamp(26px,4vw,34px); font-weight:600;
        letter-spacing:-0.02em; text-wrap:balance; }}
  h2 {{ margin:0; font-size:17px; font-weight:600; letter-spacing:-0.01em; }}
  h3 {{ margin:0; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size:11px; letter-spacing:0.12em; text-transform:uppercase;
        color:var(--text-muted); font-weight:500; }}
  .lede {{ margin:0; max-width:64ch; color:var(--text-secondary); }}
  section {{ display:flex; flex-direction:column; gap:14px; }}
  .chart {{ background:var(--surface-1); border:1px solid var(--rule);
            border-radius:3px; padding:18px 18px 10px; overflow-x:auto; }}
  svg {{ display:block; min-width:820px; width:100%; height:auto; }}
  .note {{ margin:0; color:var(--text-secondary); font-size:15px; max-width:70ch; }}
  .note b {{ color:var(--text-primary); font-weight:600; }}
  #tip {{ position:fixed; z-index:20; pointer-events:none; opacity:0;
          transition:opacity .08s ease; background:var(--text-primary);
          color:var(--surface-1); padding:6px 10px; border-radius:4px;
          font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
          font-size:12px; white-space:nowrap; }}
  #tip.on {{ opacity:1; }}
  table {{ width:100%; border-collapse:collapse; font-size:14px;
           font-variant-numeric:tabular-nums; }}
  th, td {{ text-align:right; padding:9px 0 9px 16px;
            border-bottom:1px solid var(--rule-soft); }}
  th:first-child, td:first-child {{ text-align:left; padding-left:0; }}
  th {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size:11px; letter-spacing:0.08em; text-transform:uppercase;
        color:var(--text-muted); font-weight:500; }}
  td.mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
             font-size:13px; }}
  .plot {{ min-width:640px; display:flex; flex-direction:column; gap:2px; }}
  .grp {{ display:flex; flex-direction:column; gap:2px; padding:9px 0; }}
  .grp + .grp {{ border-top:1px solid var(--rule-soft); }}
  .grp h3 {{ margin-bottom:3px; padding-left:122px; }}
  .row {{ display:grid; grid-template-columns:108px 1fr 64px; gap:14px;
          align-items:center; padding:3px 0; }}
  .row .name {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
                font-size:12px; color:var(--text-secondary); text-align:right;
                white-space:nowrap; }}
  .row.hl .name {{ color:var(--text-primary); font-weight:600; }}
  .track {{ position:relative; height:24px; }}
  .gridlines {{ position:absolute; inset:0; display:flex;
                justify-content:space-between; pointer-events:none; }}
  .gridlines i {{ width:1px; background:var(--grid); }}
  .bar {{ position:absolute; inset:0; display:flex; }}
  .seg {{ height:100%; cursor:default; transition:filter .12s ease; }}
  .seg + .seg {{ margin-left:2px; }}
  .seg:first-child {{ border-radius:4px 0 0 4px; }}
  .seg:last-child {{ border-radius:0 4px 4px 0; }}
  .seg:hover {{ filter:brightness(1.14); }}
  .row .eff {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
               font-size:13px; font-weight:600; font-variant-numeric:tabular-nums;
               text-align:right; color:var(--text-primary); }}
  .row .eff.none {{ color:var(--text-muted); font-weight:400; }}
  .axis {{ display:grid; grid-template-columns:108px 1fr 64px; gap:14px;
           margin-top:8px; padding-top:8px; border-top:1px solid var(--rule-soft); }}
  .ticks {{ grid-column:2; display:flex; justify-content:space-between;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            font-size:11px; color:var(--text-muted); }}
  .legend {{ display:flex; flex-wrap:wrap; gap:8px 22px; margin-top:14px;
             padding-top:14px; border-top:1px solid var(--rule-soft);
             font-size:13px; color:var(--text-secondary); }}
  .legend span {{ display:inline-flex; align-items:center; gap:8px; }}
  .key {{ width:12px; height:12px; border-radius:3px; flex:none; }}
  footer {{ border-top:1px solid var(--rule); padding-top:16px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            font-size:12px; color:var(--text-muted);
            display:flex; flex-wrap:wrap; gap:6px 30px; }}
  @media (max-width:620px) {{ .wrap {{ padding:28px 16px 64px; }} }}
</style>
"""


def farbvariablen(n):
    hell = "\n".join("    --series-%d:%s;" % (i + 1, PALETTE_HELL[i % 4])
                     for i in range(n))
    dunkel = "\n".join("      --series-%d:%s;" % (i + 1, PALETTE_DUNKEL[i % 4])
                       for i in range(n))
    return hell, dunkel


def kopf(titel, n_reihen):
    hell, dunkel = farbvariablen(n_reihen)
    return KOPF.format(titel=titel, vars_hell=hell, vars_dunkel=dunkel)


def lade_log(pfad, spalte):
    with open(pfad) as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SystemExit("Datei enthaelt keine Daten.")
    if spalte not in rows[0]:
        raise SystemExit("Spalte '%s' fehlt. Vorhanden: %s"
                         % (spalte, ", ".join(rows[0])))
    t0 = datetime.fromisoformat(rows[0]["zeit"])
    punkte = [((datetime.fromisoformat(r["zeit"]) - t0).total_seconds(),
               float(r[spalte])) for r in rows]
    return t0, punkte


def verdichten(punkte, ziel):
    """Mittelt auf etwa `ziel` Punkte herunter, damit die HTML-Datei klein
    bleibt. Bei 5 Werten pro Sekunde und langen Reihen sind das schnell
    zehntausende Punkte, die im Diagramm ohnehin auf demselben Pixel landen."""
    if len(punkte) <= ziel:
        return [[round(t, 1), round(v, 4)] for t, v in punkte]
    span = punkte[-1][0] or 1.0
    eimer = {}
    for t, v in punkte:
        eimer.setdefault(int(t / span * ziel), []).append(v)
    return [[round(k * span / ziel, 1), round(st.mean(v), 4)]
            for k, v in sorted(eimer.items())]


EINHEITEN = {"p_sum": "W", "s_sum": "VA", "q_sum": "var", "i_l1": "A",
             "u_l1n": "V", "frequenz": "Hz", "cosphi_l1": "", "lambda_sum": "",
             "thd_i_l1": "%", "thd_u_l1": "%"}
LABELS = {"p_sum": "Wirkleistung", "s_sum": "Scheinleistung", "i_l1": "Strom L1",
          "u_l1n": "Spannung L1-N", "frequenz": "Frequenz", "cosphi_l1": "cos phi",
          "lambda_sum": "Leistungsfaktor", "thd_i_l1": "Klirrfaktor Strom",
          "thd_u_l1": "Klirrfaktor Spannung"}


def ticks_fuer(ymax):
    for schritt in (0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 50, 100, 200):
        if ymax / schritt <= 6:
            n = int(ymax / schritt)
            return [round(i * schritt, 4) for i in range(n + 1)]
    return [0, ymax]


def baue_verlauf(args):
    spalten = args.column or ["p_sum"]
    daten = {}
    t0 = None
    for sp in spalten:
        t0, punkte = lade_log(args.datei, sp)
        daten[sp] = verdichten(punkte, args.punkte)

    tmax = max(d[-1][0] for d in daten.values())

    phasen = []
    if args.phasen:
        with open(args.phasen) as fh:
            roh = json.load(fh)

        def sek(hms):
            h, m, s = map(int, hms.split(":"))
            d = t0.replace(hour=h, minute=m, second=s, microsecond=0)
            return round((d - t0).total_seconds(), 1)

        phasen = [[sek(p["von"]), sek(p["bis"]), p.get("label", "")]
                  for p in roh]

    marken = []
    for m in (args.marke or []):
        teil = m.split(":", 1)
        marken.append([float(teil[0]), teil[1] if len(teil) > 1 else ""])

    # Panels: bei einer Spalte + --zoom zwei Panels derselben Groesse,
    # sonst ein Panel je Spalte.
    panels = []
    if len(spalten) == 1 and args.zoom:
        sp = spalten[0]
        ymax = args.max if args.max else max(v for _, v in daten[sp]) * 1.1
        panels.append({"key": sp, "ymax": ymax, "hoehe": 300,
                       "titel": "Gesamtverlauf"})
        panels.append({"key": sp, "ymax": args.zoom, "hoehe": 220,
                       "titel": "Zoom auf 0 bis %s %s"
                       % (fmt(args.zoom), EINHEITEN.get(sp, ""))})
    else:
        for i, sp in enumerate(spalten):
            ymax = max(v for _, v in daten[sp]) * 1.1
            if i == 0 and args.max:
                ymax = args.max
            panels.append({"key": sp, "ymax": ymax,
                           "hoehe": 260 if len(spalten) > 1 else 300,
                           "titel": LABELS.get(sp, sp)})

    for i, pan in enumerate(panels):
        pan["id"] = "p%d" % i
        pan["ticks"] = ticks_fuer(pan["ymax"])
        pan["einheit"] = EINHEITEN.get(pan["key"], "")

    teile = [kopf(args.titel, 1), '<div class="viz-root"><div class="wrap">']
    teile.append('<header><div class="eyebrow">%s</div><h1>%s</h1>'
                 % (args.eyebrow or ("%d Messpunkte ueber %.1f min"
                                     % (len(daten[spalten[0]]), tmax / 60)),
                    args.titel))
    if args.lede:
        teile.append('<p class="lede">%s</p>' % args.lede)
    teile.append("</header>")

    for pan in panels:
        teile.append('<section><h2>%s</h2><div class="chart">'
                     '<svg id="%s" viewBox="0 0 1000 %d" role="img" '
                     'aria-label="%s ueber die Zeit"></svg></div></section>'
                     % (pan["titel"], pan["id"], pan["hoehe"], pan["titel"]))

    teile.append('<footer><span>Janitza UMG 96RM · Modbus RTU</span>'
                 '<span>%s</span></footer>' % t0.strftime("%Y-%m-%d %H:%M"))
    teile.append("</div></div><div id=\"tip\"></div>")

    einheit_map = {pan["key"]: pan["einheit"] for pan in panels}
    aufrufe = "\n".join(
        'zeichne("%s",%s,%s,%s,%d);'
        % (pan["id"], json.dumps(pan["key"]), pan["ymax"],
           json.dumps(pan["ticks"]), pan["hoehe"])
        for pan in panels)
    teile.append("<script>\nconst DATEN=%s;\nconst PHASEN=%s;\n"
                 "const MARKEN=%s;\nconst EINHEIT=%s;\n%s\n%s\n</script>"
                 % (json.dumps(daten, separators=(",", ":")),
                    json.dumps(phasen, separators=(",", ":")),
                    json.dumps(marken, separators=(",", ":")),
                    json.dumps(einheit_map, separators=(",", ":")),
                    JS_VERLAUF, aufrufe))
    return "\n".join(teile)


JS_VERLAUF = r"""
const TMAX = Math.max(...Object.values(DATEN).map(a => a[a.length-1][0]));
const NS = "http://www.w3.org/2000/svg";
const tip = document.getElementById("tip");
const de = v => String(v).replace(".", ",");

function el(n, a) {
  const e = document.createElementNS(NS, n);
  for (const k in a) e.setAttribute(k, a[k]);
  return e;
}

function zeichne(id, key, ymax, yticks, hoehe) {
  const svg = document.getElementById(id);
  const D = DATEN[key];
  const L = 60, R = 14, T = 18, B = 30, W = 1000, H = hoehe;
  const px = t => L + (W - L - R) * t / TMAX;
  const py = v => H - B - (H - T - B) * Math.min(Math.max(v, 0), ymax) / ymax;

  PHASEN.forEach(([a, b, label]) => {
    svg.appendChild(el("rect", { x: px(a), y: T, width: Math.max(1, px(b) - px(a)),
      height: H - T - B, fill: "var(--band)" }));
    if (label) {
      const tx = el("text", { x: (px(a) + px(b)) / 2, y: T - 5,
        "text-anchor": "middle", "font-size": 10, fill: "var(--text-muted)",
        "font-family": "ui-monospace, Menlo, monospace" });
      tx.textContent = label;
      svg.appendChild(tx);
    }
  });

  yticks.forEach(v => {
    svg.appendChild(el("line", { x1: L, y1: py(v), x2: W - R, y2: py(v),
      stroke: "var(--grid)", "stroke-width": 1 }));
    const t = el("text", { x: L - 8, y: py(v) + 4, "text-anchor": "end",
      "font-size": 11, fill: "var(--text-muted)",
      "font-family": "ui-monospace, Menlo, monospace" });
    t.textContent = de(v);
    svg.appendChild(t);
  });

  const schritt = TMAX > 900 ? 240 : TMAX > 300 ? 60 : TMAX > 120 ? 30 : 10;
  for (let s = 0; s <= TMAX + 0.1; s += schritt) {
    const t = el("text", { x: px(s), y: H - 10, "text-anchor": "middle",
      "font-size": 11, fill: "var(--text-muted)",
      "font-family": "ui-monospace, Menlo, monospace" });
    t.textContent = (s / 60).toFixed(TMAX > 300 ? 0 : 1) + (s === 0 ? " min" : "");
    svg.appendChild(t);
  }

  MARKEN.forEach(([t, label]) => {
    svg.appendChild(el("line", { x1: px(t), y1: T, x2: px(t), y2: H - B,
      stroke: "var(--accent)", "stroke-width": 1, "stroke-dasharray": "3 3" }));
    if (label) {
      const tx = el("text", { x: px(t) + 4, y: T + 12, "font-size": 10,
        fill: "var(--accent)", "font-family": "ui-monospace, Menlo, monospace" });
      tx.textContent = label;
      svg.appendChild(tx);
    }
  });

  let d = "";
  D.forEach(([t, v], i) => {
    d += (i ? "L" : "M") + px(t).toFixed(1) + "," + py(v).toFixed(1);
  });
  svg.appendChild(el("path", { d, fill: "none", stroke: "var(--series-1)",
    "stroke-width": 2, "stroke-linejoin": "round" }));

  const cross = el("line", { y1: T, y2: H - B, stroke: "var(--text-muted)",
    "stroke-width": 1, opacity: 0 });
  svg.appendChild(cross);
  const feld = el("rect", { x: L, y: T, width: W - L - R, height: H - T - B,
    fill: "transparent" });
  svg.appendChild(feld);

  feld.addEventListener("mousemove", e => {
    const box = svg.getBoundingClientRect();
    const rel = (e.clientX - box.left) / box.width * W;
    const t = (rel - L) / (W - L - R) * TMAX;
    let best = D[0], diff = Infinity;
    for (const p of D) {
      const dd = Math.abs(p[0] - t);
      if (dd < diff) { diff = dd; best = p; }
    }
    cross.setAttribute("x1", px(best[0]));
    cross.setAttribute("x2", px(best[0]));
    cross.setAttribute("opacity", 0.4);
    const min = Math.floor(best[0] / 60), sek = Math.round(best[0] % 60);
    tip.textContent = min + ":" + String(sek).padStart(2, "0") + "  \u2014  "
      + de(best[1].toFixed(3)) + " " + (EINHEIT[key] || "");
    tip.classList.add("on");
    tip.style.left = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8) + "px";
    tip.style.top = (e.clientY - tip.offsetHeight - 10) + "px";
  });
  feld.addEventListener("mouseleave", () => {
    cross.setAttribute("opacity", 0);
    tip.classList.remove("on");
  });
}
"""


def fmt(v):
    return ("%g" % v).replace(".", ",")


def _ein_diagramm(d, teile):
    """Rendert ein Diagramm mit eigener Skala in die Teileliste."""
    reihen = d["reihen"]
    einheit = d.get("einheit", "W")
    hmax = d.get("max") or max(sum(z["werte"]) for g in d["gruppen"]
                               for z in g["zeilen"])
    ticks = d.get("ticks") or [0, round(hmax / 2, 2), round(hmax, 2)]

    teile.append("<section>")
    if d.get("titel"):
        teile.append("<h2>%s</h2>" % d["titel"])
    teile.append('<div class="chart"><div class="plot">')

    for g in d["gruppen"]:
        teile.append('<div class="grp">')
        if g.get("titel"):
            teile.append("<h3>%s</h3>" % g["titel"])
        for z in g["zeilen"]:
            werte = z["werte"]
            gesamt = sum(werte)
            eta = 100 * werte[0] / gesamt if werte[0] and gesamt else None
            teile.append('<div class="row%s">' % (" hl" if z.get("hl") else ""))
            teile.append('<div class="name">%s</div><div class="track">' % z["name"])
            teile.append('<div class="gridlines">%s</div>' % ("<i></i>" * len(ticks)))
            teile.append('<div class="bar">')
            for i, v in enumerate(werte):
                if v <= 0:
                    continue
                teile.append('<div class="seg" style="width:%.4f%%;'
                             'background:var(--series-%d)" title="%s — %s: %s %s">'
                             "</div>"
                             % (100 * v / hmax, i + 1, z["name"], reihen[i],
                                fmt(round(v, 3)), einheit))
            teile.append("</div></div>")
            teile.append('<div class="eff%s">%s</div>'
                         % ("" if eta else " none",
                            ("%.1f %%" % eta).replace(".", ",") if eta else "—"))
            teile.append("</div>")
        teile.append("</div>")

    teile.append('</div><div class="axis"><div class="ticks">%s</div></div>'
                 % "".join("<span>%s%s</span>"
                           % (fmt(t), " " + einheit if i == len(ticks) - 1 else "")
                           for i, t in enumerate(ticks)))
    teile.append('<div class="legend">%s</div>'
                 % "".join('<span><i class="key" style="background:'
                           'var(--series-%d)"></i> %s</span>' % (i + 1, r)
                           for i, r in enumerate(reihen)))
    teile.append("</div>")
    for absatz in d.get("hinweise", []):
        teile.append('<p class="note">%s</p>' % absatz)
    teile.append("</section>")


def baue_vergleich(args):
    with open(args.datei) as fh:
        spec = json.load(fh)

    # Eine Datei kann mehrere Diagramme mit je eigener Skala enthalten.
    diagramme = spec.get("diagramme") or [spec]
    n_reihen = max(len(d["reihen"]) for d in diagramme)

    teile = [kopf(spec["titel"], n_reihen),
             '<div class="viz-root"><div class="wrap">',
             '<header><div class="eyebrow">%s</div><h1>%s</h1>'
             % (spec.get("eyebrow", "Messreihe"), spec["titel"])]
    if spec.get("untertitel"):
        teile.append('<p class="lede">%s</p>' % spec["untertitel"])
    teile.append("</header>")

    for d in diagramme:
        _ein_diagramm(d, teile)

    teile.append('<footer><span>Janitza UMG 96RM · Modbus RTU</span>'
                 '<span>%s</span></footer>' % spec.get("fuss", ""))
    teile.append("</div></div>")
    return "\n".join(teile)


JS_SPEKTRUM = r"""
const tip = document.getElementById("tip");
const NS = "http://www.w3.org/2000/svg";
const de = (v, n) => v.toFixed(n).replace(".", ",");

function el(n, a) {
  const e = document.createElementNS(NS, n);
  for (const k in a) e.setAttribute(k, a[k]);
  return e;
}

function balken(id, feld, einheit, nk) {
  const svg = document.getElementById(id);
  const L = 62, R = 12, T = 14, B = 34, W = 1000, H = 320;
  const N = ORDNUNGEN;
  let vmax = 0;
  REIHEN.forEach(r => r.punkte.slice(0, N).forEach(p => {
    if (p[feld] > vmax) vmax = p[feld];
  }));
  const stufe = Math.pow(10, Math.floor(Math.log10(vmax || 1)));
  vmax = Math.ceil(vmax / stufe * 2) / 2 * stufe;

  const gruppe = (W - L - R) / N;
  const bw = Math.max(2, (gruppe - 4) / REIHEN.length);
  const py = v => H - B - (H - T - B) * Math.min(v, vmax) / vmax;

  for (let i = 0; i <= 4; i++) {
    const v = vmax * i / 4;
    svg.appendChild(el("line", { x1: L, y1: py(v), x2: W - R, y2: py(v),
      stroke: "var(--grid)", "stroke-width": 1 }));
    const t = el("text", { x: L - 8, y: py(v) + 4, "text-anchor": "end",
      "font-size": 11, fill: "var(--text-muted)",
      "font-family": "ui-monospace, Menlo, monospace" });
    t.textContent = de(v, nk);
    svg.appendChild(t);
  }

  REIHEN.forEach((r, ri) => {
    r.punkte.slice(0, N).forEach((p, oi) => {
      const x = L + gruppe * oi + 2 + ri * bw;
      const y = py(p[feld]);
      const rect = el("rect", { x, y, width: bw - 1, height: (H - B) - y,
        fill: "var(--series-" + (ri + 1) + ")", rx: 1.5 });
      const txt = r.label + " · " + (oi + 1) + ". Ordnung: "
        + de(p[feld], nk + 1) + " " + einheit;
      rect.addEventListener("mousemove", e => {
        tip.textContent = txt;
        tip.classList.add("on");
        tip.style.left = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8) + "px";
        tip.style.top = (e.clientY - tip.offsetHeight - 10) + "px";
      });
      rect.addEventListener("mouseleave", () => tip.classList.remove("on"));
      svg.appendChild(rect);
    });
  });

  for (let oi = 0; oi < N; oi++) {
    if (N > 20 && (oi + 1) % 2 === 0) continue;
    const t = el("text", { x: L + gruppe * oi + gruppe / 2, y: H - 14,
      "text-anchor": "middle", "font-size": 11, fill: "var(--text-muted)",
      "font-family": "ui-monospace, Menlo, monospace" });
    t.textContent = oi + 1;
    svg.appendChild(t);
  }
  const ax = el("text", { x: (L + W - R) / 2, y: H - 1, "text-anchor": "middle",
    "font-size": 11, fill: "var(--text-muted)",
    "font-family": "ui-monospace, Menlo, monospace" });
  ax.textContent = "Ordnung der Oberschwingung";
  svg.appendChild(ax);
}
"""


def baue_spektrum(args):
    """Vergleicht mehrere mit umg_oberschwingungen.py erzeugte CSVs."""
    labels = [x.strip() for x in (args.labels or "").split(";") if x.strip()]
    reihen = []
    for i, pfad in enumerate(args.dateien):
        with open(pfad) as fh:
            rows = list(csv.DictReader(fh))
        spalten = list(rows[0])
        abs_sp = spalten[1]
        pro_sp = spalten[1 + (len(spalten) - 1) // 2]
        punkte = [{"a": float(r[abs_sp]) * 1000.0, "p": float(r[pro_sp])}
                  for r in rows]
        reihen.append({"label": labels[i] if i < len(labels)
                       else pathlib.Path(pfad).stem, "punkte": punkte})

    n = min(args.ordnungen, min(len(r["punkte"]) for r in reihen))

    teile = [kopf(args.titel, len(reihen)),
             '<div class="viz-root"><div class="wrap">',
             '<header><div class="eyebrow">%s</div><h1>%s</h1>'
             % (args.eyebrow or "Oberschwingungsanalyse", args.titel)]
    if args.lede:
        teile.append('<p class="lede">%s</p>' % args.lede)
    teile.append("</header>")

    legende = "".join('<span><i class="key" style="background:var(--series-%d)">'
                      '</i> %s</span>' % (i + 1, r["label"])
                      for i, r in enumerate(reihen))

    for titel, feld, einheit, nk, hinweis in [
        ("Anteil an der Grundschwingung", "p", "%", 0, args.hinweis_p),
        ("Absoluter Strom je Ordnung", "a", "mA", 0, args.hinweis_a)]:
        teile.append('<section><h2>%s</h2><div class="chart">' % titel)
        teile.append('<svg id="chart_%s" viewBox="0 0 1000 320" role="img" '
                     'aria-label="%s"></svg>' % (feld, titel))
        teile.append('<div class="legend">%s</div></div>' % legende)
        if hinweis:
            teile.append('<p class="note">%s</p>' % hinweis)
        teile.append("</section>")

    for absatz in (args.note or "").split("|"):
        if absatz.strip():
            teile.append('<section><p class="note">%s</p></section>' % absatz.strip())

    teile.append('<footer><span>Janitza UMG 96RM · Fourieranalyse bis 40. Ordnung</span>'
                 '<span>%s</span></footer>' % (args.fuss or ""))
    teile.append('</div></div><div id="tip"></div>')
    teile.append("<script>\nconst REIHEN=%s;\nconst ORDNUNGEN=%d;\n%s\n"
                 'balken("chart_p","p","%%",0);\nbalken("chart_a","a","mA",0);\n</script>'
                 % (json.dumps(reihen, separators=(",", ":")), n, JS_SPEKTRUM))
    return "\n".join(teile)


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="modus", required=True)

    v = sub.add_parser("verlauf", help="Zeitverlauf aus einer Logdatei")
    v.add_argument("datei")
    v.add_argument("-o", "--output", required=True)
    v.add_argument("-c", "--column", action="append",
                   help="Spalte; mehrfach angebbar, je Spalte ein Panel "
                        "(Vorgabe p_sum)")
    v.add_argument("--titel", default="Zeitverlauf")
    v.add_argument("--lede", default="")
    v.add_argument("--eyebrow", default="")
    v.add_argument("--marke", action="append",
                   help="senkrechte Markierung, 'Sekunde' oder 'Sekunde:Text', "
                        "mehrfach angebbar")
    v.add_argument("--phasen", help="JSON mit von/bis/label je Plateau")
    v.add_argument("--punkte", type=int, default=1100,
                   help="Zielzahl der Punkte nach Verdichtung")
    v.add_argument("--max", type=float, help="Obergrenze der y-Achse")
    v.add_argument("--zoom", type=float,
                   help="zweites Panel mit dieser Obergrenze")
    v.set_defaults(fn=baue_verlauf)

    g = sub.add_parser("vergleich", help="Gestapelte Balken aus einer JSON-Datei")
    g.add_argument("datei")
    g.add_argument("-o", "--output", required=True)
    g.set_defaults(fn=baue_vergleich)

    k = sub.add_parser("spektrum",
                       help="Oberschwingungsspektren aus CSVs vergleichen")
    k.add_argument("dateien", nargs="+")
    k.add_argument("-o", "--output", required=True)
    k.add_argument("--labels", help="Beschriftungen, mit Semikolon getrennt")
    k.add_argument("--titel", default="Oberschwingungen im Vergleich")
    k.add_argument("--lede", default="")
    k.add_argument("--eyebrow", default="")
    k.add_argument("--fuss", default="")
    k.add_argument("--note", default="", help="Absaetze, mit | getrennt")
    k.add_argument("--hinweis-p", default="")
    k.add_argument("--hinweis-a", default="")
    k.add_argument("-n", "--ordnungen", type=int, default=15)
    k.set_defaults(fn=baue_spektrum)

    args = p.parse_args()
    html = args.fn(args)
    with open(args.output, "w") as fh:
        fh.write(html)
    print("%s geschrieben (%.1f kB)" % (args.output, len(html) / 1024))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Fehler: %s" % exc, file=sys.stderr)
        sys.exit(1)
