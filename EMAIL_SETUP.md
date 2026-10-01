# E-Mail-Versand

Den Inhalt von `.streamlit/email-secrets.example.toml` in **Streamlit → App settings → Secrets** ergänzen. Vorhandene Einstellungen wie `QUEST_ADMIN_PASSWORD` beibehalten; diese müssen oberhalb des `[email]`-Abschnitts stehen, wenn sie bisher auf der obersten Ebene stehen.

1. Das Gmail-App-Passwort ausschliesslich in Secrets eintragen.
2. `enabled = true` setzen; `mode = "test"` und `test_recipient = "j.burkard@svial.ch"` beibehalten.
3. In der App mit `ADMIN-01` und dem Administrator-Passwort anmelden.
4. **Veranstaltung verwalten → E-Mail-Versand · Test & Freigabe → SMTP-Testmail senden**.
5. Für einen persönlichen Test muss eine Demo-Person angemeldet sein und der Zusammenfassung zugestimmt haben. Im selben Bereich diese Person auswählen und **Kontakt-Mail als Test senden** klicken.

Für echte Teilnehmende später `mode = "live"` setzen. Die Kontakt-Mail geht dann an die gespeicherte Profiladresse; `test_recipient` wird für Kontakt-Mails ignoriert. Die separate SMTP-Testmail geht weiterhin an die Testadresse. Alle fest eingebauten Demo-Konten verwenden immer j.burkard@svial.ch, auch im Live-Modus.

Gleiche Nachrichten an dieselbe Person werden nicht erneut versendet. Der Status wird in der lokalen Ereignis-Datenbank gespeichert. Bei einem unklaren SMTP-Ergebnis gibt es keinen automatischen Wiederholungsversuch: erst das Absenderpostfach prüfen. Ein erfolgreicher Status bestätigt die Annahme durch den Mailserver, nicht die Zustellung beim Empfänger.

Zusätzlich zum manuellen Admin-Versand läuft der unten beschriebene automatische Versand. Neu abgesendete Mitgliedschaftsanträge gehen an svial@svial.ch; die Person erhält eine separate Willkommensbestätigung. Im Testmodus werden beide Nachrichten an test_recipient umgeleitet. Ältere Antragsentwürfe werden nicht nachträglich automatisch verschickt. Dauerhafte Speicherung der Datenbank ist Voraussetzung für einen zuverlässigen produktiven Versandverlauf.


## Geplanter Versand am Veranstaltungsabend

Standard: **8. Oktober 2026, 21:00 Uhr Europe/Zurich**. Unter ADMIN-01 → Veranstaltung verwalten → Zusammenfassung lässt sich der Termin ändern. Bei `enabled = true` und `auto_send = true` prüft der laufende Server alle 30 Sekunden die Warteschlange. Mit `mode = "live"` erhält jede Person mit Zustimmung ihre eigene Kontaktliste; im Testmodus gehen alle Nachrichten an `test_recipient`. Nicht zugeordnete Ersatzpersonen werden bis zur Korrektur übersprungen. Die Liste berücksichtigt die aktuellen E-Mail-Freigaben beim Versand.

Streamlit Community Cloud kann die App schlafen legen. Dieser Worker läuft nur solange der Python-Prozess läuft; er ist kein externer Zeitplaner. Für garantierten Versand zur gewünschten Uhrzeit braucht die App einen dauerhaft laufenden Server und eine persistente Datenbank. Nach einem verspäteten Start werden fällige, noch nicht versuchte Nachrichten versendet. Fehlerhafte oder unklare Versuche werden nicht automatisch wiederholt; den Status unter der Warteschlange und das Absenderpostfach prüfen, danach gegebenenfalls den Einzelversand nutzen.

## Mehrfachtickets und Ersatzpersonen

Jede Eventfrog-Ticket-ID erhält eine eigene Badge-ID, einen eigenen öffentlichen QR-Code und einen privaten Zugangscode. Bei mehreren Tickets mit identischem Namen und identischer E-Mail bleiben ab dem zweiten Ticket die vorderen Namensfelder leer. Die vorläufige Kennzeichnung (z. B. Lea Meier 2) steht hinten. Mit der Excel-Spalte **Namensschild leer** und dem Wert **ja** kann dies auch ausdrücklich angefordert werden.

Unter ADMIN-01 → Registration → **Badge korrigieren** anhand der Badge-ID den tatsächlichen Namen und die persönliche E-Mail erfassen. QR und Zugang bleiben gleich. Korrekturen werden beim erneuten Import derselben Ticket-ID erhalten. Die neue Person bestätigt die Datenschutzoptionen erneut. Ohne Ticket-ID lassen sich identische Käufer nicht zuverlässig als einzelne Tickets unterscheiden.


## Mitgliedschaft und kurze Zugangscodes

Ein zugeordneter Mitgliedschafts-QR öffnet **Profil**. Nur dann werden Abschluss (HAFL, ETHZ, HES-SO, ZHAW, Andere), Studiengang (Agrarwissenschaften, Lebensmittelwissenschaften, Andere), Postadresse und Geburtsdatum abgefragt. Alle vier Angaben sind Pflicht. Die Mitgliedschaft endet am 31.12.2027 ohne automatische Verlängerung. Die Bestätigung kündigt eine Rückfrage zur Verlängerung im Jahr 2027 an; diese spätere Rückfrage wird nicht bereits durch diese App geplant.

Neue Importe und Reserve-Badges erhalten kurze Codes im Format **AFJD-LM-482**. Unter **Registration → Badge korrigieren** kann die Administration mit „Neuen kurzen Zugangscode erstellen“ den Code erneuern. Das widerruft gespeicherte Anmeldungen der Person. Der öffentliche QR-Code und die ID bleiben unverändert. Ein bereits gedruckter privater Zugangszettel muss bei einem Codewechsel ersetzt werden.

Unter **Registration → Nachmeldung → 20 Reserve-Badges anlegen** entstehen 20 John-Doe-Platzhalter. Der Vorgang ist wiederholbar, ohne weitere Kopien anzulegen. Im Druckbereich können alle oder ausgewählte Badges exportiert werden. Korrekturen bleiben bei erneutem Import erhalten.

Die öffentliche Startseite zeigt keine Demo- oder Team-Kennungen. Diese Kennungen funktionieren weiterhin im normalen Zugangsfeld. **ADMIN-01 → Veranstaltung verwalten → Testzugänge & Team-Zugänge** zeigt die aktuelle Liste einschliesslich importierter Personen. Echte Admin- und Team-Passwörter bleiben in Secrets. Im Scan-Test können importierte Personen statt der eingebauten Beispiele ausgewählt werden.
