# ForexCracked.com AI (AI FREE)

## 📝 Beschreibung
Ein moderner EA, der technische Indikatoren (ADX & Alligator) als Pre-Filter nutzt. Sobald ein Trend erkannt wird, erstellt der EA drei Screenshots des Charts und sendet sie per WebRequest an ein konfiguriertes LLM (z. B. Claude, GPT, Gemini). Die KI entscheidet über den Einstieg, die Richtung sowie SL/TP.

## ⚙️ Einstellungen
1. **WebRequest-Freigabe:** In MetaTrader 5 unter *Tools -> Options -> Expert Advisors* müssen folgende URLs eingetragen werden:
   * `https://api.anthropic.com`
   * `https://api.openai.com`
   * `https://generativelanguage.googleapis.com`
   * `https://api.deepseek.com`
   * `https://api.x.ai`
2. **API-Key:** Sie müssen Ihren eigenen API-Schlüssel im EA-Eingabeparameter `InpAPIKey` eintragen.
3. **LLM-Provider:** In `InpProviderOverride` können Sie die KI wählen. Gemini (Free Key) funktioniert gut, DeepSeek unterstützt in dieser Version keine Vision-Bilder.
4. **Timeframe:** Standardmäßig M15.

## ⚠️ Risikomanagement & Kapitalanforderung
* **Kapital:** Flexibel (Standard-Konten oder Prop-Firm-Modus).
* **Risiko-Rating:** 🟢 Gering bis 🟠 Mittel (abhängig davon, ob optionales Martingale aktiviert ist).
* **Hinweis:** Kann im MT5-Tester nicht backgetestet werden, da WebRequests dort blockiert sind. Optimierung nur auf Demo-Konten möglich.
