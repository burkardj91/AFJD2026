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


## Geplanter Versand am Veranstaltungsabend

Standard: **8. Oktober 2026, 21:00 Uhr Europe/Zurich**. Unter ADMIN-01 → Veranstaltung verwalten → Zusammenfassung lässt sich der Termin ändern. Bei `enabled = true` und `auto_send = true` prüft der laufende Server alle 30 Sekunden die Warteschlange. Mit `mode = "live"` erhält jede Person mit Zustimmung ihre eigene Kontaktliste; im Testmodus gehen alle Nachrichten an `test_recipient`. Nicht zugeordnete Ersatzpersonen werden bis zur Korrektur übersprungen. Die Liste berücksichtigt die aktuellen E-Mail-Freigaben beim Versand.

Streamlit Community Cloud kann die App schlafen legen. Dieser Worker läuft nur solange der Python-Prozess läuft; er ist kein externer Zeitplaner. Für garantierten Versand zur gewünschten Uhrzeit braucht die App einen dauerhaft laufenden Server und eine persistente Datenbank. Nach einem verspäteten Start werden fällige, noch nicht versuchte Nachrichten versendet. Fehlerhafte oder unklare Versuche werden nicht automatisch wiederholt; den Status unter der Warteschlange und das Absenderpostfach prüfen, danach gegebenenfalls den Einzelversand nutzen.

## Mehrfachtickets und Ersatzpersonen

Jede Eventfrog-Ticket-ID erhält eine eigene Badge-ID, einen eigenen öffentlichen QR-Code und einen privaten Zugangscode. Bei mehreren Tickets mit identischem Namen und identischer E-Mail bleiben ab dem zweiten Ticket die vorderen Namensfelder leer. Die vorläufige Kennzeichnung (z. B. Lea Meier 2) steht hinten. Mit der Excel-Spalte **Namensschild leer** und dem Wert **ja** kann dies auch ausdrücklich angefordert werden.

Unter ADMIN-01 → Registration → **Badge korrigieren** anhand der Badge-ID den tatsächlichen Namen und die persönliche E-Mail erfassen. QR und Zugang bleiben gleich. Korrekturen werden beim erneuten Import derselben Ticket-ID erhalten. Die neue Person bestätigt die Datenschutzoptionen erneut. Ohne Ticket-ID lassen sich identische Käufer nicht zuverlässig als einzelne Tickets unterscheiden.
