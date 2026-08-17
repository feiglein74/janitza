# UMG 96RM auslesen

Liest Messwerte aus einem **Janitza UMG 96RM (Grundgerät)** über Modbus RTU
auf RS485 aus.

`umg_read.py` kommt ohne Modbus-Bibliothek aus und baut die Frames selbst —
das hält die Kontrolle über Funktionscode und Wortreihenfolge, bei denen
Janitza von den üblichen Voreinstellungen abweicht.

Alle Angaben unten stammen aus der Betriebsanleitung Dok. 1.040.126.1.a
(10/2023) und der Modbus-Adressliste Dok. 1.040.034.t (01/2023).

## Beispielausgabe

```
UMG 96RM auf /dev/ttyUSB0, Adresse 2, 38400 baud

  Spannung L1-N                230.493 V
  Spannung L2-N                  0.000 V
  Spannung L3-N                  0.000 V
  Spannung L1-L2               230.493 V
  Spannung L2-L3                 0.000 V
  Spannung L1-L3               230.493 V
  Strom L1                       0.000 A
  Strom L2                       0.000 A
  Strom L3                       0.000 A
  Wirkleistung L1                0.000 W
  Wirkleistung L2                0.000 W
  Wirkleistung L3                0.000 W
  Wirkleistung Summe             0.000 W
  Frequenz                      50.029 Hz
```

## Stromwandler zwingend erforderlich

Handbuch S. 24, wörtlich:

> „Das UMG 96RM ist für den Anschluss von Stromwandlern mit Sekundärströmen
> von ../1A und ../5A ausgelegt. Das werkseitig eingestellte
> Stromwandlerverhältnis liegt bei 5/5A und muss gegebenenfalls an die
> verwendeten Stromwandler angepasst werden.
> **Eine Direktmessung ohne Stromwandler ist mit dem UMG 96RM nicht möglich.**
> Es können nur Wechselströme und keine Gleichströme gemessen werden."

Die Stromeingänge vertragen laut technischen Daten **120 A für 1 Sekunde**.
Eine Wandler-Sekundärseite ist von sich aus strombegrenzt und kann diesen
Wert nicht überschreiten; ein direkt aufgelegter Netzstromkreis liefert im
Fehlerfall den vollen Kurzschlussstrom der Installation.

Wie oft die 120 A / 1 s wiederholt werden dürfen und welcher **Dauerstrom**
zulässig ist, steht **nicht** im Handbuch. Die genannten 6 A<sub>rms</sub>
sind der Messbereich, keine thermische Dauergrenze.

**Kleine Ströme messen:** Für Prüflinge im Bereich weniger hundert
Milliampere lohnt es sich, den Leiter **mehrfach durch das Wandlerfenster**
zu führen. Sechs Windungen durch den hier vorhandenen 30/5-Wandler ergeben
effektiv 5/5, also 1:1 — das Wandlerverhältnis in `010`/`012` bleibt dann auf
der Werkseinstellung. Die Zuordnung von Windungszahl, Messbereich und
Leitungsschutzschalter steht im Schaltbild.

## Hardware

- Janitza UMG 96RM (Grundgerät, RS485 serienmäßig)
- Stromwandler mit Sekundärstrom 1 A oder 5 A
- USB-RS485-Adapter — hier ein Waveshare USB-RS232/485 mit FT232R
- Verdrilltes, geschirmtes Kabel, z. B. Li2YCY(TP) 2x2x0.22
  **CAT-Kabel ist laut Handbuch für Modbus ungeeignet.**

## Messplatz

`schaltbild.html` enthält das Prinzipschaltbild des geplanten Prüfplatzes für
wechselnde Einzelgeräte — im Browser öffnen. Es zeigt Leistungskreis,
Steuerkreis mit Schützselbsthaltung und die Einbindung der Janitza, dazu die
Zuordnung von Windungszahl, Messbereich, Parameter `010` und
Leitungsschutzschalter.

Die Grundidee: **Mit Wandler steht die Janitza neben dem Lastpfad, nicht
darin.** Der Wandler sitzt im Lastpfad, das Gerät sieht nur die
Sekundärseite. Not-Aus und Koppelrelais wirken als Öffner im Haltekreis des
Schützes und schalten keinen Laststrom; die Selbsthaltung ergibt den
Wiederanlaufschutz.

Prinzipschaltbild, kein ausführungsreifer Stromlaufplan. Vor Inbetriebnahme
durch eine Elektrofachkraft prüfen lassen.

### Einkaufsliste

Abgeleitet aus dem, was beim Aufbau und bei den Messungen als Lücke sichtbar
wurde. Nach Dringlichkeit.

#### Schutzkreis — das ist die eigentliche Lücke

| Teil | Spezifikation | warum |
|---|---|---|
| **FI/RCD** | 30 mA, Typ A (Typ B bei Prüflingen mit Umrichter) | Personenschutz, durch nichts anderes zu ersetzen |
| **LS-Schalter** | B2, B3 oder B4, abgestimmt auf die Windungszahl | siehe Tabelle im Schaltbild — Windungszahl und Vorsicherung sind ein Paar |
| **Not-Aus** | rastend, mit Öffnerkontakt | wirkt auf den Haltekreis, nicht auf den Laststrom |
| **Schütz** | mit Hilfskontakt für die Selbsthaltung | ergibt den Wiederanlaufschutz |
| **Koppelrelais** | **Spulenleistung < 1,2 W bei 24 V** (≥ 480 Ω), Öffnerkontakt | die 50-mA-Grenze der Digitalausgänge ist bindend — nach der Spule auswählen, nicht nach den Kontaktdaten |
| **Netzteil 24 V** | für den Steuerkreis | die Digitalausgänge brauchen eine externe Hilfsspannung |
| **Prüfklemmen** (optional) | mit Trennstelle und Querbrücker für den Wandler-Sekundärkreis | nur nötig, wenn am Wandlerkreis unter Spannung gearbeitet werden soll — siehe unten |
| **Sicherung** | 10 A, Charakteristik C | laut Anschlussplan S. 106 für die Spannungsmesspfade gefordert |

#### Messlücke schließen

**Oszilloskop mit Stromzange** oder Shunt mit Differenztastkopf.

Das ist die einzige Anschaffung, die eine **neue Klasse von Messungen**
aufmacht statt die bestehenden zu verbessern. Am festen 200-ms-Messfenster
scheiterten der Einschaltstrom der Glühlampe und die Burst-Frequenz des
GaN-Laders — beides unter *Messreihen* dokumentiert.

Ob sich das lohnt, hängt daran, ob Einschaltvorgänge und Schaltverhalten
interessieren oder nur der Verbrauch über die Zeit.

#### Kleinteile

- **Li2YCY(TP) 2×2×0,22** für die Modbus-Leitung — die aktuelle Strecke läuft
  nur, weil sie kurz ist
- **120-Ω-Abschlusswiderstände** oder Janitzas Fertigstecker **52.00.008**,
  sobald die Leitung länger wird
- **Aderendhülsen** — Querschnitte siehe *Ausführung der Klemmstellen*

#### Nicht nötig

**Ein zweiter USB-RS485-Adapter.** Der vorhandene funktioniert nachweislich —
Loopback 10 von 10, über 100 000 Messungen ohne Lesefehler.

**Ein Präzisionsmessgerät für Sub-Watt-Standby.** Die Integration über den
Energiezähler erreichte bei 0,225 W einen Standardfehler von 0,0004 W, also
0,2 %. Das reicht für alles, was hier gemessen werden soll.

**Ein weiterer Stromwandler.** Der vorhandene 30/5 ergibt mit sechs Windungen
effektiv 5/5 — genau richtig für Kleinverbraucher.

## Klemmenbelegung

| Klemme | Funktion |
|---|---|
| 1 / 2 | Versorgung N/− bzw. L/+ |
| 3 / 4 / 5 / 6 | Spannungsmessung V1 / V2 / V3 / VN |
| 7 / 8 | Strom I1 (S1 / S2) |
| 9 / 10 | Strom I2 (S1 / S2) |
| 11 / 12 | Strom I3 (S1 / S2) |
| 13 | Digitalausgänge, gemeinsamer Bezug |
| 14 / 15 | Digitalausgang 1 / 2 |
| 16 | RS485 **B** |
| 17 | RS485 **A** |

### Ausführung der Klemmstellen

| | Strom- und Spannungsmessung | Digitalausgänge |
|---|---|---|
| Querschnitt | 0,2–2,5 mm² (AWG 26-12) | 0,14–1,5 mm² (AWG 28-16) |
| Aderendhülsen | 0,2–2,5 mm² | 0,2–1,5 mm² |
| Anzugsmoment | **0,4–0,5 Nm** | 0,20–0,25 Nm |
| Abisolierlänge | 7 mm | 7 mm |
| Leiter je Klemmstelle | **nur einer** | nur einer |

Messleitungen müssen für mindestens 80 °C ausgelegt sein.

Für den Wandler-Sekundärkreis, wo eine gelöste Ader der einzige Fehlerfall
ist, der ohne Zutun eintritt:

- **Aderendhülsen** verwenden — sonst spreizen sich die Litzen auf und die
  Schraube klemmt nur einen Teil davon
- **Sicherungslack** über Schraubenkopf und Klemmenkörper. Der Nutzen liegt
  weniger im mechanischen Halt als in der **Sichtmarke**: Ist die Lackspur
  gerissen, hat sich etwas bewegt — sichtbar beim Draufschauen, ohne
  nachziehen zu müssen.
- **Zugentlastung an der Leitung**, nicht an der Klemme. Schrumpfschlauch
  isoliert und bündelt, hält aber keinen Zug ab; ein Kabelbinder auf Schiene
  oder Schelle kurz hinter der Klemme schon.
- Nach einigen Wärmezyklen **einmal nachziehen** — Kupfer setzt sich.

Die Strom- und Spannungsklemmen sitzen auf einem **steckbaren Klemmenteil**
(Ersatzteil 10.01.871), das jedoch **verschraubt** wird. Damit ist der
naheliegende zweite Weg, den Kreis versehentlich zu öffnen, konstruktiv
ausgeschlossen — bei einem Gerät, das Wandler-Sekundärkreise führt, ist das
Absicht und keine Bequemlichkeit.

