//+------------------------------------------------------------------+
//|                                     Max Risky EA - 24/7 Scalper  |
//|    Dynamic Volatility Zones + OCO + Partial Close + KILL SWITCH  |
//+------------------------------------------------------------------+
#property strict
#include <Trade/Trade.mqh>
CTrade trade;

//--- Professional Palette
#define COLOR_WIN     C'32,178,170'  
#define COLOR_LOSS    C'230,100,100' 
#define COLOR_TEXT    C'200,200,220'
#define COLOR_BG      C'30,30,46'

//--- Enums
enum ENUM_RISK_MODE {
   RISK_FIXED_LOT = 0,    // Fixed Lot Size
   RISK_PERCENTAGE = 1    // Percentage of Balance
};

//--- Inputs 
input group "--- Dynamic Scalping Settings ---"
input int    LookbackBars  = 20;        // Number of bars to define the Liquidity Zone
input int    CommissionPts = 70;        
input int    EntryBuffer   = 100;       // Points outside the box to place traps
input double VolThreshold  = 1.5;       // Volume spike multiplier to trigger traps

input group "--- Capital Protection (Safety Net) ---"
input double MaxLossAmount  = 50.0;     // Kill Switch: Max floating loss in Account Currency ($)
input int    MinRiskPoints  = 150;      // Lot Bloat Fix: Minimum SL points for lot math

input group "--- Risk Management ---"
input ENUM_RISK_MODE RiskMethod = RISK_PERCENTAGE; 
input double BaseLot      = 0.1;            
input double RiskPercent  = 2.0;            
input double MaxLotLimit  = 10.0;           

input group "--- Profit Targets & Trade Management ---"
input bool   EnablePartialClose = true;     
input double RR_Multiplier = 0.0;           // Set to 0.0 for NO Hard TP (Let Trailing Stop ride the trend)
input bool   UseTrailing   = true;          
input int    TrailingStop  = 500;           // Widened to 500 points (50 pips) to prevent premature exit
input int    TrailingStep  = 100;           // Step updated to 100 points (10 pips)

//--- Globals
double   rangeHigh = 0.0, rangeLow = 0.0;
long     magicNumber = 777111;
string   dash_prefix = "MaxRisk_";
datetime lastTrapTime = 0;

// Array to track which tickets have already had 50% closed
ulong partialClosedTickets[];

//+------------------------------------------------------------------+
//| Helper: Count EA Positions and Orders                            |
//+------------------------------------------------------------------+
int CountEAPositions() {
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if(PositionSelectByTicket(ticket)) {
         if(PositionGetInteger(POSITION_MAGIC) == magicNumber && PositionGetString(POSITION_SYMBOL) == _Symbol) {
            count++;
         }
      }
   }
   return count;
}

int CountEAOrders() {
   int count = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--) {
      ulong ticket = OrderGetTicket(i);
      if(OrderSelect(ticket)) {
         if(OrderGetInteger(ORDER_MAGIC) == magicNumber && OrderGetString(ORDER_SYMBOL) == _Symbol) {
            count++;
         }
      }
   }
   return count;
}

