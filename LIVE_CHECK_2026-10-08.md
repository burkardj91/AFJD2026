# Lokale Betriebsprüfung · 8. Oktober 2026

Geprüft: Quellcode von Branch codex/badge-activation (Ausgangsstand d862436), Python/Streamlit 1.61.1 unter Windows. Die relevanten Laufzeitdateien stimmen mit dem gepushten Branch überein. Sämtliche Prüfungen verwenden temporäre Datenbanken und fiktive Personen. Keine echten E-Mails, keine Veränderungen an importierten Personen, IDs oder Aktivitäten. Cloud-Secrets und die tatsächliche Cloud-Datenbank wurden nicht geprüft.

## Ergebnisse

- 84 automatisierte Tests bestanden: Import, stabile Identitäten, Anmeldeablauf, Widerruf/4-Stunden-Frist, Quest-Regeln, Datenschutz, Gewinnbestand, Rückgabe, Mitgliedschaft und Mailverarbeitung.
- 100 parallele Speicherclients: keine verlorenen Kontakte oder doppelten Gewinnzuordnungen. Mehrfacher Scan und wiederholte Ziehung bleiben idempotent. Laufzeit 7,50 s, 95. Perzentil eines vollständigen Clientablaufs 6,87 s, Maximum 7,39 s.
- 120 parallele Speicherclients: keine Fehler. Laufzeit 13,84 s, 95. Perzentil 12,94 s, Maximum 13,68 s. Weitere Prüfungen liefen teilweise parallel; diese Zeiten sind Orientierungswerte, kein isolierter Hosting-Benchmark.
- Oberflächentests bestanden: Import, Termine, Anmeldung/Datenschutz, unveränderte IDs und Codes, Admin-/Team-Schutz, Preis zurücklegen/neu ziehen, Mitgliedschaftsnavigation, Eventbestätigung, physisches Geschenk, SFR-Preis und sauberer Kontowechsel. Hintergrund-Mailworker deaktiviert, SMTP-Verbindungen ausdrücklich blockiert.

- Zusätzlicher Extremtest nach Korrektur bestanden: 100 gleichzeitige Ziehungsanfragen für dieselbe Person → genau eine Gewinnzuordnung; 100 wiederholte Scans → genau eine Verbindung; acht konkurrierende Maildienste → genau 100 eindeutige simulierte Versandaufrufe. Laufzeit insgesamt 34,27 s, davon Mailkonkurrenz 22,20 s. Keine echten E-Mails. Fremde Gewinnlinks und private Felder wurden ebenfalls geprüft.

## Behobene Befunde

Die Begrenzung falscher Anmeldeversuche prüfte den bisherigen Zähler und speicherte den neuen Fehler in getrennten Transaktionen. Gleichzeitige Anfragen konnten dadurch an der Grenze vorbeikommen. Beide Schritte werden jetzt unter derselben Datenbanksperre ausgeführt. Der Regressionstest schickt 20 parallele Fehlversuche aus derselben Gruppe: fünf werden gezählt, die übrigen 15 blockiert. Erfolgreiche Anmeldungen werden nicht als Fehler gezählt. Keine bestehenden Zugangscodes wurden geändert.

Ein Extremtest mit acht gleichzeitig laufenden Maildiensten und 100 fälligen Kontaktmails löste zunächst `database is locked` aus. Ursache: Die Warteschlangenpflege erstellte durch ein vorzeitig ausgewertetes `setdefault`-Argument bei jeder Änderung alle bereits vorhandenen Mailentwürfe erneut. Nach dem Versandzeitpunkt betraf dies auch normale Benutzeraktionen. Bestehende Einträge werden jetzt vor der Entwurfserstellung übersprungen. Beim tatsächlichen Beanspruchen einer Mail wird der Inhalt weiterhin frisch mit den aktuellen Freigaben erstellt. Ein Regressionstest deckt beide Bedingungen ab.

## Datenschutz und Grenzen

Die geprüften Kontaktübersichten enthalten keine Postadressen oder Geburtsdaten und respektieren die E-Mail-Freigabe. Die öffentliche Netzwerkansicht enthält keine persönlichen Badge-Tokens, Zugangscodes oder E-Mail-Adressen. Bei der Hauptverlosung erscheinen Gewinner-Badge-IDs absichtlich öffentlich. Fremde Gewinnkarten dürfen nicht über ihren Link eingelöst werden. HTML-Inhalte in Kontaktmails werden maskiert; SQL-Werte werden als Parameter übergeben.

