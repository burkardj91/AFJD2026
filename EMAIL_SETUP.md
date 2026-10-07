# E-Mail-Versand für AFJD 2026

Unter Streamlit → App settings → Secrets im bestehenden Abschnitt `[email]`:

```toml
[email]
enabled = true
auto_send = true
mode = "live"
```

Bestehende SMTP-Felder `sender`, `username`, `password`, `smtp_server` und `smtp_port` beibehalten. Zugangsdaten gehören ausschliesslich in Secrets. Gmail funktioniert mit dem bereits eingerichteten App-Passwort; Port 465 verwendet SSL, 587 STARTTLS. `test_recipient` wird im Live-Modus ignoriert und kann entfernt werden. Fehlendes `mode` bedeutet weiterhin sicherheitshalber Testmodus. Es gibt keine Testmail- oder Simulationsschaltflächen mehr; der Adminbereich zeigt den tatsächlichen Betriebsstatus.

Kontaktübersichten gehen an die gespeicherte Profiladresse jeder Person mit Zustimmung. Mitgliedschaftsanträge gehen an SVIAL mit separater Willkommensbestätigung für die Person; Eventbestätigungen verwenden die vorgesehenen Empfänger und CC. Der Live-Modus ändert keine Profiladressen: Eine importierte Testadresse bleibt eine Testadresse.

## Vor der Freigabe

- Änderungen auf GitHub nach `main` mergen und die aktualisierte Cloud-Version prüfen.
- ADMIN-01 → Veranstaltung verwalten → E-Mail-Versand: Modus und Konfiguration prüfen. Zusammenfassung → Termin auf **8. Oktober 2026, 21:00 Uhr Europe/Zurich** prüfen, falls kein anderer Zeitpunkt gewünscht ist.
- Personen, tatsächliche E-Mail-Adressen, Zustimmung, Gewinnbestand und bestehende Warteschlange kontrollieren. Dieses Code-Update löscht weder Importe noch Testaktivitäten. Bereits versuchte Nachrichten werden durch den Moduswechsel nicht nochmals automatisch versendet. Fällige, noch nicht versuchte Nachrichten können sofort nach Aktivierung versendet werden.
- Dauerhafte Datenbank und laufenden Worker sicherstellen (siehe INFRASTRUCTURE.md). Eine neue Datenbank-URL übernimmt bestehende Daten nicht automatisch; zuerst gesicherte Migration durchführen. Der interne Worker läuft nur mit dem App-Prozess. Ein externer Worker muss separat eingerichtet werden.
- ADMIN- und STAFF-Passwörter in Secrets müssen mindestens 16 Zeichen haben. Ein finaler Ablauf mit realem Smartphone, gedrucktem Badge, Rückkehr nach Kamera-Scan, Gewinn und E-Mail bleibt vor Ort zu prüfen. Automatisierte Tests ersetzen keinen Lasttest mit 100 Browsern.

## Versandstatus

ADMIN-01 → Veranstaltung verwalten → Zeitplan & E-Mail-Warteschlange zeigt geplante Nachrichten und Ergebnisse. Ein erfolgreicher SMTP-Aufruf bestätigt nur die Annahme durch den Mailserver. Fehlgeschlagene oder unklare Versuche werden nicht automatisch wiederholt. Vor einem manuellen Einzelversand das Absenderpostfach prüfen; dieser ist ein separater Versand und ersetzt die geplante Nachricht nicht.

Die Oberfläche enthält nur importierte Personen und Team-Zugänge. Eingebaute Testkonten sind für die öffentliche App deaktiviert. Testdaten und Hilfsfunktionen für automatisierte Tests bleiben im Quellcode, sind aber nicht über die App zugänglich. Bestehende Veranstaltungsdaten wurden nicht bereinigt oder verändert.