//+------------------------------------------------------------------+
//| Helper: Equity Kill Switch (Fixed Dollar Value)                  |
//+------------------------------------------------------------------+
void CheckEquityKillSwitch() {
   if(CountEAPositions() == 0) return;
   
   double totalFloatingLoss = 0.0;
   bool hasOpenPositions = false;
   
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if(PositionSelectByTicket(ticket) && PositionGetInteger(POSITION_MAGIC) == magicNumber) {
         
         double posCommission = 0.0;
         long posID = PositionGetInteger(POSITION_IDENTIFIER);
         
         if(HistorySelectByPosition(posID)) {
            for(int k = 0; k < HistoryDealsTotal(); k++) {
               ulong dealTicket = HistoryDealGetTicket(k);
               posCommission += HistoryDealGetDouble(dealTicket, DEAL_COMMISSION);
            }
         }
         
         double profit = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP) + posCommission;
         totalFloatingLoss += profit;
         hasOpenPositions = true;
      }
   }
   
   if(hasOpenPositions && totalFloatingLoss < 0) {
      // Check if absolute loss exceeds the fixed dollar amount input
      if(MathAbs(totalFloatingLoss) >= MaxLossAmount) {
         Print("🚨 KILL SWITCH ACTIVATED! Max monetary loss reached ($", DoubleToString(MathAbs(totalFloatingLoss), 2) ,"). Closing trades.");
         
         for(int i = PositionsTotal() - 1; i >= 0; i--) {
            ulong ticket = PositionGetTicket(i);
            if(PositionSelectByTicket(ticket) && PositionGetInteger(POSITION_MAGIC) == magicNumber) trade.PositionClose(ticket);
         }
         
         for(int i = OrdersTotal() - 1; i >= 0; i--) {
            ulong t = OrderGetTicket(i);
            if(OrderSelect(t) && OrderGetInteger(ORDER_MAGIC) == magicNumber) trade.OrderDelete(t);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Helper: Check & Mark Partial Closes                              |
//+------------------------------------------------------------------+
bool IsPartiallyClosed(ulong ticket) {
   for(int i = 0; i < ArraySize(partialClosedTickets); i++) {
      if(partialClosedTickets[i] == ticket) return true;
   }
   return false;
}

void MarkPartiallyClosed(ulong ticket) {
   int size = ArraySize(partialClosedTickets);
   ArrayResize(partialClosedTickets, size + 1);
   partialClosedTickets[size] = ticket;
}

//+------------------------------------------------------------------+
//| Money Management: Dynamic Lot Calculation                        |
//+------------------------------------------------------------------+
double CalculateLots(double entryPrice, double stopLossPrice) {
   if(RiskMethod == RISK_FIXED_LOT) return BaseLot;

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmount = balance * (RiskPercent / 100.0);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   
   double pointsAtRisk = MathAbs(entryPrice - stopLossPrice) / _Point;
   
   // THE FIX: Prevent massive lot sizes if the Zone is micro-sized
   pointsAtRisk = MathMax(pointsAtRisk, (double)MinRiskPoints);
   
   double mathRiskDistance = pointsAtRisk * _Point;
   if(mathRiskDistance <= 0) return BaseLot; 
   
   double calculatedLot = riskAmount / ((mathRiskDistance / tickSize) * tickValue);
   
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxBrokerLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double stepLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   
   calculatedLot = MathFloor(calculatedLot / stepLot) * stepLot;
   
   if(calculatedLot < minLot) calculatedLot = minLot;
   if(calculatedLot > maxBrokerLot) calculatedLot = maxBrokerLot;
   if(calculatedLot > MaxLotLimit) calculatedLot = MaxLotLimit;
   
   return NormalizeDouble(calculatedLot, 2);
}

//+------------------------------------------------------------------+
//| Dashboard Setup                                                  |
//+------------------------------------------------------------------+
void CreateLabel(string name, string text, int x, int y, int size, color clr) {
   if(ObjectFind(0, name) < 0) ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, size);
   ObjectSetString(0, name, OBJPROP_FONT, "Trebuchet MS");
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_LOWER);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_LEFT_LOWER);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
}

void UpdateDashboard() {
   if(!HistorySelect(0, TimeCurrent())) return;
   
   int total_t = 0, wins = 0; double net_p = 0;
   for(int i = 0; i < HistoryDealsTotal(); i++) {
      ulong t = HistoryDealGetTicket(i);
      if(HistoryDealSelect(t) && HistoryDealGetInteger(t, DEAL_MAGIC) == magicNumber) {
         if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(t, DEAL_ENTRY) == DEAL_ENTRY_OUT) {
            double p = HistoryDealGetDouble(t, DEAL_PROFIT) + HistoryDealGetDouble(t, DEAL_SWAP) + HistoryDealGetDouble(t, DEAL_COMMISSION);
            net_p += p; total_t++; if(p > 0) wins++;
         }
      }
   }

   string status = "Status: Scanning 24/7";
   color s_clr = clrGray;
   if(CountEAOrders() > 0 && CountEAPositions() == 0) { status = "Status: TRAPS LIVE"; s_clr = clrDodgerBlue; }
   if(CountEAPositions() > 0) { status = "Status: IN TRADE"; s_clr = COLOR_WIN; }

   CreateLabel(dash_prefix+"1", "💎 Max Risky EA - Scalper", 20, 160, 10, clrGold);
   CreateLabel(dash_prefix+"2", "Zone: Last " + IntegerToString(LookbackBars) + " Bars", 25, 140, 8, clrCyan);
   CreateLabel(dash_prefix+"3", status, 25, 120, 8, s_clr);
   CreateLabel(dash_prefix+"4", "Net Profit: $" + DoubleToString(net_p, 2), 25, 100, 8, (net_p >= 0 ? COLOR_WIN : COLOR_LOSS));
}