Diese gezielte Prüfung ist kein vollständiger Penetrationstest. Kurze persönliche Codes mit drei Ziffern bleiben leichter zu erraten als starke Passwörter. Die Begrenzung gilt je Quelladresse und Namenskürzel: verteilte Versuche sind nicht global begrenzt; Personen im selben WLAN mit gleichen Kürzeln können eine Sperre teilen. Browser-Anmeldetokens sind zufällig, in der Datenbank nur gehasht und nach vier Stunden ungültig; das aktuelle JavaScript-Cookie ist aber nicht HttpOnly. Team-/Admin-Passwörter brauchen mindestens 16 Zeichen; deren Eingabe hat noch keine eigene Versuchsbegrenzung. Für eine längerfristige Plattform empfiehlt sich eine stärkere serverseitige Authentifizierung.

## Was für den Anlass offen bleibt

1. Kein Nachweis für 100 gleichzeitige echte Streamlit-Browser auf dem konkreten Cloud-Tarif. Die Datenbanktests decken weder WebSockets, Browser-Rendering, RAM-Bedarf noch Veranstaltungs-WLAN ab. Bei Spitzenlast sind Wartezeiten erkennbar; alle Änderungen teilen einen serialisierten Veranstaltungsdatensatz.
2. PostgreSQL wurde nicht mit einem echten Server integriert getestet. SQLite-Daten auf kurzlebigem Hosting benötigen eine verlässliche Sicherungs-/Persistenzstrategie. Eine neue Datenbank-URL kopiert bestehende Daten nicht automatisch.
3. Geplante E-Mails benötigen einen laufenden App-Prozess oder separat eingerichteten Worker. SMTP-Annahme ist keine Zustellbestätigung; Provider-Limits, Spamfilter und die echte Konfiguration wurden nicht getestet. Bei unklarem Versandstatus wird bewusst nicht automatisch erneut gesendet.
4. Historische Testaktivitäten, Bestand und Mailwarteschlange wurden nicht verändert. Vor Liveversand im Adminbereich kontrollieren. Manuelle und geplante Kontaktmails sind getrennte Versandvorgänge und können beide ausgeführt werden.

Reproduzieren (jeweils mit temporären Daten, ohne SMTP):

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_quest*.py"
.venv\Scripts\python.exe scripts/check_quest_concurrency.py
.venv\Scripts\python.exe scripts/check_quest_concurrency.py --clients 120
.venv\Scripts\python.exe scripts/check_quest_event_races.py
```


## Nachtrag: Lastreduzierung während des Anlasses

Eine ausgegraute/hängende Live-Sitzung liess sich ohne Serverlogs oder betroffene Sitzung nicht eindeutig reproduzieren. Unabhängig davon wurden wiederkehrende Kosten reduziert:

- Badge-Dateien werden über Streamlits verzögerte Download-Erzeugung erst auf Klick erstellt. Alle vier Dateiformate wurden geprüft; Seitenaufbau und Änderungen erzeugen keine Druckdateien mehr.
- Registration reagiert nicht mehr auf jeden fremden Scan mit einem automatischen kompletten Seitenaufbau. Eigene Interaktionen laden aktuelle Daten weiterhin. Teilnehmer-, Team- und Leinwand-Aktualisierung bleiben aktiv.
- Datenbank-Lesezugriffe kopieren nur das benötigte Feld/Ergebnis, nicht jedes Mal den gesamten Veranstaltungszustand. Zurückgegebene Daten bleiben unabhängige Kopien. Zwischenzeitliche Änderungen anderer Clients werden weiterhin anhand der Datenbankrevision erkannt.
- Unveränderte Teilnehmeransichten verwenden ihren bereits berechneten Vergleichswert wieder; Änderung von Profil, Kontakten, Gewinnstatus und Terminbestätigung wird weiterhin erkannt.

Lokaler Vorher/Nachher-Vergleich mit 100 Personen und gefüllter Mailwarteschlange: 100 Leseabläufe von 2,202 auf 1,507 Sekunden; 100 unveränderte Aktualisierungsprüfungen von 0,584 auf 0,280 Sekunden. Dies ist kein Cloud-Benchmark.

86 Tests bestanden, zusätzlich geprüfte Admin-/Gewinnoberflächen und gültige verzögerte Downloads. Erneuter Konflikttest: 100 Anfragen auf denselben Gewinn ergeben eine Zuweisung, 100 wiederholte Scans eine Verbindung, acht Maildienste 100 eindeutige simulierte Versandaufrufe. Keine echten E-Mails, kein Zugriff auf Veranstaltungsdaten. Keine Datenmigration, keine Änderung bestehender IDs oder Zugangscodes. Ein Live-Rollout bleibt ein eigener Schritt und kann laufende Sitzungen zum Neuladen bringen.
