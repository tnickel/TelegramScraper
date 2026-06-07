# Heiken_Ashi (Automatisch extrahiert)

## 📝 Beschreibung
Dieser Forex-Roboter wurde automatisch aus den Chat-Nachrichten und Dateianhängen extrahiert, da er in der Community aktiv diskutiert wird.

## 📊 Statistiken
* **Erwähnungen im Chat:** 13 Mal
* **Gefundene Versionen/Dateien:** 1 Datei(en)

## 📁 Zugehörige Dateien im Ordner
* `Heiken Ashi.ex4`

## 💬 Community-Kommentare (Was die User schreiben)
> *"I need heiken ashi dashboard or scanner,,
Anyone can help me get it ??"*

> *"This guy scammer,,, beware,,, i just paid 20 usd for heiken ashi dashboard"*

> *"I need heiken ashi dashboard with alert phone notification"*

> *"1. **Heiken Ashi + TMA Bands** (with arrows/circles)
 2. **Custom TDI or RSI-based oscillator** (“pollan vers 2”)
 3. **MACD (12,26,9)**
 4. **Trend Confirmation Histogram**"*

> *"Heiken Ashi Forex Trading Strategy – Smoother Trend Identification & Consistent Profits

Identifying real trends in Forex trading can be tough, especially when market noise and volatility cloud decision making. While traditional candlesticks often lead to choppy signals, the Heiken Ashi Forex Trading Strategy smooths out price action, making trend direction clearer and entries more precise. This article presents a practical, stand-alone approach to using Heiken Ashi…

https://www.forexcracked.com/education/forex-strategies/heiken-ashi-forex-trading-strategy/"*

> *"yes. only need 3 pins confirmation and other filter such RSI, EMA, and HAS(Heiken AShi) agreement"*

> *"Does anone have any heiken Ashi EA?"*

> *"Here’s the script:

//@version=2
study("Tradest Indicator Script", overlay=true)
EMAlength=input(55,"EMA length:")

src=ohlc4
haOpen=0.0
haOpen := (src + nz(haOpen[1]))/2
haC=(ohlc4+nz(haOpen)+max(high,nz(haOpen))+min(low,nz(haOpen)))/4
EMA1=ema(haC,EMAlength)
EMA2=ema(EMA1,EMAlength)
EMA3=ema(EMA2,EMAlength)
TMA1=3*EMA1-3*EMA2+EMA3
EMA4=ema(TMA1,EMAlength)
EMA5=ema(EMA4,EMAlength)
EMA6=ema(EMA5,EMAlength)
TMA2=3*EMA4-3*EMA5+EMA6
KEVA=TMA1-TMA2
NAVA=TMA1+KEVA
EMA7=ema(hlc3,EMAlength)
EMA8=ema(EMA7,EMAlength)
EMA9=ema(EMA8,EMAlength)
TMA3=3*EMA7-3*EMA8+EMA9
EMA10=ema(TMA3,EMAlength)
EMA11=ema(EMA10,EMAlength)
EMA12=ema(EMA11,EMAlength)
TMA4=3*EMA10-3*EMA11+EMA12
KEVA1=TMA3-TMA4
NAVA1=TMA3+KEVA1

igres=NAVA1
indoc=NAVA



longCond=igres>indoc and igres[1]<=indoc[1]
shortCond=igres<indoc and igres[1]>=indoc[1]
trendState  = indoc < igres ? true : indoc > igres ? false : trendState[1]
closePlot   = plot(indoc, title = "Close Line", color = #00ffa8, linewidth = 10, style = line, transp = 90)
openPlot    = plot(igres, title = "Open Line", color = #ff004c, linewidth = 10, style = line, transp = 90)
closePlotU  = plot(trendState ? indoc : na, transp = 100, editable = false)
openPlotU   = plot(trendState ? igres : na, transp = 100, editable = false)
closePlotD  = plot(trendState ? na : indoc, transp = 100, editable = false)
openPlotD   = plot(trendState ? na : igres, transp = 100, editable = false)
fill(openPlotU, closePlotU, title = "Up Trend Fill", color = #00ffa8, transp = 1)
fill(openPlotD, closePlotD, title = "Down Trend Fill", color = #ff004c, transp = 1)


last_signal = 0
long_final  = longCond  and (nz(last_signal[1]) == 0 or nz(last_signal[1]) == -1)
short_final = shortCond and (nz(last_signal[1]) == 0 or nz(last_signal[1]) == 1)

alertcondition(long_final, title="Buy signal", message="Buy")
alertcondition(short_final, title="Sell signal", message="Sell")
last_signal := long_final ? 1 : short_final ? -1 : last_signal[1]

plotshape(long_final, style=shape.triangleup,
          location=location.belowbar, color=#00ffa8,size=size.tiny,title="buy label",text="Buy",textcolor=#00ffa8)
plotshape(short_final, style=shape.triangledown,
          location=location.abovebar, color=#ff004c,size=size.tiny,title="sell label",text="Sell",textcolor=#ff004c)


Video guides:

1. Quick installation guide: https://youtu.be/WHJfwILcWjo

2. Setting Alerts guide: https://youtu.be/e_2hamFc9oU

*Text instructions are available in video descriptions.


Here is some information about our script:

- Paste the script source code to Pine Editor* in your TradingView layout, Save and Add to your chart. Please also turn on Heiken Ashi bars style for candles while using this script to get the most accurate signals. 
*Make sure that Pine Editor window is empty before pasting the code. 

- After uploading script you should see two-coloured Moving Average and Buy/Sell signal labels. Appearance of those are customisable in script settings as well.

- Script works on Forex, Crypto, Stocks, Indices and Commodities markets on all time frames. If script is not loading on particular chart time frame, the reason is probably lack of past data on the chart to calculate signals. 


Few useful tips:

- You can set Alerts for Buy/Sell signals of Tradest Indicator Script to not miss any of them on your TradingView panel.

- The most optimal opportunity for entering a position after getting a signal is if the signal occurred with no significant price move; it remained after candle close which makes it confirmed; Moving Average reversed its colour to direction of the position signal is calling to open. If all those conditions are met, it’s a strong indicator to open a position. 

- The most optimal opportunity for closing a position is when Heiken Ashi candles are turning to opposite color to position you took, especially making ‘Doji' formations; Moving Average is turning to opposite color to position you took or getting very flat and thin; opposite signal appeared."*