//+------------------------------------------------------------------+
//| EXECUTION ENGINE                                                 |
//+------------------------------------------------------------------+
void OnTick() {
   UpdateDashboard();
   CheckEquityKillSwitch(); 

   // Flatten tracking array if no active EA positions
   if(CountEAPositions() == 0 && ArraySize(partialClosedTickets) > 0) {
      ArrayResize(partialClosedTickets, 0);
   }

   // --- DYNAMIC ENTRY LOGIC (24/7) ---
   if(CountEAPositions() == 0) {
      long vol_buf[];
      // Scan the current timeframe natively
      if(CopyTickVolume(_Symbol, PERIOD_CURRENT, 0, 11, vol_buf) >= 11) {
         double avg = 0; for(int i=1; i<=10; i++) avg += (double)vol_buf[i]; avg /= 10.0;
         
         datetime currentBarTime = (datetime)SeriesInfoInteger(_Symbol, PERIOD_CURRENT, SERIES_LASTBAR_DATE);

         // Trigger when volume spikes and we haven't already acted on this specific bar
         if((double)vol_buf[0] > avg * VolThreshold && currentBarTime != lastTrapTime) {
            
            // Delete old stale pending orders to reset the traps around current price
            for(int i = OrdersTotal() - 1; i >= 0; i--) {
               ulong t = OrderGetTicket(i);
               if(OrderSelect(t) && OrderGetInteger(ORDER_MAGIC) == magicNumber) trade.OrderDelete(t);
            }

            // Dynamically calculate the box based on recent lookback
            rangeHigh = iHigh(_Symbol, PERIOD_CURRENT, iHighest(_Symbol, PERIOD_CURRENT, MODE_HIGH, LookbackBars, 1));
            rangeLow = iLow(_Symbol, PERIOD_CURRENT, iLowest(_Symbol, PERIOD_CURRENT, MODE_LOW, LookbackBars, 1));

            if(rangeHigh > rangeLow) {
               double buyP = NormalizeDouble(rangeHigh + (EntryBuffer * _Point), _Digits);
               double sellP = NormalizeDouble(rangeLow - (EntryBuffer * _Point), _Digits);
               
               double boxSize = rangeHigh - rangeLow; 
               double longSL = sellP; 
               double shortSL = buyP;

               // Updated TP Logic: Allow 0 to mean "No TP, infinite runner"
               double longTP = 0.0;
               double shortTP = 0.0;
               if(RR_Multiplier > 0) {
                  longTP = NormalizeDouble(buyP + (boxSize * RR_Multiplier), _Digits);
                  shortTP = NormalizeDouble(sellP - (boxSize * RR_Multiplier), _Digits);
               }

               double currentBuyLot = CalculateLots(buyP, longSL);
               double currentSellLot = CalculateLots(sellP, shortSL);

               double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
               double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

               if(ask < buyP) trade.BuyStop(currentBuyLot, buyP, _Symbol, longSL, longTP);
               else trade.BuyLimit(currentBuyLot, ask, _Symbol, longSL, longTP); 

               if(bid > sellP) trade.SellStop(currentSellLot, sellP, _Symbol, shortSL, shortTP);
               else trade.SellLimit(currentSellLot, bid, _Symbol, shortSL, shortTP); 
                  
               lastTrapTime = currentBarTime; // Lock out until next bar
            }
         }
      }
   }

   // --- ONE-CANCELS-OTHER (OCO) ---
   if(CountEAPositions() > 0 && CountEAOrders() > 0) {
      for(int i = OrdersTotal() - 1; i >= 0; i--) {
         ulong t = OrderGetTicket(i);
         if(OrderSelect(t) && OrderGetInteger(ORDER_MAGIC) == magicNumber) {
            trade.OrderDelete(t);
         }
      }
   }

   // --- ACTIVE TRADE MANAGEMENT ---
   if(CountEAPositions() > 0) {
      double boxSize = rangeHigh - rangeLow; 

      for(int i = PositionsTotal() - 1; i >= 0; i--) {
         ulong ticket = PositionGetTicket(i);
         if(PositionSelectByTicket(ticket) && PositionGetInteger(POSITION_MAGIC) == magicNumber) {
            double b = SymbolInfoDouble(_Symbol, SYMBOL_BID), a = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
            double sl = PositionGetDouble(POSITION_SL), o = PositionGetDouble(POSITION_PRICE_OPEN);
            double tp = PositionGetDouble(POSITION_TP); 
            double currentVol = PositionGetDouble(POSITION_VOLUME);
            long type = PositionGetInteger(POSITION_TYPE);
            
            // --- PARTIAL CLOSE ENGINE ---
            if(EnablePartialClose && !IsPartiallyClosed(ticket)) {
               double targetPrice = (type == POSITION_TYPE_BUY) ? (o + boxSize) : (o - boxSize);
               bool hitTarget = (type == POSITION_TYPE_BUY) ? (b >= targetPrice) : (a <= targetPrice);
               
               if(hitTarget) {
                  double stepLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
                  double closeVol = MathFloor((currentVol / 2.0) / stepLot) * stepLot; 
                  
                  if(closeVol >= SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN)) {
                     if(trade.PositionClosePartial(ticket, closeVol)) {
                        MarkPartiallyClosed(ticket); 
                        currentVol = PositionGetDouble(POSITION_VOLUME); 
                     }
                  }
               }
            }

            // --- RELAXED TRAILING STOP ---
            if(UseTrailing) {
               if(type == POSITION_TYPE_BUY) {
                  if(b > o + (TrailingStop * 2 * _Point)) { 
                     double nSL = NormalizeDouble(b - (TrailingStop * _Point), _Digits);
                     if(nSL > sl + (TrailingStep * _Point) && nSL < b) trade.PositionModify(ticket, nSL, tp);
                  }
               } else {
                  if(a < o - (TrailingStop * 2 * _Point)) {
                     double nSL = NormalizeDouble(a + (TrailingStop * _Point), _Digits);
                     if((sl == 0 || nSL < sl - (TrailingStep * _Point)) && nSL > a) trade.PositionModify(ticket, nSL, tp);
                  }
               }
            }
         }
      }
   }
}

int OnInit() { trade.SetExpertMagicNumber(magicNumber); return(INIT_SUCCEEDED); }
void OnDeinit(const int r) { ObjectsDeleteAll(0, dash_prefix); }
//+------------------------------------------------------------------+