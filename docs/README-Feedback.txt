HJ SUPPORT – Feedbackformular

1. feedback.html neben index.html im bestehenden Dokumentations-Repository ablegen.
   Die Seite nutzt das vorhandene assets/style.css und assets/logo-hj.jpg.
2. Die Navigation und werkzeugspezifischen Feedbacklinks werden automatisch
   durch assets/support.js erzeugt. assets/feedback.js verarbeitet das Formular,
   assets/feedback.css enthält ausschließlich das Formulardesign.
3. Für eine Verlinkung aus Allplan die GitHub-Pages-Adresse verwenden:
   https://lukasburtscher2003.github.io/handy-dandy-allplan-tools/feedback.html
   Optional direkt mit Werkzeugvorauswahl: ?tool=GeoIMPORT

MAILVERSAND EINRICHTEN

Der vorhandene Formspree-Endpunkt ist bereits in feedback.html eingetragen.
GitHub Pages versendet selbst keine E-Mails.

Nach Freigabe des externen Formulardienstes durch die Firma:
1. Auf https://formspree.io/ ein Konto erstellen und E-Mail verifizieren.
2. Ein Formular namens HJ Tools Feedback erstellen.
3. Die gewünschte Empfängeradresse für Benachrichtigungen einrichten.
4. Den Formular-Endpunkt aus der Integration kopieren, z. B.:
   https://formspree.io/f/DEINE_FORM_ID
5. Falls der Dienst gewechselt wird, in feedback.html das Attribut
   data-endpoint mit dem neuen Formular-Endpunkt aktualisieren.
6. Commit und Push durchführen. Eine Testnachricht absenden und den
   tatsächlichen Eingang im Postfach überprüfen.

Die Formular-ID ist öffentlich und kein API-Schlüssel. Keine Login-Daten
oder API-Schlüssel in das Repository schreiben.

Ohne einen freigegebenen Dienst bleibt der Senden-Button deaktiviert.
Eine unternehmensintern freigegebene Alternative (z. B. Microsoft Forms)
ist ebenfalls möglich. Vor Aktivierung Datenschutz / IT-Freigabe klären.