Der Schirm der RS485-Leitung wird nur **einseitig** auf PE gelegt,
schaltschrankseitig. Beidseitiges Auflegen erzeugt eine Erdschleife.

Das UMG 96RM hat eine reine 2-Draht-RS485 ohne Masseanschluss; der
gemeinsame Bezug entsteht über PE. Bei einem Laptop im Akkubetrieb mit nicht
galvanisch getrenntem Adapter fehlt dieser Bezug — dann Netzteil anstecken
oder einen isolierten Adapter verwenden.

**Abschlusswiderstände:** Das UMG hat keine, weder eingebaut noch als Jumper.
Bei längeren Leitungen 120 Ω extern über Klemme 16/17.

### Leitung und Baudrate

Dokumentiert (Handbuch S. 33): geschirmtes verdrilltes Kabel, etwa
Li2YCY(TP) 2×2×0,22, **max. 1200 m bei 38400 Baud**, höchstens 32 Teilnehmer
je Segment. **Für ungeschirmte Verlegung gibt es keine Angabe** — sie ist
schlicht nicht vorgesehen.

Aus der Technik, nicht aus dem Handbuch:

- **Verdrillt ist wichtiger als geschirmt.** RS485 überträgt differentiell;
  eine Störung, die beide Adern gleich trifft, hebt sich am Empfänger auf.
  Das leistet die Verdrillung. Der Schirm ist die zweite Verteidigungslinie.
  Zwei einzeln verlegte Adern sind deutlich schlechter als ein ungeschirmtes
  verdrilltes Paar.
- **Auf Tischlänge unkritisch.** Unter etwa zehn Metern in ruhiger Umgebung
  läuft ungeschirmtes verdrilltes Kabel problemlos — der hiesige Aufbau
  belegt das mit CAT-Kabel und ohne Abschlusswiderstände.
- **Ein schaltendes Schütz ändert das.** Der Lichtbogen beim Öffnen erzeugt
  breitbandiges Störspektrum direkt neben der Datenleitung. Spätestens dann
  ist der Schirm keine Formalie.

**Warum Janitza CAT-Kabel ablehnt, ist nicht der Schirm** — CAT ist verdrillt
und oft geschirmt. Es ist der **Wellenwiderstand**: CAT liegt bei 100 Ω,
RS485 erwartet 120 Ω. Die Fehlanpassung erzeugt Reflexionen. Über wenige
Meter bedeutungslos, weil die Laufzeit gegen die Bitdauer verschwindet — über
hundert Meter bei hoher Baudrate nicht mehr.

**Eine höhere Baudrate bringt hier nichts.** Das Gerät aktualisiert alle
200 ms, ein voller Lesevorgang über 52 Register dauert gemessen 47 ms. Es
wird also ohnehin drei Viertel des Fensters gewartet. 115200 würde das auf
etwa 20 ms drücken und 27 ms schenken, mit denen nichts anzufangen ist.

Umgekehrt ist die **niedrigere Baudrate die robustere**: längere Bitdauer,
größerer Störabstand, mehr Toleranz gegen Reflexionen und Einkopplungen.
38400 ist damit nicht nur ausreichend, sondern die bessere Wahl.

Zwei Fälle, in denen das kippt:

- **Mehrere Geräte am Bus.** Bei 47 ms je Abfrage passen etwa vier
  Teilnehmer in ein 200-ms-Fenster.
- **Das vollständige Oberschwingungsspektrum aller neun Kanäle** — 720
  Register in sechs Telegrammen, zusammen deutlich über 200 ms. Einphasig
  mit zwei Kanälen sind es rund 90 ms, das passt.

Hat der Adapter einen Schiebeschalter RS232/RS485, muss er auf **RS485**
stehen. Die beiden Zweige sind wechselseitig abgeschaltet.

## Gerätekonfiguration

Am UMG die Tasten **1 und 2 gleichzeitig ~1 Sekunde** drücken, bis `PRG`
erscheint. Taste 2 blättert durch drei Menüs: Stromwandler → Spannungs-
wandler → **Parameterliste**.

In der Parameterliste ist die **obere Zeile die Parameternummer** und die
**untere der Wert**. Taste 1 wählt die Ziffer, Taste 2 ändert sie
(kurz = +1, lang = −1). Am Gerät sind nur **dreistellige** Parameteradressen
eingebbar; alles ab 1000 geht nur über Modbus oder GridVis.

| Parameter | Bedeutung | Bereich | Werk |
|---|---|---|---|
| `000` | Modbus-Adresse | 1–247 | 1 |
| `001` | Baudrate-Code | 0–4 | 4 |
| `003` | Stoppbits / Parität | 0–3 | 0 |
| `010` / `012` | Stromwandler I1 primär / sekundär | / 1 oder 5 | 5 / 5 |
| `018` / `020` | Stromwandler I2 primär / sekundär | | 5 / 5 |
| `026` / `028` | Stromwandler I3 primär / sekundär | | 5 / 5 |
| `043` | Nennstrom für TDD (A, float) | 0–1000000 | 150 |
| `045` | Ansprechschwelle Strommessung (mA) | 0–200 | 5 |
| `050` | Passwort | | 0 = keins |
| `506` | Min/Max-Werte löschen | 0–1 | 0 |
| `507` | Energiewerte löschen | | |
| `508` | Sofortiges Schreiben ins EEPROM | | |

Baudrate-Codes: `0` = 9600, `1` = 19200, `2` = 38400, `3` = 57600,
`4` = 115200.

Stoppbits/Parität: `0` = 1 Stoppbit ohne Parität, `1` = 2 Stoppbits ohne
Parität, `2` = 1 Stoppbit gerade, `3` = 1 Stoppbit ungerade. Datenbits sind
fest auf 8.

Die im Skript hinterlegten Werte (Adresse 2, 38400, 8N1) stehen oben in
`umg_read.py` und müssen zur Geräteeinstellung passen.

## Messtechnische Grenzen

Technische Daten S. 85/86:

| | |
|---|---|
| Nennstrom | 5 A |
| Messbereich Strom | 0–6 A<sub>rms</sub> |
| **Auflösung** | **0,1 mA** (Display nur 0,01 A) |
| Genauigkeit Phasenstrom | Klasse 0,2 nach IEC 61557-12 |
| Leistungsaufnahme Strompfad | ca. 0,2 VA, R<sub>i</sub> = 5 mΩ |
| Überlast | 120 A für 1 s (sinusförmig) |
| Abtastfrequenz | 21,33 kHz bei 50 Hz je Kanal |

Über RS485 kommen die Werte als float32 mit voller Auflösung — der Faktor
100 gegenüber der Displayanzeige ist der eigentliche Grund, die Schnittstelle
zu benutzen. **Auflösung ist aber nicht Genauigkeit:** die Klasse 0,2 bezieht
sich auf den Nennwert, im unteren Messbereich dominiert daher der absolute
Fehler.

**Messfenster:** Alle Effektivwerte werden über 10 Perioden (50 Hz) bzw. 12
Perioden (60 Hz) gebildet, also **200 ms**. Häufiger pollen liefert keine
neuen Daten.

**Ansprechschwelle (Parameter `045`):** Einheit mA, Bereich 0–200,
Werkseinstellung 5 mA, bezogen auf den Eingangs-/Sekundärstrom. Bei einem
Wandler skaliert die Schwelle primärseitig mit dem Wandlerverhältnis mit.
Bei einem 100/5-Wandler entsprechen 5 mA sekundär bereits 100 mA primär,
also gut 23 W bei 230 V, die als Null durchgehen.

Das Handbuch enthält **keine Beschreibung der Wirkungsweise**. Am Gerät
nachgemessen (Juli 2026, Eingang offen, Wandlerverhältnis 5/5):

| Parameter `045` | Strom L1 | Wirkleistung L1 |
|---|---|---|
| 5 mA (Werk) | exakt 0,000 A | exakt 0,000 W |
| 0 mA | 0,001 A | −0,003 bis −0,005 W |

**Ströme unterhalb der Schwelle werden also hart auf 0 gesetzt** — und damit
auch die Leistung. Konsequenz: Der **Energiezähler zählt in diesem Bereich
nicht mit**. Wer kleine Verbräuche über die Zeit integrieren will, muss die
Schwelle absenken, sonst bleibt der Zähler stehen.

Das Grundrauschen liegt bei rund **1 mA**, entsprechend etwa 0,2 W bei
230 V. Das leichte negative Vorzeichen der Leistung deutet auf einen
konstanten Offset hin, der sich rechnerisch abziehen ließe.

Nach dem Einschalten braucht die automatische Frequenzerkennung ca. 20 s;
währenddessen halten die Messwerte die zugesicherte Unsicherheit nicht ein.

## Zeit, Min/Max und Speicher

**Das Grundgerät hat keine Echtzeituhr.** Die Register 512–517
(Jahr/Monat/Tag/Stunde/Minute/Sekunde) tragen in der Parametertabelle die
Fußnote „Werte-Einstellungen nur für die UMG96RM-Erweiterungen mit Batterie
und Uhr". Zeitstempel müssen daher vom Rechner kommen.

