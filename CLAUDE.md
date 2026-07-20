# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Sachinformationen zu Gerät, Verkabelung, Registeradressen und Fehlersuche
stehen in `README.md` — dort nachschlagen, nicht hier duplizieren.

## Skripte

| Datei | Zweck |
|---|---|
| `umg_read.py` | Momentanwerte einmalig lesen; enthält CRC, FC04 und Float-Dekodierung, die die anderen importieren |
| `umg_log.py` | Messreihe als CSV aufzeichnen, 100 ms Überabtastung mit Dedup |
| `umg_param.py` | Konfigurationsparameter lesen und schreiben (FC03/06/16) |
| `umg_segmente.py` | Logdatei auswerten: Sprungstellen und stabile Betriebspunkte |
| `umg_oberschwingungen.py` | Fourieranalyse bis zur 40. Ordnung, mit Selbsttest gegen die THD-Register |
| `umg_grafik.py` | HTML-Grafiken erzeugen: `verlauf` aus CSV, `vergleich` aus JSON |
| `umg_live.py` | Live-Anzeige im Browser, lokaler Server; kann parallel aufzeichnen |
| `schaltbild.html` | Prinzipschaltbild des Prüfplatzes (Standalone-HTML, im Browser öffnen) |
| `wirkungsgrad.html` | Wirkungsgradvergleich — erzeugt aus `messungen/wirkungsgrad.json` |
| `spektren.html` | Oberschwingungsvergleich — erzeugt aus `messungen/spektrum_gan_*.csv` |
| `verlauf_usb.html` | Zeitverlauf der USB-Messreihe — erzeugt aus `messungen/usb_vergleich.csv` |

Aufgezeichnete Messreihen liegen in `messungen/`, die Herstellerdokumente
in `doku/` — dort nachschlagen statt im Netz suchen, die `/current/`-URLs
zeigen nach jeder Janitza-Revision auf ein anderes Dokument.

**Messdaten immer in `messungen/` schreiben, nie ins Scratchpad** — das ist
sitzungsgebunden und geht verloren. Bei der Inbetriebnahme ging so die
Zeitreihe der Integrationsprobe verloren; erhalten blieben nur die
gerechneten Kennzahlen.

Das UMG hängt an `/dev/ttyUSB0`, Adresse 2, 38400 8N1. Der Benutzer ist in
`dialout` und `plugdev`, kein `sudo` nötig.

Abweichungen vom Auslieferungszustand:

| Parameter | Werk | jetzt | Grund |
|---|---|---|---|
| `045` Ansprechschwelle | 5 mA | **0** | sonst werden kleine Ströme hart auf 0 gesetzt und der Energiezähler läuft dort nicht mit |
| `043` Nennstrom TDD | 150 A | **5** | passend zum Wandlernennstrom, sonst sind die TDD-Register 914–918 wertlos |

Details im README. Der Energiezähler wurde mehrfach über `507` gelöscht; der
ursprüngliche Stand von rund 150 MWh aus der Vorverwendung ist damit weg.

Die Komparatoren wurden erprobt und **wieder zurückgesetzt** (`110 = 0`,
`200 = 1`); das Gerät steht dort auf Werkseinstellung. Die verifizierte
Prozedur samt gemessener Umschaltpunkte steht im README.

## Diagnose-Reihenfolge bei fehlender Antwort

Diese Reihenfolge nicht abkürzen — bei der Inbetriebnahme wurde stundenlang
die Hardware verdächtigt, während die Ursache in der Abfrage lag.

1. **Erst Register 19050 (Frequenz) prüfen.** Muss ~50 Hz liefern. Das ist
   der billigste Positivtest, und ein Erfolg schließt die gesamte
   physikalische Ebene auf einen Schlag aus.
2. **Erst danach** Adresse, Baudrate, Verkabelung in Zweifel ziehen.

Ein Timeout beweist bei diesem Gerät **nicht**, dass die Verbindung steht
oder nicht steht — das UMG schweigt auch bei gültiger Verbindung, wenn die
Registeradresse ungültig ist. Es schickt keine Modbus-Exception. Die
allgemeine Modbus-Faustregel „falsches Register ⇒ Exception, also muss ein
Timeout ein Leitungsproblem sein" führt hier in die Irre.

## Beim Debuggen mit Hardware

Der Benutzer sitzt physisch am Gerät und schraubt zwischen den Läufen um.
Daraus folgt:

- **Nach jedem Testlauf fragen, was verändert wurde**, bevor das Ergebnis
  interpretiert wird. Zwei identisch aussehende Läufe können
  unterschiedliche Aufbauten messen.
- **Einzelergebnisse nicht als Beweis nehmen.** Tests mehrfach wiederholen
  und die Trefferquote ausgeben; ein einzelner Treffer unter vielen
  Fehlschlägen bedeutet meist, dass sich der Aufbau geändert hat.
- **Breite Parameter-Sweeps sind billig, aber wertlos, wenn eine gemeinsame
  Konstante darin falsch ist.** Ein Sweep über 200 Kombinationen blieb
  komplett still, weil alle 200 dieselbe falsche Registeradresse benutzten.
  Vor einem Sweep prüfen, was in allen Durchläufen gleich bleibt.

## Konventionen im Code

`umg_read.py` implementiert Modbus RTU direkt auf `pyserial` — CRC, Frame-Bau
und Float-Dekodierung von Hand. Vorhanden sind `read_input_registers()`
(FC 04) und `read_write_registers()` (FC 23, schreiben und lesen in einem
Telegramm); `umg_param.py` ergänzt FC 03, 06 und 16. Das ist Absicht: Janitza weicht bei
Funktionscode (04) und Wortreihenfolge (Big Endian) von den Voreinstellungen
gängiger Bibliotheken ab. Keine Modbus-Bibliothek einziehen, ohne diese
beiden Punkte explizit zu konfigurieren.

Kommentare und Ausgaben sind auf Deutsch, ohne Umlaute in Konsolenausgaben.

## Serieller Port

Der Port ist exklusiv. `umg_read.py`, `umg_log.py`, `umg_param.py`,
`umg_segmente.py` und `umg_live.py` können **nicht gleichzeitig** laufen.
Läuft eine Live-Anzeige, muss sie erst gestoppt werden — oder sie zeichnet
mit `--csv` gleich selbst auf.

Hintergrundprozesse mit dem dafür vorgesehenen Werkzeug beenden, **nicht mit
`pkill`**: Das Suchmuster findet sich auch in der eigenen Befehlszeile und
bringt die Shell mitsamt der nachfolgenden Auswertung um.

## Grafiken

Beide HTML-Grafiken sind **erzeugte Artefakte**, nicht von Hand gepflegt. Wer
sie ändern will, ändert die Eingabe und lässt `umg_grafik.py` neu laufen —
nicht die HTML-Datei direkt, die wird beim nächsten Lauf überschrieben.

Eingaben: `messungen/wirkungsgrad.json` (Arbeitspunkte) und
`messungen/usb_phasen.json` (Plateaugrenzen für die Schattierung).

Beim Ändern des Templates in `umg_grafik.py`: Das erzeugte JavaScript vor dem
Ausliefern prüfen, es steckt als String im Python-Code und wird von keinem
Linter erfasst:

```bash
python3 -c "import pathlib;s=pathlib.Path('x.html').read_text();\
pathlib.Path('/tmp/c.js').write_text(s.split('<script>')[1].split('</script>')[0])"
node --check /tmp/c.js
```
