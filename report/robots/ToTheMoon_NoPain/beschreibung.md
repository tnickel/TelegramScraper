# ToTheMoon (NoPain Signal)

## 📝 Beschreibung
ToTheMoon ist ein vollautomatischer Grid-Handelsroboter (Expert Advisor), der von Daniel Moraes Da Silva (MQL5: `tec_daniel`) entwickelt wurde und die Basis für das bekannte MQL5-Kopiersignal **"NoPain"** bildet.
Der EA nutzt eine intelligente Grid-Strategie mit automatischem Durchschnittspreis-Management (Smart Averaging). Bei Trendwenden schützt er das Konto durch ein integriertes Verlustmanagement (Smart Loss Management / Smart Stop Loss), das Verlustpositionen schrittweise (teilweise) schließt, um einen hohen Drawdown zu verhindern.

## ⚙️ Einstellungen
* **Währungspaar:** Hauptsächlich optimiert für Paare mit geringer Volatilität und Seitwärtsphasen, insbesondere **AUDCAD**. Kann auch im Multi-Symbol-Modus betrieben werden.
* **Timeframe:** In der Regel auf **H1** betrieben (manche Nutzer nutzen auch M15/M5).
* **Settings:** Der Entwickler bietet spezielle Presets (.set) an. Standardeinstellungen sollten primär auf Demo-Konten getestet werden.

## ⚠️ Risikomanagement & Kapitalanforderung
* **Risiko-Rating:** 🔴 Sehr Hoch (Grid-/Martingale-Verhalten). Obwohl das Smart-Loss-Management den Drawdown dämpft, besteht bei lang anhaltenden Einwegtrends das Risiko von erheblichen Verlusten.
* **Kapital:** Mindestens **$1.000 bis $2.000 USD** oder Betrieb auf einem **Cent-Konto** mit entsprechendem Risikopuffer.
