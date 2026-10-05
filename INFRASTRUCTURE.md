# Betrieb der AFJD-App

Streamlit bleibt die Oberfläche. Ohne zusätzliche Konfiguration bleibt die
vorhandene SQLite-Datenbank aktiv; vorhandene IDs, Zugangscodes und Kontakte
werden durch dieses Update nicht ersetzt.

## Was dieses Update verbessert

- SQLite im WAL-Modus; Transaktionen schützen gleichzeitige Scans und Ziehungen.
- Datenbankzustand wird innerhalb einer Sitzung nur bei neuer Revision erneut
  dekodiert. Lesezugriffe serialisieren den Zustand nicht mehr zum Vergleich.
- Teilnehmerprüfung alle 10 Sekunden statt 2 Sekunden, ohne Schreibsperre.
  Änderungen fremder Personen lösen keine vollständige Aktualisierung aus.
  Eigene Aktionen bleiben unmittelbar sichtbar.
- Leinwand alle 3 Sekunden; Countdown und Animation laufen im Browser weiter.
- Ein Prozess pro App prüft Termine alle 5 Sekunden, statt jeder Teilnehmerseite.
- Bereits geprüfte öffentliche Badge-QR-Grafiken werden begrenzt zwischengespeichert.
- Optional PostgreSQL mit maximal 8 Verbindungen pro App-Prozess. Veranstaltungsdaten,
  Login-Tokens, Anmeldeversuche und Versandbelege liegen dann gemeinsam dort.
  Schreibtransaktionen verwenden eine gemeinsame PostgreSQL-Transaktionssperre;
  der Veranstaltungszustand bleibt vorerst ein JSON-Datensatz.

## Dauerhafte Datenbank in Streamlit Secrets

Eine leere PostgreSQL-Datenbank bei einem geeigneten Anbieter bereitstellen.
Zugangsdaten nicht in GitHub oder Chat einfügen. In Streamlit unter App Settings →
Secrets diesen Eintrag **vor** dem bestehenden `[email]`-Abschnitt ergänzen:

```toml
QUEST_DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require"

[email]
# Bestehende Mailkonfiguration unverändert beibehalten.
```

Der Zugang muss Tabellen erstellen und Daten lesen/schreiben dürfen. Backups beim
Datenbankanbieter aktivieren. TLS-Zertifikatsprüfung nach dessen Vorgaben konfigurieren.
Die URL wechselt den gesamten Speicherort; sie kopiert bestehende SQLite-Daten
**nicht automatisch**. Bei einer leeren Datenbank erscheinen zunächst die
Standard-Testzugänge. Vor dem Wechsel vorhandene Daten migrieren, nicht während
des laufenden Events umschalten. Eine nicht erreichbare konfigurierte Datenbank
führt zu einem Fehler; es gibt keinen stillen Rückfall auf leere lokale Daten.

## Bestehende Daten übernehmen

Während der Migration die App für Änderungen stoppen. Eine konsistente Kopie der
SQLite-Datei einschliesslich aller Tabellen sichern (SQLite-Backupfunktion verwenden,
nicht nur die Hauptdatei während laufender WAL-Schreibzugriffe kopieren). Das Skript
`scripts/migrate_quest_database.py` kopiert alle vier App-Tabellen in eine leere
PostgreSQL-Datenbank. Ein bestehendes Ziel wird nicht überschrieben:

```powershell
python scripts/migrate_quest_database.py --source /private/event.sqlite3 --secrets /private/secrets.toml
python scripts/migrate_quest_database.py --source /private/event.sqlite3 --secrets /private/secrets.toml --apply
```

Der erste Aufruf prüft nur. Nach erfolgreicher Migration Secrets der App umstellen,
neu starten und Anmeldung, Kontakte und Gewinnbestand kontrollieren. SQLite-Sicherung
privat behalten. Keine Datenbank oder Secrets ins Repository aufnehmen.

## E-Mails unabhängig von Streamlit auslösen

Der eingebaute Worker arbeitet nur solange der App-Prozess läuft. Für verlässlichen
Versand auch bei schlafender/neustartender Streamlit-App einen externen geplanten
Job mit derselben PostgreSQL-Datenbank und Mailkonfiguration einrichten:

```powershell
python scripts/run_quest_worker.py --secrets /private/secrets.toml --once
```

Zum Beispiel jede Minute ausführen; ohne `--once` läuft ein dauerhafter Worker.
Diese Bereitstellung ist nicht automatisch enthalten. Gleichzeitige Worker beanspruchen
Nachrichten atomar. SMTP kann keine exakt-einmalige Zustellung garantieren: Bei
Abbruch nach Beanspruchung bleibt eine Nachricht zur manuellen Prüfung stehen,
statt automatisch eine mögliche Doppelmail zu senden. Versandstatus im Admin prüfen.
Für Probeläufe `email.mode = "test"` nutzen; `enabled = false` verhindert Versand.

## Prüfung und Grenzen

```powershell
python -m unittest discover -s tests -p "test_quest*.py"
python scripts/check_quest_concurrency.py
```

Der Lastcheck verwendet eine temporäre Datenbank, 100 parallele Clients,
wiederholte Scans und Kartenziehungen. Er versendet keine E-Mails und verändert
keine Veranstaltungsdaten. Das ist ein Speichertest, kein Nachweis für 100
gleichzeitige Streamlit-Browser auf Community Cloud. PostgreSQL benötigt zusätzlich
einen Integrationstest mit der tatsächlichen bereitgestellten Datenbank. Vor dem
Event auch Foto-Scans, mobile Browser, WLAN und Cloud-Ressourcen unter Last testen.