**Min/Max-Werte werden ohne Zeitstempel gespeichert** (S. 12: „Speicherung
von Min- und Maxwerten (ohne Zeitstempel)"), alle 5 Minuten ins EEPROM. Sie
laufen kumulativ seit dem letzten Löschen und werden alle 200 ms
aktualisiert. Löschen über Parameter `506` (eine `001` schreiben).

Nützlich, um Spitzen zu erfassen, die zwischen zwei Abfragen liegen — man
erfährt allerdings nicht, *wann* sie auftraten:

| Adresse | Wert |
|---|---|
| 3358 / 3360 / 3362 | Maximalstrom I L1 / L2 / L3 |
| 3510 | Maximum des Leistungsmittelwerts Psum3 |
| 2578 | Maximalfrequenz |
| 3436 | Minimalfrequenz |

Diese Register sind RD/**WR**, lassen sich also auch einzeln überschreiben.

**Einen Datenlogger hat das Grundgerät nicht.** Das EEPROM speichert alle 5
Minuten nur Komparatortimer, S0-Zählerstände, Min/Max/Mittelwerte und
Energiewerte — bei einem Spannungsausfall gehen bis zu 5 Minuten verloren.
Parameter `508` erzwingt ein sofortiges Schreiben.

## Messreihen

In `messungen/` liegen die aufgezeichneten Reihen. Alle mit Direktmessung im
Strompfad, Wandlerverhältnis 5/5, Ansprechschwelle 0 mA.

| Datei | Prüfling | Inhalt |
|---|---|---|
| `trafo_leerlauf.csv` | Labornetzteil, Leerlauf | 60 s Grundlinie, 301 Punkte |
| `spielerei.csv` | Labornetzteil, Leerlauf | 120 s mit zwei Verstellungen |
| `wirkungsgrad.csv` | Labornetzteil unter Last | 12-V-Reihe, zwei OVP-Abschaltungen |
| `wirkungsgrad2.csv` | Labornetzteil unter Last | 6/12/20 V, sauber durchgelaufen |
| `gluehlampe.csv` | 40-W-Glühlampe | Referenzmessung, ein Einschaltzyklus |
| `gan_leerlauf.csv` | GaN-USB-Lader 140 W | 9,4 min Leerlauf, nichts angesteckt |
| `gan_last.csv` | GaN-USB-Lader 140 W | 20 V bei 0,25 / 1 / 3 A, dazu Ruhezustände |
| `usb_vergleich.csv` | 4 USB-Netzteile | 5 V/1 A alle vier, dazu 9 V/2 A für 2 und 3 |
| `spektrum_gan_*.csv` | GaN-USB-Lader | Oberschwingungsspektren, drei Arbeitspunkte |
| `heisskleber.csv` | PTC-Klebepistole | Kaltstart und Aufheizen, 220 s |
| `live.csv`, `luefter.csv` | Versorgung der elektronischen Last | Ruhezustände und Lüfterverhalten |

Dazu die Eingabedateien der Grafiken: `wirkungsgrad.json` (Arbeitspunkte) und
`usb_phasen.json` (Plateaugrenzen).

**Ausgewertete Grafiken**, alle im Browser zu öffnen und aus den Rohdaten
erzeugt:

| Datei | Inhalt |
|---|---|
| `wirkungsgrad.html` | Linearnetzteil, GaN-Lader und vier USB-Netzteile an gleichen Arbeitspunkten |
| `verlauf_usb.html` | Zeitverlauf der USB-Messreihe, mit Zoom auf die Leerlaufzustände |
| `spektren.html` | Oberschwingungsspektren des GaN-Laders, relativ und absolut |
| `heisskleber.html` | Klebepistole: Wirkleistung und Klirrfaktor über die Zeit |
| `schaltbild.html` | Prinzipschaltbild des Prüfplatzes |

### Referenzmessung: 40-W-Glühlampe

Eine Glühlampe ist rein ohmsch und ihre Leistung bekannt — damit prüft man die
gesamte Kette, nicht nur das Messgerät. Ergebnis:

| | gemessen | erwartet |
|---|---|---|
| Wirkleistung | **39,37 W** | 39,4 W bei 228,3 V |
| cosφ | **1,0000** | 1 |
| THD Strom | **1,74 %** | ~0, Rest ist Netzverzerrung (THD U = 1,13 %) |
| Strom | 0,1718 A | |

Die Nennleistung gilt bei 230 V; über P ∝ U² ergibt das bei den gemessenen
228,3 V genau 39,4 W. **Abweichung 0,1 %.** Zusammen mit cosφ = 1,0000
belegt das, dass Wandlerverhältnis, Skalierung, Vorzeichen und
Float-Dekodierung stimmen.

Zum Vergleich dieselben Größen am Labornetzteil im Leerlauf: 14,04 W,
cosφ 0,341, THD 67,9 %. Zwei Prüflinge, wie sie unterschiedlicher nicht sein
könnten.

**Der Einschaltstrom ist mit diesem Gerät nicht messbar.** Der kalte
Glühfaden hat etwa ein Zehntel seines Betriebswiderstands, der Vorgang ist
nach rund 100 ms vorbei. Bei einem Messfenster von 200 ms bleibt davon ein
einziger erhöhter Wert übrig:

```
17:39:42.126   I 0,0006 A   P  -0,002 W
17:39:42.332   I 0,1775 A   P  39,978 W   <- einziges Fenster mit Einschaltanteil
17:39:42.521   I 0,1714 A   P  39,028 W
```

0,1775 A gegen 0,1713 A im Betrieb, also 3,6 % statt der tatsächlichen
800–1000 %. Der Max-Speicher des Geräts (Register 3358) hält denselben Wert —
es geht also nichts durch zu langsames Pollen verloren, die Grenze ist das
Messfenster selbst. Für den echten Verlauf braucht es ein Oszilloskop mit
Shunt oder Stromzange.

Der langsame Ausläufer desselben Effekts ist dagegen gut sichtbar: 39,37 W in
den ersten 16 Sekunden, 38,99 W danach — der Faden heizt sich weiter auf, der
Widerstand steigt, die Leistung sinkt um 1 %.

### Ergebnis der Wirkungsgradmessung

Linear geregeltes Labornetzteil, 20 V / 3 A, einphasig an 230 V:

| Arbeitspunkt | P<sub>aus</sub> | P<sub>ein</sub> | η | cosφ | THD I |
|---|---|---|---|---|---|
| Leerlauf | 0 W | 14,04 W | — | 0,341 | 67,9 % |
| 12 V / 0,25 A | 3 W | 20,05 W | 15,0 % | 0,465 | 67,3 % |
| 12 V / 0,50 A | 6 W | 24,40 W | 24,6 % | 0,541 | 69,9 % |
| 6 V / 1,00 A | 6 W | 32,24 W | 18,6 % | 0,643 | 75,0 % |
| 12 V / 1,00 A | 12 W | 32,83 W | 36,5 % | 0,641 | 75,0 % |
| 20 V / 1,00 A | 20 W | 53,12 W | 37,7 % | 0,804 | 83,8 % |
| 20 V / 3,00 A | 60 W | 121,49 W | 49,4 % | 0,962 | 86,3 % |

**Die beiden 6-W-Punkte sind der Kern:** gleiche Ausgangsleistung, 24,6 %
gegen 18,6 %. Der Längsregler verheizt die Differenz zur
Zwischenkreisspannung.

**Bis 12 V ist die Zwischenkreisspannung fest.** 6 V/1 A und 12 V/1 A nehmen
32,24 W und 32,83 W auf, also dasselbe innerhalb der Messgenauigkeit — und
ihr THD stimmt auf drei Nachkommastellen überein (75,008 % / 75,004 %). Aus
Netzsicht dieselbe Last.

**Zwischen 12 V und 20 V wird umgeschaltet.** Bei gleichem Strom steigt die
Aufnahme auf 53,12 W, was mit fester Zwischenkreisspannung unvereinbar ist.
Aus 20 V/1 A gegen 20 V/3 A geschätzt: obere Zwischenkreisspannung ~31 V.

Aus der 12-V-Reihe ergibt sich als Modell **P<sub>ein</sub> = 15,94 W +
1,394 × P<sub>aus</sub>** (Residuen ≤ 0,1 W), also ein marginaler
Wirkungsgrad von 71,8 % bei 15,94 W fixem Sockel — davon 14,04 W Grundlast
und 1,8 W allein für den aktiven Ausgang.

**Messgenauigkeit:** Der Arbeitspunkt 12 V/1 A wurde dreimal über zwei Läufe
und eine Dreiviertelstunde gemessen — 32,63 / 33,09 / 32,83 W. Spannweite
0,46 W.

### GaN-USB-Lader gegen Linearnetzteil

Beide Geräte an denselben Arbeitspunkten gemessen, 20 V Ausgangsspannung:

| P<sub>aus</sub> | GaN-Lader | Linearnetzteil |
|---|---|---|
| Leerlauf | 0,225 W | 14,04 W |
| 5 W (0,25 A) | 7,36 W · 67,9 % | — |
| 20 W (1,00 A) | 24,11 W · **83,0 %** | 53,12 W · 37,7 % |
| 60 W (3,00 A) | 66,11 W · **90,8 %** | 121,49 W · 49,4 % |

Bei 60 W Nutzleistung verheizt der Lader 6,1 W, das Linearnetzteil 61,5 W —
also mehr Abwärme, als der Lader insgesamt aufnimmt. Im Leerlauf liegt der
Faktor bei 62.

**Leistungsfaktor steigt mit der Last, springt aber nicht:**

| P<sub>ein</sub> | λ | THD I |
|---|---|---|
| 7,4 W | 0,50 | 58 % |
| 24,1 W | 0,73 | 45 % |
| 66,1 W | 0,88 | 31 % |

Ein Kondensatoreingang ganz ohne Korrektur läge bei 80–130 % THD, eine
aktive PFC bei λ > 0,95 und THD < 10 %. Der Lader liegt dazwischen. Möglicher
Grund: EN 61000-3-2 greift erst oberhalb **75 W Eingangsleistung**, und mit
66,1 W sind wir darunter geblieben. Ob bei Volllast eine aktive Stufe
zuschaltet, wäre mit 20 V / 5 A zu prüfen.

**Burst-Betrieb bei Teillast.** Bei 0,25 A schwankt die Leistung mit σ = 3,5 W
zwischen etwa 1 W und 11 W. Das ist kein Messrauschen, sondern Pulspaket-
Betrieb: Der Lader schaltet in Paketen und pausiert dazwischen. Die
Burst-Periode liegt dicht bei den 200 ms des Messfensters, weshalb im Log ein
langsam durchwanderndes Schwebungsmuster erscheint. **Die Burst-Frequenz
selbst ist mit diesem Gerät nicht auflösbar**; der Mittelwert bleibt korrekt,
weil das UMG lückenlos über alle Fenster misst.

### Ruhezustände des Laders

Vier unterschiedliche Zustände, die man nicht verwechseln darf:

| Zustand | mittlere Leistung | Signatur |
|---|---|---|
| Nichts angesteckt | **0,225 W** | konstant, σ = 0,02 |
| Trigger + Last dran, 0 A | **2,550 W** | Burst, σ = 3,15 |
| Trigger abgezogen | **0,445 W** | Puls alle 4,2 s, dazwischen 0,05–0,10 W |

Der mittlere Fall ist praktisch bedeutsam: **Ein Lader, an dem ein volles
Gerät hängt, zieht rund das Zehnfache eines Laders, an dem nichts steckt** —
der 20-V-Vertrag muss aufrechterhalten werden. Nicht abschließend getrennt
ist dabei der Eigenverbrauch der elektronischen Last bei 0 A.

Im dritten Zustand liegt der **Tiefschlaf bei 0,05–0,10 W**; die 0,445 W im
Mittel stammen fast ausschließlich aus den Pulsen der periodischen
USB-C-Anschlusserkennung.

**Offener Punkt:** Der erste Zustand zeigte 0,2251 W konstant ohne
Pulsspuren, der dritte 0,06 W mit Pulsen. Zwei verschiedene Ruhezustände
desselben Geräts, wofür keine belegte Erklärung vorliegt. Zu prüfen wäre, ob
der Lader nach längerer unberührter Zeit in einen anderen Zweig fällt.

**Messtechnische Anmerkung:** Durch den Entstörkondensator fließen dauerhaft
etwa 23 mA (≈ 0,31 µF X-Kondensator, aus I = U·2πf·C zurückgerechnet). Das
ist reine Blindleistung — 5,2 VA bei 0,22 W Wirkleistung, cosφ 0,043. Sie
kostet nichts, weil Zähler Wirkarbeit abrechnen, und sie stört die Messung
nicht: Wirkleistungen von 0,06 W sind trotz der 23 mA sauber auflösbar, weil
der Blindstrom in die Wirkleistung nicht eingeht. Die Rauschgrenze von rund
1 mA gilt für den Strom, nicht für die Leistung.

### Vier USB-Netzteile im Vergleich

Vier Ladegeräte, alle bei 5 V / 1 A gemessen, danach zwei davon zusätzlich an
ihrem eigenen Nennpunkt. Ausgangsspannung an der elektronischen Last
abgelesen, Ausgangsleistung daraus berechnet — die Spannungen weichen
zwischen den Geräten um bis zu 8 % ab.

| | Bauart | U<sub>aus</sub> | P<sub>aus</sub> | P<sub>ein</sub> | η | Abwärme | Leerlauf |
|---|---|---|---|---|---|---|---|
| 1 | China, USB-A, ohne PD | 5,141 V | 5,14 W | 6,81 W | **75,5 %** | 1,67 W | 0,137 W |
| 2 | Samsung/Apple, USB-C | 5,069 V | 5,07 W | 10,39 W | **48,8 %** | 5,32 W | 0,173 W |
| 3 | Samsung/Apple, USB-C | 4,947 V | 4,95 W | 10,30 W | **48,1 %** | 5,35 W | 0,161 W |
| 4 | China, USB-A, ohne PD | 5,413 V | 5,41 W | 7,18 W | **75,4 %** | 1,77 W | 0,121 W |

Dieselben Markengeräte an ihrem Nennpunkt, 9 V / 2 A (beide lassen sich nur
auf 9 V triggern):

| | P<sub>aus</sub> | P<sub>ein</sub> | η | λ | THD I |
|---|---|---|---|---|---|
| 2 | 18 W | 20,14 W | **89,4 %** | 0,491 | 173,0 % |
| 3 | 18 W | 20,21 W | **89,1 %** | 0,494 | 172,1 % |

**Die naheliegende Deutung der ersten Tabelle wäre falsch.** Sie zeigt nicht,
dass die China-Lader besser gebaut sind, sondern dass ein kleines Netzteil
nahe seinem Nennpunkt ein großes Netzteil weit darunter schlägt. Ein
USB-A-Lader ohne PD ist für 5–10 W ausgelegt und läuft bei 5 W im Optimum;
ein USB-C-Lader mit 25–45 W läuft dort bei 10–20 % Last, wo der feste
Eigenbedarf — Regler-IC, Hilfsspannung, ständig laufender PD-Controller —
den Wirkungsgrad auffrisst. Zudem ist 5 V für einen PD-Lader der ungünstigste
Ausgang, weil der Sperrwandler dort mit kleinstem Tastverhältnis arbeitet.

An denselben Geräten macht der Arbeitspunkt **über 40 Prozentpunkte** aus.
Der GaN-Lader zeigt dasselbe Muster: 67,9 % bei 5 W, 83,0 % bei 20 W, 90,8 %
bei 60 W.

Sinnvoll verglichen — jedes Gerät an einem für es passenden Punkt — steht es
so:

| | Arbeitspunkt | η |
|---|---|---|
| China-Lader 1 | 5,1 V / 1 A | 75,5 % |
| China-Lader 4 | 5,4 V / 1 A | 75,4 % |
| Samsung/Apple 2 | 9 V / 2 A | 89,4 % |
| Samsung/Apple 3 | 9 V / 2 A | 89,1 % |

**Was als praktische Aussage bleibt:** Wer über Nacht mit 5 V und 1 A lädt,
verliert mit dem großen Lader mehr Energie als mit dem kleinen. Das ist ein
realer Anwendungsfall — nur eben kein Urteil über die Bauqualität.

**Netzrückwirkung fällt nicht mit dem Wirkungsgrad zusammen.** Beide
Markenlader bleiben bei λ ≈ 0,49 und THD ≈ 173 %, und zwar unverändert
zwischen 10 W und 20 W Aufnahme — ein Kondensatoreingang ohne jede
Korrektur. Bei unter 75 W ist das normkonform (EN 61000-3-2), steht aber im
Gegensatz zum GaN-Lader, der bei 66 W auf λ 0,88 und THD 31 % kommt.
Wirkungsgrad und Netzverträglichkeit sind unabhängige Qualitätsmerkmale.

**Spannungshaltung:** USB erlaubt 5 V ±5 %, also 4,75–5,25 V. Kandidat 4
liegt mit 5,413 V darüber. Sein Wirkungsgrad hängt davon nicht ab —
Kandidat 1 erreicht denselben Wert bei spezifikationskonformen 5,14 V.

**Nebenbefunde:** Die Trigger-Platine kostet an einem 5-V-Lader rund
**72 mW** (0,091 W ohne, 0,164 W mit). Am GaN-Lader waren es 2,3 W, weil dort
ein 20-V-Vertrag aufrechterhalten werden muss — ein 5-V-Netzteil verhandelt
nichts. Die Nullreferenz der Messkette lag zu Beginn bei −0,0021 W und neun
Minuten später bei −0,0020 W: kein Nullpunktdrift.

### Oberschwingungsspektrum des GaN-Laders

Gemessen wurde der Netzstrom L1 bei drei Arbeitspunkten. Alle drei
Spektren sind gegen das THD-Register des Geräts gegengeprüft und stimmen
auf zwei Nachkommastellen überein.

| Ordnung | Leerlauf (0,4 W) | 20 V / 1 A (24 W) | 20 V / 3 A (67 W) |
|---|---|---|---|
| 1. (Grundschwingung) | 22,5 mA | 128,4 mA | 315,5 mA |
| 3. | 1,2 mA · 5 % | 46,3 mA · 36 % | 66,5 mA · 21 % |
| 5. | 2,0 mA · 9 % | 19,5 mA · 15 % | 62,3 mA · 20 % |
| 7. | 2,0 mA · 9 % | 19,1 mA · 15 % | 17,3 mA · 5 % |
| 9. | 1,7 mA · 8 % | 8,8 mA · 7 % | 17,2 mA · 5 % |
| 11. | 1,3 mA · 6 % | 13,5 mA · 11 % | 12,2 mA · 4 % |
| **THD** | **26,0 %** | **46,2 %** | **31,7 %** |

**Im Leerlauf ist der Strom fast ein reiner Sinus** — 97 % Grundschwingung.
Das bestätigt, dass die 22,5 mA praktisch vollständig vom X-Kondensator des
Entstörfilters stammen. Aus der Grundschwingung allein gerechnet ergibt sich
C = 22,515 mA / (232,25 V × 314,16 s⁻¹) = **0,308 µF**, passend zu einem
X2-Kondensator mit 0,33 µF Nennwert. Die verbleibenden 5–9 % bei der 5., 7.
und 9. Ordnung sind die 0,39 W Eigenverbrauch der Elektronik.

**Zwischen 1 A und 3 A wird das Spektrum umgeformt, nicht skaliert.** Die
Grundschwingung wächst um den Faktor 2,46, aber:

| Ordnung | Faktor |
|---|---|
| 1. | 2,46 |
| 3. | 1,44 |
| 5. | **3,20** |
| 7. | **0,91** |
| 9. | 1,97 |
| 11. | **0,91** |

Die 5. verdreifacht sich, während 7. und 11. bei zweieinhalbfacher Leistung
**absolut sinken**. Das ist mit keiner einfachen Erklärung vereinbar:

- Ein bloß **breiterer Stromflusswinkel** würde alle Ordnungen gleichmäßig
  gegenüber der Grundschwingung senken. Stattdessen steigt die 5. relativ von
  15 auf 20 %.
- Eine **aktive Leistungsfaktorkorrektur** würde das ganze Spektrum unter
  etwa 10 % drücken und den Klirrfaktor einstellig machen. Bei 31,7 % ist
  davon keine Rede.

Es bleibt: Der Wandler **wechselt bei höherer Last die Betriebsart** — etwa
vom lückenden in den nicht lückenden Betrieb. Die Stromform wird eine andere,
nicht bloß eine größere.

**Konsequenz für die Interpretation:** Der bessere Klirrfaktor bei 3 A ist
*kein* Beleg für eine Leistungsfaktorkorrektur. Wer nur die THD-Zahl
betrachtet, käme zum falschen Schluss. Mit 67 W Aufnahme liegt der Lader
zudem unter der 75-W-Schwelle, ab der EN 61000-3-2 überhaupt Grenzwerte
setzt — er *muss* nichts tun.

**Für die Verbrauchsmessung ändert das nichts.** Wirkungsgrad und
Wattzahlen bleiben, wie gemessen. Relevant wird die Ordnungsverteilung erst
bei der Bewertung von Netzrückwirkungen, wo die 3. und 5. sich anders
auswirken als die 7. oder 11.

### Referenzmessung: PTC-Klebepistole (nichtlineare Heizung)

Ein Verbrauchertyp, der weder ohmsch (Glühlampe) noch elektronisch geregelt
(Netzteile) ist: ein Heizelement mit stark temperaturabhängigem Widerstand.
`heisskleber.html` zeigt den Verlauf, `messungen/heisskleber.csv` die Daten.

**Kaltstart:**

```
 t=0 s   440 W   1,96 A   THD  8,4 %   ← Einschaltspitze, 10x Betrieb
 t=1 s    66 W   0,30 A   THD 24,5 %
 t=20 s   46 W   0,21 A   THD 25,4 %   ← Maximum
 Ende     27 W   0,12 A   THD 24,8 %   ← Selbstregelung, noch fallend
```

Drei Phänomene in einer Messung:

**PTC-Einschaltstrom.** Das kalte Element ist niederohmig und zieht das
Zehnfache des Betriebsstroms. Anders als der Glühlampen-Einschaltstrom
(≈ 100 ms, für dieses Gerät unsichtbar) klingt er über **rund eine Sekunde**
ab und fällt damit voll ins 200-ms-Raster.

**Der Klirrfaktor folgt der Steilheit der Kennlinie, nicht der Temperatur.**
Kalt liegt das Element auf dem flachen Teil der R(T)-Kurve — dR/dT klein,
kaum Verzerrung, 8 %. Im heißen, steilen Regelbereich wird der Widerstand
stark temperaturempfindlich; die mit 100 Hz pulsierende Leistung moduliert
ihn tief, und die **dritte Harmonische** springt auf 25 %. Das Spektrum ist
fast rein Grundschwingung + 3. Ordnung, gerade Ordnungen unter 0,2 % —
symmetrisch, also kein Gleichrichter; und cosφ bleibt durchgehend bei 0,99,
also kein Phasenanschnitt. Es ist reine thermische Modulation:

> I ∝ U · (1 + m·cos 2ωt) = cos ωt + (m/2)(cos ωt + **cos 3ωt**)

**PTC-Selbstregelung.** Ohne dass Kleber durchgeschoben wird, regelt sich die
Aufnahme über Minuten auf rund 27 W herunter — gerade genug, um die
Wärmeverluste zu decken.

Nebenbei der erste Lasttest des Steuergehäuses (RS485, Relais und
Bedienelemente in einem Kasten): 1101 Messpunkte durch den Schaltmoment
lückenlos, kein verlorener Wert. **Die Schaltstörung schlägt nicht auf die
Datenleitung durch.**

### Falle: Eigenversorgung der elektronischen Last

Die Versorgung der elektronischen Last gehört **nicht** in den gemessenen
Strompfad — und zwar nicht nur aus Sauberkeit, sondern weil sie sich nicht
herausrechnen ließe:

| Zustand der Last | Verlustleistung | Aufnahme ihrer Versorgung |
|---|---|---|
| aus | 0 W | 0,43 W |
| ein, kaum Strom | ~0 W | 1,80 W |
| 15 V / 3 A | 45 W | 2,07 W |
| 20 V / 4 A | 80 W | 3,24 W |

Der Faktor 7,5 zwischen aus und Volllast entsteht vollständig über den
**temperaturgeregelten Lüfter**: Die verheizte Leistung kommt aus dem
Prüfling und passiert die Versorgung nie, wärmt aber den Kühlkörper, worauf
der Lüfter hochdreht. Der Zusammenhang ist real, aber indirekt und
zeitverzögert — bei 45 W war nach vier Minuten nichts zu sehen, 80 W trieben
den Lüfter binnen anderthalb Minuten von 35 auf 65 %.

**Wer das für einen festen Offset hält, zieht den falschen Wert ab.** Bei
allen hier dokumentierten Messungen lag die Versorgung außerhalb; belegt
durch die Nullreferenz von −0,002 W am Anfang und am Ende der USB-Reihe.

## Installation

```bash
sudo apt install python3-serial
```

Der Benutzer muss in der Gruppe `dialout` sein:

```bash
sudo usermod -aG dialout $USER   # danach neu anmelden
```

## Verwendung

**Momentanwerte einmalig lesen:**

```bash
python3 umg_read.py
```

**Messreihe aufzeichnen:**

```bash
python3 umg_log.py                          # CSV nach stdout
python3 umg_log.py -o messung.csv
python3 umg_log.py -o messung.csv -d 3600   # eine Stunde
python3 umg_log.py -o messung.csv --reset-minmax
```

Der Logger tastet mit 100 ms über und verwirft unveränderte Blöcke. Damit
wird jede der alle 200 ms erzeugten Aktualisierungen genau einmal
aufgezeichnet, ohne dass die Aufzeichnung mit dem internen Takt des Geräts
synchron laufen muss. In der Praxis ergibt das ~5 Zeilen pro Sekunde.
Unveränderte Werte werden zusätzlich alle 60 s geschrieben (`--heartbeat`),
damit auch Stillstand belegt ist.

Zeitstempel kommen vom Rechner in ISO 8601 mit Zeitzone — das Grundgerät hat
keine Uhr. Nach dem Ende gibt der Logger die Spitzenwerte aus dem
Min/Max-Speicher des Geräts aus; mit `--reset-minmax` beziehen sie sich
sauber auf den aktuellen Durchlauf.

**Messreihe auswerten:**

```bash
python3 umg_segmente.py messungen/spielerei.csv
python3 umg_segmente.py messung.csv -c i_l1
python3 umg_segmente.py messung.csv --extra cosphi_l1,lambda_sum,thd_i_l1
```

Sucht Sprungstellen im Verlauf und gibt die dazwischenliegenden stabilen
Betriebspunkte mit Mittelwert und Streuung aus. Das Rauschmaß wird robust aus
den Differenzen aufeinanderfolgender Werte geschätzt, die Ansprechschwelle
liegt bei sechs Sigma (`-s` ändert das).

Verstellungen an einem Gerät erzeugen meist mehrere Sprünge kurz
hintereinander — Überschwingen, Korrektur, Nachjustieren. Sprünge im Abstand
von unter 8 Sekunden werden deshalb zu einem Ereignis zusammengefasst, und
als Betriebspunkte gelten nur die ruhigen Abschnitte dazwischen.

Gemessene Trennschärfe am Trafo-Netzteil: bei σ = 0,038 W wurden
Verstellungen ab 0,34 W sicher erkannt.

**Oberschwingungen auslesen:**

```bash
python3 umg_oberschwingungen.py              # U L1-N und I L1, 25 Ordnungen
python3 umg_oberschwingungen.py -k i_l1 -n 40
python3 umg_oberschwingungen.py --csv messungen/spektrum.csv
```

Gibt das Spektrum mit Balkendarstellung aus, absolut und in Prozent der
Grundschwingung. Der Klirrfaktor wird aus allen 40 Ordnungen berechnet und
**gegen das THD-Register des Geräts geprüft** — stimmen beide überein, ist die
Adressierung bestätigt. Das ist der billigste Selbsttest, den die
Registerkarte hergibt.

Gemessen an einem Schaltnetzteil ohne Korrektur:

```
I L1   Grundschwingung 1,9307 mA
    1.   1,9307 mA   100,00 %
    3.   1,6173 mA    83,77 %
    5.   2,1261 mA   110,13 %   <- groesser als die Grundschwingung
    7.   1,7427 mA    90,26 %
    9.   2,0254 mA   104,91 %

  THD aus Spektrum:  324,03 %
  THD aus Register:  324,03 %
```

Die geraden Ordnungen bleiben unter 15 % — Zeichen eines symmetrischen
Verbrauchers, bei dem sich positive und negative Halbwelle gleichen. Ein
einweggleichgerichteter Verbraucher hätte dort kräftige Anteile.

**Spektren vergleichen:**

```bash
python3 umg_grafik.py spektrum \
    messungen/spektrum_gan_leerlauf.csv \
    messungen/spektrum_gan_20v1a.csv \
    messungen/spektrum_gan_20v3a.csv \
    -o spektren.html --labels "Leerlauf;20 V / 1 A;20 V / 3 A" -n 15
```

Stellt mehrere mit `umg_oberschwingungen.py --csv` erzeugte Spektren
gegenüber, einmal in Prozent der Grundschwingung und einmal als absoluter
Strom. **Beide Ansichten sind nötig** — die Prozentansicht zeigt, woraus sich
der Klirrfaktor bildet, die Absolutansicht, was tatsächlich fließt. Bei
wachsender Grundschwingung erzählen sie verschiedene Geschichten.

**Live-Anzeige im Browser:**

```bash
python3 umg_live.py                          # http://localhost:8000
python3 umg_live.py --csv messungen/live.csv # zeichnet gleichzeitig auf
python3 umg_live.py --host 0.0.0.0           # auch im Netz erreichbar
```

Kleiner Webserver aus der Standardbibliothek. Ein Hintergrund-Thread liest das
UMG zyklisch aus, die Seite holt sich die Werte alle 400 ms und zeigt Kacheln
sowie eine rollende Kurve der Wirkleistung über 120 Sekunden.

**Der serielle Port ist exklusiv** — solange die Anzeige läuft, kann
`umg_log.py` nicht gleichzeitig aufzeichnen. Deshalb übernimmt die Anzeige das
mit `--csv` selbst, im gleichen Format wie der Logger, inklusive Dedup.

Voreinstellung ist `127.0.0.1`, also nur vom eigenen Rechner erreichbar.
`--host 0.0.0.0` macht die Anzeige im ganzen Netz sichtbar; das ist bewusst
nicht die Vorgabe.

**Grafiken erzeugen:**

```bash
# Zeitverlauf aus einer Logdatei
python3 umg_grafik.py verlauf messungen/usb_vergleich.csv -o verlauf_usb.html \
    --phasen messungen/usb_phasen.json --titel "..." --max 22 --zoom 0.3

# Gestapelte Balken aus einer Beschreibung der Arbeitspunkte
python3 umg_grafik.py vergleich messungen/wirkungsgrad.json -o wirkungsgrad.html
```

Erzeugt eigenständige HTML-Dateien ohne externe Abhängigkeiten — CSS und
JavaScript inline, Daten einkopiert. Lokal im Browser zu öffnen und ohne Netz
weiterzugeben; die Artefakt-Umgebung blockiert externe Anfragen, deshalb kommt
keine Chart-Bibliothek zum Einsatz.

Mehrere `-c`-Spalten ergeben je ein Panel auf gemeinsamer Zeitachse, `--marke`
setzt eine senkrechte Markierung:

```bash
python3 umg_grafik.py verlauf messungen/heisskleber.csv \
    -c p_sum -c thd_i_l1 --marke "16.0:Last ein" -o heisskleber.html
```

`verlauf` liest die CSV direkt und verdichtet sie auf etwa 1100 Punkte
(Mittelwert je Zeitfenster), damit die Datei klein bleibt. `--zoom` fügt ein
zweites Panel mit kleinerer y-Achse an — nötig, wenn Leerlauf und Volllast
mehr als zwei Zehnerpotenzen auseinanderliegen. Mit `--phasen` werden die
ausgewerteten Plateaus grau hinterlegt.

`vergleich` liest eine JSON-Beschreibung; eine Datei kann mehrere Diagramme
mit je eigener Skala enthalten. Der Wirkungsgrad wird als erster Wert geteilt
durch die Summe gerechnet, die erste Reihe muss also die Nutzleistung sein.
Beispiel: `messungen/wirkungsgrad.json`.

Die Farbpalette ist gegen Farbfehlsichtigkeit und Kontrast geprüft; ihre
Reihenfolge ist Teil der Prüfung und sollte nicht umsortiert werden.

**Konfigurationsparameter lesen und schreiben:**

```bash
python3 umg_param.py 45              # lesen
python3 umg_param.py 45 0            # schreiben
python3 umg_param.py -f 10           # FLOAT-Parameter lesen
python3 umg_param.py -f 10 100       # FLOAT-Parameter schreiben
```

Schreibzugriffe verändern die Gerätekonfiguration dauerhaft. Der alte Wert
wird vor dem Schreiben ausgegeben.

## Registeradressen

Messwerte als **float32, Big Endian**, ab Adresse 19000:

| Adresse | Wert |
|---|---|
| 19000 / 19002 / 19004 | Spannung L1-N / L2-N / L3-N |
| 19006 / 19008 / 19010 | Spannung L1-L2 / L2-L3 / L1-L3 |
| 19012 / 19014 / 19016 | Strom L1 / L2 / L3 |
| 19018 | Vektorsumme IN |
| 19020 / 19022 / 19024 | Wirkleistung L1 / L2 / L3 |
| 19026 | Wirkleistung Summe |
| 19028–19034 | Scheinleistung L1 / L2 / L3 / Summe |
| 19036–19042 | Blindleistung L1 / L2 / L3 / Summe |
| 19044–19048 | CosPhi L1 / L2 / L3 |
| 19050 | Frequenz |
| 19052 | Drehfeld (1 = rechts, 0 = keins, −1 = links) |
| 19054–19060 | Wirkarbeit L1 / L2 / L3 / gesamt |
| 19068 | Wirkarbeit bezogen |
| 19076 | Wirkarbeit geliefert |
| 19110–19120 | THD U L1–L3, THD I L1–L3 |

Ein zweiter Block bietet dieselben Größen ab Adresse 800 (Frequenz 800,
Spannungen 808–812, Ströme 860–864, Leistungen 868–874). **Dieser Block ist
für Komparatoren relevant**, weil am Gerät nur dreistellige Adressen
eingebbar sind.

### Funktionscodes

Dokumentiert und vom Gerät unterstützt: **03** (Halteregister lesen), **04**
(Eingangsregister lesen), **06** (ein Register schreiben), **16** (mehrere
schreiben), **23** (lesen und schreiben in einem Telegramm).

Janitza dokumentiert für Messwerte **FC 04**. FC 03 funktioniert in der
Praxis ebenfalls, ist aber nicht zugesichert.

**FC 23** ist als `read_write_registers()` in `umg_read.py` implementiert. Am
Gerät gemessen: **17,6 ms gegen 46,2 ms** für dieselbe Operation als
`06` + `04`, also 62 % gespart. Das Gerät schreibt zuerst und liest danach;
zurück kommt der Zustand **nach** dem Schreibzugriff. Beschreibbar sind nur
Halteregister — Messwerte sind Eingangsregister und lassen sich damit lesen,
aber nicht setzen.

Lohnend wird das erst, wenn der Messplatz zyklisch **steuert**: etwa die
Digitalausgänge direkt vom Rechner schalten (Parameter `200` = 2, dann
laufend auf Register `602` schreiben) und in derselben Schleife die Messwerte
holen. Solange nur gelesen wird, bringt er nichts.

## Oberschwingungen

Das Gerät führt eine Fourieranalyse bis zur **40. Oberschwingung** für Spannung
und Strom durch, gerade und ungerade Ordnungen gleichermaßen, ohne Lücken.

**Die Indizierung ist die Stolperstelle:** Der Index zählt ab null, die Ordnung
ab eins. Adressliste S. 9: `xxx[0]` = Netzfrequenz, `xxx[1]` = 2. Oberschwingung,
`xxx[2]` = 3. Oberschwingung. Index 0 ist also die **Grundschwingung**, nicht
die zweite Harmonische.

### Float-Block (Wandlerverhältnisse eingerechnet)

Adresse = `1000 + 80 × Kanal + 2 × (Ordnung − 1)`, Kanal 0–8 in dieser
Reihenfolge:

| Kanal | Größe | von | bis | Einheit |
|---|---|---|---|---|
| 0 | U L1-N | 1000 | 1078 | V |
| 1 | U L2-N | 1080 | 1158 | V |
| 2 | U L3-N | 1160 | 1238 | V |
| 3 | U L1-L2 | 1240 | 1318 | V |
| 4 | U L2-L3 | 1320 | 1398 | V |
| 5 | U L3-L1 | 1400 | 1478 | V |
| 6 | I L1 | 1480 | 1558 | A |
| 7 | I L2 | 1560 | 1638 | A |
| 8 | I L3 | 1640 | 1718 | A |

40 Ordnungen × 2 Register = 80 Register je Kanal, alle FLOAT, nur lesbar.
Beispiel: 5. Oberschwingung des Stroms L1 = 1480 + 2 × 4 = **1488**.

### Weitere Blöcke, gleiche Geometrie

| Block | Spannung | Strom | Zugriff |
|---|---|---|---|
| Momentanwert, float | 1000–1478 | 1480–1718 | RD |
| Mittelwert, float | 1740–2218 | 2260–2498 | RD |
| Maximum, float | 2598–3076 | 3118–3356 | RD/**WR** |
| Momentanwert, short | 3536–3775 | 3796–3915 | RD |
| Mittelwert, short | 3966–4205 | 4226–4345 | RD |
| Maximum, short | 4395–4634 | 4655–4774 | RD/**WR** |

Die Maximumblöcke sind schreibbar, lassen sich also einzeln zurücksetzen.

**Vorsicht bei den short-Blöcken:** Zwischen Spannungs- und Stromgruppe liegen
20 Register Lücke (3776–3795 enthält THD-Skalare), die Schrittweite ist also
nicht durchgehend. Außerdem sind dort die **Wandlerverhältnisse nicht
eingerechnet**, und der gesamte Bereich 3526–4851 ist über Profinet nicht
lesbar — über RS485 schon. Für portablen Code die Float-Blöcke nehmen.

### Absolutwerte, keine Prozente

Oberschwingungen kommen in **V, A bzw. mA** — einen Prozentblock gibt es
nicht. Handbuch S. 51: *„Die Oberschwingungen für die Ströme werden in Ampere
und die Oberschwingungen der Spannungen in Volt angegeben."* Prozent vom
Grundton muss man selbst gegen Index 0 rechnen.

### THD und TDD

**THD** setzt die Oberschwingungen ins Verhältnis zur **Grundschwingung**:

> THD = √(I₂² + I₃² + …) / I₁

Werte über 100 % sind damit möglich und normal — an einem Schaltnetzteil ohne
Korrektur wurden hier 324 % gemessen. Das Gerät rechnet ausschließlich so
(THD-F); die Variante THD-R, die auf den Effektivwert bezieht und nie über
100 % gehen kann, ist in den technischen Daten S. 86/87 ausdrücklich als
**nicht unterstützt** gekennzeichnet. Entsprechende Register gibt es nicht.

**Das Problem:** THD sagt nichts darüber, wie sehr ein Verbraucher die Anlage
belastet. Die 324 % stammten von einem Gerät mit 2 mA Stromaufnahme — der
gesamte Oberschwingungsanteil betrug 6 mA und stört niemanden. Umgekehrt wäre
ein Verbraucher mit 8 % THD bei 200 A ein ernsthaftes Problem.

**TDD** behebt das, indem es auf den **Nennstrom der Anlage** bezieht statt
auf den eigenen Grundton:

> TDD = √(I₂² + I₃² + …) / I_nenn

Damit werden Verbraucher vergleichbar, und die Kennzahl beantwortet die
Frage, die zählt: belastet dieses Gerät das Netz?

#### Register

Der Zugriff über 19110–19120 ist richtig, aber ein Auszug. Der vollständige
Block liegt bei 836 ff. und enthält zwei Größen, die im 19000er-Block fehlen:

| Adresse | Größe |
|---|---|
| 836 / 838 / 840 | THD U L1-N / L2-N / L3-N |
| **842 / 844 / 846** | **THD U L1-L2 / L2-L3 / L3-L1** |
| 908 / 910 / 912 | THD I1 / I2 / I3 |
| **914 / 916 / 918** | **TDD I1 / I2 / I3** |

TDD ist nur sinnvoll mit korrekt gesetztem Parameter `043`. Werkseinstellung
150 A — hier **auf 5 A gesetzt**, passend zum Wandlernennstrom.
Kontrollrechnung an einem Kleinverbraucher:

```
Strom L1     0,02283 A
THD I1         12,24 %     bezogen auf die Grundschwingung
TDD I1          0,0555 %   bezogen auf 5 A
Probe: THD x I1 / 5 A = 0,0559 %
```

Parameter `511` (0 = L-N, 1 = L-L) betrifft laut Adressliste nur die
**Anzeige** von THD und FFT am Gerät, nicht die Modbus-Register — die haben
für L-N und L-L eigene, dauerhaft gültige Adressen.

### Messgrundlage

Dasselbe 200-ms-Fenster wie alle anderen Werte, lückenlos. Genauigkeit für
Spannungs- und Stromoberschwingungen: **Klasse 1 nach IEC 61000-4-7 bis
2,5 kHz**. Das deckt die 40. Ordnung bei 50 Hz (2000 Hz) ab.

**Widerspruch in den Dokumenten:** Handbuch S. 12 nennt Oberschwingungen nur
„für ULN und I", die Adressliste führt aber L-L-Register bei 1240–1478. Die
Adressliste ist das speziellere Dokument; die L-L-Werte sollten beim ersten
Auslesen trotzdem gegen eine bekannte Last geprüft werden.

## Bisher ungenutzte Möglichkeiten des Geräts

Die folgenden Funktionen sind dokumentiert, in diesem Projekt aber noch nicht
verwendet. Angaben aus der Modbus-Adressliste bzw. dem Handbuch; wo etwas
nicht belegt ist, steht es dabei.

**Tarifaufgelöste Energiezähler**, Adressen 5000–5446 (float, RD/WR) und
5448–5894 (int32, RD). Acht getrennte Zähler je Größe, zwei Register pro
Wert. Für einen Prüfplatz interessant: statt den Zähler zwischen zwei
Prüflingen zu löschen, ließe sich der Tarif umschalten — am Ende stehen acht
Verbrauchssummen nebeneinander.

Die Umschaltung erfolgt über die Register **618–624** (SHORT, RD/WR, 0–127),
je eines pro Größe: 618 Wirkarbeit, 619 bezogen, 620 geliefert, 621 Blind,
622 induktiv, 623 kapazitiv, 624 Schein. Kein Index, sondern eine
**Bitmaske** — Tarife lassen sich gleichzeitig laufen, und **Tarif 0 zählt
immer mit**, unabhängig von der Einstellung. Der float-Block ist RD/WR und
damit vorbelegbar, der int32-Block nur lesbar.

**Impulsausgang S0** an den Digitalausgängen. Parameter `102` und `104` legen
die Wertigkeit fest — **Wh oder varh**, je nachdem welche Größe dem Ausgang
zugewiesen ist (Werk: 1000). Das Vorzeichen ist bedeutsam: positiv gibt nur
bei positiven Messwerten Impulse aus, negativ nur bei negativen. `106` setzt
die Mindestimpulslänge in 10-ms-Schritten, Bereich 1–1000, also 10 ms bis
10 s (Werk: 5, also 50 ms), maximal 50 Hz. Damit könnte ein
externer Zähler mitlaufen.

**Mittelwerte mit einstellbarem Fenster** — Parameter `040` (Strom), `041`
(Leistung), `042` (Spannung). Kein Sekundenwert, sondern ein Index 0–8:

| 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| 5 s | 10 s | 15 s | 30 s | 1 min | 5 min | **8 min** | 10 min | 15 min |

Werkseinstellung ist 6, also 8 Minuten. Die Mittelung ist **exponentiell,
kein gleitendes Blockmittel** — Handbuch S. 48: „erreicht nach der
eingestellten Mittelungszeit mindestens 95 % des Messwertes". Daraus folgt
eine Zeitkonstante von etwa einem Drittel des Nennfensters.

Das erklärt einen Befund aus der ersten Messreihe: Register 3510 meldete
14,12 W als Maximum, obwohl der Logger 15,6 W über 14 Sekunden gesehen hatte.
Bei τ ≈ 160 s hebt ein Sprung von 1,5 W über 14 s den Mittelwert nur um
1,5 × (1 − e^(−14/160)) = 0,13 W. Das Register hat korrekt gerechnet, das
Fenster war für die Fragestellung zu lang. **Für Prüfstandsbetrieb `040` und
`041` auf 0 setzen** (5 s), dann werden die geräteinternen Maximalwerte auch
für kurze Lastspitzen brauchbar.

**Integer-Blöcke** ab 4385 (short) und 5448 (int32) liefern dieselben Größen
als Ganzzahl. Kein Quantisierungsproblem bei großen Zählerständen — die
float32-Auflösung betrug bei 150 MWh immerhin 16 Wh. Dafür sind in den
short-Werten die Wandlerverhältnisse **nicht** eingerechnet.

**Little-Endian per Adressoffset:** auf jede Adresse 32768 addieren, dann
liefert das Gerät die Bytefolge andersherum. Nützlich für Bibliotheken, die
nur eine Reihenfolge beherrschen. Sauber belegt ist das für die Blöcke
unterhalb 4851; **ob es auch für die 19000er-Adressen gilt, sagen die
Dokumente nicht** — nicht ungeprüft annehmen.

**Komparator-Laufzeitzähler** auf 5898–5908, INT32 in Sekunden, nur lesbar,
Schrittweite 2. Sechs Einträge: vermutlich [0]–[2] für Gruppe 1 A/B/C und
[3]–[5] für Gruppe 2 — *die Adressliste beschriftet die Indizes nicht, das
wäre vor produktivem Einsatz zu prüfen.* Direkt darüber auf 5896 liegt der
Betriebsstundenzähler, ebenfalls in Sekunden.

**Was das Gerät nicht kann:** Gleichstrom, Vorgänge unterhalb des
200-ms-Messfensters, Zeitstempel (das Grundgerät hat keine Uhr) und
Datenaufzeichnung im Gerät.

## Komparatoren und Digitalausgänge

Zwei Vergleichergruppen mit je drei Vergleichern (A/B/C), UND- oder
ODER-verknüpfbar. **Gruppe 1 ist fest dem Digitalausgang 1 zugeordnet**,
Gruppe 2 dem Ausgang 2. Eine Hysterese gibt es nicht — nur Vorlaufzeit
(Bedingung muss anstehen) und Mindesteinschaltzeit (Nachhaltezeit), beide in
ganzen Sekunden.

Parameter je Vergleicher — die Adressabstände sind **unregelmäßig**, nicht
berechnen:

| | 1A | 1B | 1C | 2A | 2B | 2C |
|---|---|---|---|---|---|---|
| Grenzwert (float) | 108 | 114 | 120 | 127 | 133 | 139 |
| Adresse des Messwerts | 110 | 116 | 122 | 129 | 135 | 141 |
| Mindesteinschaltzeit (s) | 111 | 117 | 123 | 130 | 136 | 142 |
| Vorlaufzeit (s) | 112 | 118 | 124 | 131 | 137 | 143 |
| Operator | 113 | 119 | 125 | 132 | 138 | 144 |

Operator `0` = ≥, `1` = <. Messwertadresse `0` schaltet den Vergleicher
inaktiv. Verknüpfung der Gruppe über `107` bzw. `126` (`1` = UND, `0` = ODER).

Ausgangsrouting:

| Parameter | Bedeutung | Werk |
|---|---|---|
| `200` / `202` | Quelle Digitalausgang 1 / 2 | **1** |
| `201` / `203` | Invertierung | 0 |

Quelle: `0` = Vergleichergruppe, `1` = Impulsausgang, `2` = Modbus. Die
Werkseinstellung `1` ist die häufigste Fehlerquelle — siehe unten.

Ergebnisse auslesbar über `610`–`612` (Gruppe 1 A/B/C), `613`–`615`
(Gruppe 2), `616`/`617` (Verknüpfungsergebnis), `608`/`609` (Zustand der
Ausgänge).

### Komparator einrichten — erprobte Prozedur

Am Gerät durchgespielt und in allen Gliedern nachgewiesen. Beispiel:
Wirkleistungssumme über 30 W, ohne Verzögerung.

```
110 = 874     Messwert: Wirkleistungssumme (800er-Block!)
108 = 30.0    Grenzwert, FLOAT ueber zwei Register
113 = 0       Operator: groesser gleich
112 = 0       Vorlaufzeit in Sekunden
111 = 0       Mindesteinschaltzeit in Sekunden
116 = 0       Vergleicher 1B inaktiv
122 = 0       Vergleicher 1C inaktiv
107 = 0       ODER-Verknuepfung
200 = 0       Quelle Ausgang 1: Vergleichergruppe
201 = 0       nicht invertiert
```

**Die Messwertadresse bezieht sich auf den 800er-Block**, nicht auf die
19000er: Strom L1 = `860`, Wirkleistungssumme = `874`, Strom im
Neutralleiter = `866`. Nur dreistellige Adressen sind am Gerät eingebbar.

**`200` steht ab Werk auf `1`** (Impulsausgang). Ohne `200 = 0` schaltet der
Komparator nichts, egal wie sorgfältig er eingestellt ist. Das ist die
häufigste Fehlerquelle.

Zurücksetzen: `110 = 0` und `200 = 1`.

#### Gemessene Umschaltpunkte

```
 0,04 s   23,098 W   1A=0  Ausgang=0
 9,00 s   31,470 W   1A=1  Ausgang=1
15,00 s   28,474 W   1A=0  Ausgang=0
```

Vergleicherergebnis (610), Verknüpfung (616) und Ausgangszustand (608)
springen im selben Zyklus.

**Es gibt keine Hysterese.** Ausgelöst wurde bei 31,5 W, abgefallen bei
28,5 W — beides schlicht die Werte, die beim Überqueren der 30-W-Marke
anstanden. Das Gerät schaltet in beide Richtungen exakt am Grenzwert. Bei
einer Last, die um die Schwelle pendelt, flattert der Ausgang entsprechend.
**Die Mindesteinschaltzeit ist deshalb kein Komfortmerkmal, sondern das
einzige Mittel gegen dieses Flattern.** Für den Schutzkreis sind
Vorlaufzeit 1 s und Mindesteinschaltzeit 120 s die sinnvollen Werte, nicht
die Nullen aus dem Testaufbau.

#### Ohne Außenbeschaltung testen

Zwei Wege, beide erprobt:

**Statusregister lesen** — 610 (Vergleicher), 616 (Verknüpfung), 608
(Ausgang). Braucht keinerlei Verdrahtung.

**Am Display** — die Kreise hinter `K1` und `K2` zeigen den Zustand der
Digitalausgänge und füllen sich beim Durchschalten. Achtung: Die Anzeige
wird nur **einmal pro Sekunde** aktualisiert, schnellere Wechsel sind dort
nicht sichtbar; über Modbus schon.

**Den Halbleiter selbst prüfen** geht mit dem Multimeter im **Ohm-Bereich**
zwischen Klemme 13 und 14, ohne externe Spannung. Ein PhotoMOS leitet
symmetrisch bis herunter zu null Volt, die Prüfspannung des Multimeters
genügt also. Gesperrt: Überlauf. Durchgeschaltet: einige zehn Ohm — **nicht**
nahe null wie bei einem mechanischen Kontakt. Den Durchgangspiepser nicht
verwenden, dessen Schwelle liegt je nach Gerät genau im Bereich des
Einschaltwiderstands.

Alternativ mit externer Spannung: Vorwiderstand von 1 kΩ gegen 20 V ergibt
20 mA, sicher unter der 50-mA-Grenze. **Der Vorwiderstand ist Pflicht** — der
Ausgang ist nicht kurzschlussfest.

### Elektrische Daten der Digitalausgänge

Technische Daten S. 83:

| | |
|---|---|
| Typ | Halbleiterrelais, optokopplergetrennt, **nicht kurzschlussfest** |
| Schaltspannung | max. 33 V AC, 60 V DC |
| Schaltstrom | max. 50 mA<sub>eff</sub> AC/DC |
| Reststrom offen | < 1 mA |
| **Reaktionszeit** | **10/12 Perioden + 10 ms** = 210 ms bei 50 Hz |

Eine **externe Hilfsspannung ist erforderlich**. Beide Ausgänge teilen sich
den Bezug auf Klemme 13, sind also nicht gegeneinander getrennt. Leitungen
über 30 m müssen geschirmt sein.

Das Handbuch zeigt auf S. 36 ausdrücklich den Anschluss zweier Relaisspulen
an 24 V AC/DC. Die Spule muss ≤ 50 mA ziehen — bei 24 V DC also ≥ 480 Ω
bzw. ≤ 1,2 W. Viele Industrie-Koppelrelais liegen darüber, Datenblatt
prüfen.

Eine **Freilaufdiode wird nirgends erwähnt** und ist in der Zeichnung nicht
enthalten. Der Ausgang ist ein bidirektionaler AC/DC-fähiger Halbleiter-
schalter; bei einer DC-Spule ist eine Schutzbeschaltung trotzdem gute
Praxis.

Wegen der 210 ms Reaktionszeit ist eine Komparator-Abschaltung **kein
Kurzschlussschutz**, sondern greift nur gegen dauerhafte Überschreitung.

#### Was sich mit 50 mA treiben lässt

Bei 24 V sind 50 mA gerade **1,2 W**. Die Auslegung geht über den
Spulenwiderstand:

> I = U / R, oder aus der Spulenleistung: I = P / U

Bei 24 V heißt das: **Spulenwiderstand mindestens 480 Ω**, Spulenleistung
höchstens 1,2 W.

| passt | typischer Strom bei 24 V |
|---|---|
| Schmale Koppelrelais (6 mm Reihenklemme) | 10–20 mA (0,25–0,5 W Spule) |
| SPS-Digitaleingänge | 5–10 mA |
| LED-Meldeleuchten | 10–20 mA |
| Piezo-Summer | 5–20 mA |
| S0-Zählereingänge nach DIN 43864 | 10–27 mA |

| passt nicht | warum |
|---|---|
| Schütze direkt | mehrere Watt Haltestrom, ein Vielfaches beim Anziehen |
| Magnetventile, Lampen, Lüfter, Motoren | Größenordnungen darüber |
| Ältere Industrierelais | 24-V-Spulen oft mit 40–100 mA — Datenblatt prüfen, die Bauform sagt nichts über die Spule |

**Zwei Fallen:**

*Einschaltstromspitzen bei kapazitiven Lasten.* Eine Relaisspule ist
unkritisch, weil der Strom in einer Induktivität von null aus ansteigt. Ein
SPS-Eingang mit Eingangsfilter oder ein kleines Netzteil zieht im ersten
Moment aber deutlich mehr als im Betrieb — und der Ausgang ist nicht
kurzschlussfest. Diese Spitze steht in keinem Datenblatt.

*Der Reststrom von unter 1 mA im gesperrten Zustand.* Bei einer Relaisspule
egal. Bei einem hochohmigen Eingang nicht unbedingt: Liegt dessen
Umschaltschwelle niedrig, könnte er den Reststrom bereits als eingeschaltet
lesen. Bei SPS-Eingängen steht die Schwelle im Datenblatt, meist bei 2 mA
oder darüber.

**Für den Prüfplatz** heißt das: Koppelrelais nicht nach
Kontaktbelastbarkeit auswählen — die reicht bei allen —, sondern nach der
**Spulenleistung unter 1,2 W bei 24 V**, mit Öffnerkontakt für den
Haltekreis.

S. 37: Klemme 13 als Funktionserde mit PE verbinden, um Restspannungs-
anzeigen zu vermeiden; Leitungsfarbe rosa nach DIN EN 60445.

## Fehlersuche

**Keine Antwort, nur Timeouts.** Das UMG antwortet auf ungültige Register-
adressen **gar nicht**, statt eine Modbus-Exception zu schicken. Ein Timeout
ist deshalb kein Hinweis auf ein Verkabelungsproblem. Erst gegen Register
**19050** testen — das muss rund 50 Hz liefern. Bleibt auch das still, sind
Adresse, Baudrate und Verkabelung zu prüfen.

**mbpoll zählt Register 1-basiert.** Ohne die Option `-0` fragt `-r 19000` in
Wirklichkeit Protokolladresse 18999 ab. Die Adressen der Janitza-Doku sind
roh und nullbasiert:

```bash
mbpoll -0 -a 2 -b 38400 -P none -s 1 -t 3 -r 19050 -c 2 -1 /dev/ttyUSB0
```

**Werte sehen aus wie Zufallszahlen.** Dann stimmt die Wortreihenfolge nicht.
Janitza liefert Big Endian; `mbpoll -t 3:float` dekodiert Little Endian.
Alternativ lässt sich auf jede Adresse **32768 addieren**, dann sendet das
Gerät Little Endian.

**Ströme lesen 0.** Erst Wandlerverhältnis (`010`/`012`) prüfen, dann die
Ansprechschwelle (`045`).

**Adapter prüfen.** Ein TXD/RXD-Loopback auf der RS232-Seite testet nur den
RS232-Zweig und sagt nichts über RS485 aus. Für RS485 gibt es keinen
Selbsttest — der einzige Beweis ist eine gültige Antwort vom Gerät.

**USB-Latenz.** Der FTDI-Latenztimer steht per Default auf 16 ms und kostet
das bei jedem Umlauf. Ein voller Lesevorgang über 52 Register dauert damit
median 47 ms, ohne ihn rund 32 ms:

```bash
echo 1 | sudo tee /sys/bus/usb-serial/devices/ttyUSB0/latency_timer
```

## Quellen

Die Originaldokumente liegen in `doku/`:

| Datei | Dokument |
|---|---|
| `handbuch-umg96rm-de.pdf` | Betriebsanleitung, Dok. 1.040.126.1.a, 10/2023, 134 S. |
| `handbuch-umg96rm-en.pdf` | dieselbe, englisch |
| `handbuch-umg96rm-de-2019.pdf` | ältere Ausgabe 1.040.126.0.h, 01/2019 — zum Abgleich |
| `modbus-adressliste-umg96rm-en.pdf` | Modbus-Adressliste, Dok. 1.040.034.t, 01/2023, 122 S. |

**Lokal aufbewahren, nicht nur verlinken:** Die Download-URLs enthalten
`/current/` — Janitza ersetzt die Datei dort bei jeder Revision. Ein Link
zeigt also irgendwann auf ein anderes Dokument als das, aus dem hier zitiert
wird. Die Dokumentnummern oben sind die verbindliche Angabe.

Ursprungs-URLs:
[Handbuch](https://www.janitza.de/files/download/manuals/current/UMG96RM/Basic/janitza-bhb-umg96rm-de.pdf) ·
[Adressliste](https://www.janitza.com/files/download/manuals/current/UMG96RM/Basic/janitza-mal-umg96rm-en.pdf)

### Wo die RS485-Schnittstelle beschrieben ist

Es gibt **kein eigenes Schnittstellendokument**. Die Beschreibung verteilt
sich auf beide Dateien:

| Thema | Fundstelle |
|---|---|
| Klemmen 16/17, Anschlussplan | Handbuch S. 106 |
| Abschlusswiderstände, Kabeltyp, Segmentlänge | Handbuch S. 33 |
| Adresse, Baudrate, Stoppbits am Gerät einstellen | Handbuch S. 47 |
| Modbus-Eigenheiten: Bytefolge, Telegrammlänge, Adressbereiche | Handbuch S. 61 |
| Technische Daten der Schnittstelle | Handbuch S. 89 |
| Unterstützte Funktionscodes (03, 04, 06, 16, 23) | Adressliste S. 4 |
| Bytefolge und Little-Endian-Offset +32768 | Adressliste S. 5 |
| Messfenster 200 ms, Aktualisierungsrate | Adressliste S. 6 |
| Vollständige Registerkarte | Adressliste S. 7 ff. |
