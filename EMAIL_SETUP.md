# E-Mail-Versand

Den Inhalt von `.streamlit/email-secrets.example.toml` in **Streamlit → App settings → Secrets** ergänzen. Vorhandene Einstellungen wie `QUEST_ADMIN_PASSWORD` beibehalten; diese müssen oberhalb des `[email]`-Abschnitts stehen, wenn sie bisher auf der obersten Ebene stehen.

1. Das Gmail-App-Passwort ausschliesslich in Secrets eintragen.
2. `enabled = true` setzen; `mode = "test"` und `test_recipient = "svial@svial.ch"` beibehalten.
3. In der App mit `ADMIN-01` und dem Administrator-Passwort anmelden.
4. **Veranstaltung verwalten → E-Mail-Versand · Test & Freigabe → SMTP-Testmail senden**.
5. Für einen persönlichen Test muss eine Demo-Person angemeldet sein und der Zusammenfassung zugestimmt haben. Im selben Bereich diese Person auswählen und **Kontakt-Mail als Test senden** klicken.

Für echte Teilnehmende später `mode = "live"` setzen. Die Kontakt-Mail geht dann an die gespeicherte Profiladresse; `test_recipient` wird für Kontakt-Mails ignoriert. Die separate SMTP-Testmail geht weiterhin an die Testadresse. Alle fest eingebauten Demo-Konten verwenden immer svial@svial.ch, auch im Live-Modus.

Gleiche Nachrichten an dieselbe Person werden nicht erneut versendet. Der Status wird in der lokalen Ereignis-Datenbank gespeichert. Bei einem unklaren SMTP-Ergebnis gibt es keinen automatischen Wiederholungsversuch: erst das Absenderpostfach prüfen. Ein erfolgreicher Status bestätigt die Annahme durch den Mailserver, nicht die Zustellung beim Empfänger.

Dieser Schritt ergänzt einen manuellen Admin-Versand. Der Zeitplan erzeugt weiterhin Entwürfe; er startet keinen automatischen Massenversand. Mitgliedschaftsanträge bleiben Entwürfe. Dauerhafte Speicherung der Datenbank ist Voraussetzung für einen zuverlässigen produktiven Versandverlauf.
