//+------------------------------------------------------------------+
//|                  ScalpingEA_MultiTF_v5.mq5                       |
//|     Scalping EA - Revised Confluence Scoring                     |
//|   Core: EMA+RSI+Candle | Bonus: FVG, BOS, EMA SR               |
//|   Entry M1 | Trend M5/M15/M30 | TP USD | DD Watermark          |
//+------------------------------------------------------------------+
#property copyright "ScalpingEA v5"
#property version   "5.30"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

CTrade        trade;
CPositionInfo posInfo;

enum ENUM_DD_ACTION
{
   DD_STOP_TOTAL   = 0, // Berhenti Total
   DD_PAUSE_ONEDAY = 1, // Berhenti Sehari (resume next day)
   DD_CONTINUE     = 2, // Lanjut Sekarang (reset HWM)
};

enum ENUM_TP_ACTION
{
   TP_CONTINUE     = 0, // Lanjut Terus (tidak berhenti)
   TP_STOP_TOTAL   = 1, // Berhenti Total
   TP_PAUSE_ONEDAY = 2, // Berhenti Sehari (resume next day)
};

//=== INPUTS =========================================================

input group "=== ENTRY ==="
input int     MaxPositions    = 8;
input int     MagicNumber     = 202401;

input group "=== SCORING ==="
// Skor terdiri dari:
// CORE (hampir selalu ada): EMA align(1) + RSI(1) + Candle(1) = max 3
// BONUS (tambahan):         EMA SR(1) + FVG(1) + BOS(1) + RSI momentum(1) = max 4
// Total max = 7
// Rekomendasi MinScore: 2 (core saja) s/d 4 (core+bonus)
input int     MinScore        = 3;      // Min skor untuk entry (2-4 disarankan)
input bool    UseBonus_EMASR  = true;   // Hitung bonus EMA SR
input bool    UseBonus_FVG    = true;   // Hitung bonus FVG
input bool    UseBonus_BOS    = true;   // Hitung bonus BOS
input bool    UseBonus_RSIMom = true;   // Hitung bonus RSI momentum
input int     FVG_Lookback    = 15;     // Lookback FVG (candle M5)
input int     BOS_Lookback    = 30;     // Lookback BOS (candle M5)
input double  FVG_MinPip      = 2.0;    // Min gap FVG (pip)
input double  EMA_SR_Pip      = 10.0;   // Zona EMA SR (pip)

input group "=== EMA ==="
input int     EMA_Fast        = 8;
input int     EMA_Slow        = 21;

input group "=== RSI ==="
input int     RSI_Period      = 14;
input double  RSI_OB          = 70.0;
input double  RSI_OS          = 30.0;

input group "=== TP & TRAILING ==="
input double  TakeProfit_USD  = 0.50;   // TP per posisi (USD)
input double  HardSL_USD      = 1.50;   // Hard SL per posisi (USD) — 0 = nonaktif
input double  Trail_StartUSD  = 0.20;   // Trailing aktif setelah profit (USD)
input double  Trail_Stop_Pip  = 3.0;    // Trailing distance (pip)
input double  Trail_Step_Pip  = 2.0;    // Trailing step (pip)

input group "=== LOT ==="
input bool    UseDynamicLot   = true;
input double  RiskPct         = 1.0;
input double  MinLot          = 0.01;
input double  MaxLot          = 1.00;

input group "=== DD CUTOFF ==="
input double         MaxDD_Pct = 25.0;
input ENUM_DD_ACTION DD_Action = DD_PAUSE_ONEDAY;

input group "=== TP STOP (TARGET HARIAN) ==="
input bool           UseTPStop      = true;         // Aktifkan TP Stop harian
input double         TPStop_USD     = 5.0;          // Berhenti jika profit harian >= USD ini (0 = skip)
input double         TPStop_Pct     = 5.0;          // Berhenti jika profit harian >= X% dari balance awal hari (0 = skip)
input ENUM_TP_ACTION TP_Action      = TP_PAUSE_ONEDAY; // Tindakan setelah TP Stop hit

input group "=== JAM ==="
input bool    UseTimeFilter   = true;
input int     Hour_Start      = 8;
input int     Hour_End        = 20;
input bool    CloseOnFriday   = true;
input int     Friday_StopHour = 17;

input group "=== PANEL ==="
input int     Panel_X         = 15;
input int     Panel_Y         = 30;
input color   Panel_BG        = C'20,20,40';
input color   Col_Title       = C'100,180,255';
input color   Col_Label       = C'160,160,180';
input color   Col_Value       = clrWhite;
input color   Col_Profit      = clrLime;
input color   Col_Loss        = clrTomato;
input color   Col_Warning     = clrOrange;

//=== HANDLES ========================================================

int h_ef1,h_es1,h_ef5,h_es5,h_ef15,h_es15,h_ef30,h_es30;
int h_e21,h_e50,h_rsi1,h_rsi5;

//=== GLOBALS ========================================================

double   pip;
double   hwm;           // High Water Mark
bool     ddOn,ddStop;
datetime ddResume;
bool     frClosed;
int      nTrades;
int      lastBS,lastSS;

// TP Stop state
bool     tpStopOn;      // TP Stop sedang aktif
bool     tpStopTotal;   // Pilihan: berhenti total
datetime tpStopResume;  // Pilihan: resume besok
double   dayStartBal;   // Balance awal hari ini (untuk hitung profit harian)
int      dayStartDay;   // Hari terakhir reset dayStartBal

#define PRE    "SEA_"
#define PW     218
#define PH     332
#define RH     22
#define FNT    "Consolas"
#define FSZ    9

//=== INIT ===========================================================

int OnInit()
{
   pip      = _Point*10;
   hwm      = AccountInfoDouble(ACCOUNT_BALANCE);
   ddOn     = false; ddStop=false; ddResume=0;
   frClosed = false; nTrades=0;
   lastBS   = 0; lastSS=0;
   // TP Stop init
   tpStopOn     = false;
   tpStopTotal  = false;
   tpStopResume = 0;
   dayStartBal  = AccountInfoDouble(ACCOUNT_BALANCE);
   dayStartDay  = -1;

   h_ef1  = iMA(_Symbol,PERIOD_M1, EMA_Fast,0,MODE_EMA,PRICE_CLOSE);
   h_es1  = iMA(_Symbol,PERIOD_M1, EMA_Slow,0,MODE_EMA,PRICE_CLOSE);
   h_ef5  = iMA(_Symbol,PERIOD_M5, EMA_Fast,0,MODE_EMA,PRICE_CLOSE);
   h_es5  = iMA(_Symbol,PERIOD_M5, EMA_Slow,0,MODE_EMA,PRICE_CLOSE);
   h_ef15 = iMA(_Symbol,PERIOD_M15,EMA_Fast,0,MODE_EMA,PRICE_CLOSE);
   h_es15 = iMA(_Symbol,PERIOD_M15,EMA_Slow,0,MODE_EMA,PRICE_CLOSE);
   h_ef30 = iMA(_Symbol,PERIOD_M30,EMA_Fast,0,MODE_EMA,PRICE_CLOSE);
   h_es30 = iMA(_Symbol,PERIOD_M30,EMA_Slow,0,MODE_EMA,PRICE_CLOSE);
   h_e21  = iMA(_Symbol,PERIOD_M5, 21,      0,MODE_EMA,PRICE_CLOSE);
   h_e50  = iMA(_Symbol,PERIOD_M5, 50,      0,MODE_EMA,PRICE_CLOSE);
   h_rsi1 = iRSI(_Symbol,PERIOD_M1,RSI_Period,PRICE_CLOSE);
   h_rsi5 = iRSI(_Symbol,PERIOD_M5,RSI_Period,PRICE_CLOSE);

   if(h_ef1==INVALID_HANDLE||h_es1==INVALID_HANDLE||
      h_ef5==INVALID_HANDLE||h_es5==INVALID_HANDLE||
      h_ef15==INVALID_HANDLE||h_es15==INVALID_HANDLE||
      h_ef30==INVALID_HANDLE||h_es30==INVALID_HANDLE||
      h_e21==INVALID_HANDLE||h_e50==INVALID_HANDLE||
      h_rsi1==INVALID_HANDLE||h_rsi5==INVALID_HANDLE)
   { Alert("Handle gagal!"); return INIT_FAILED; }

   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(10);
   trade.SetTypeFilling(ORDER_FILLING_IOC);

   PanelCreate(); PanelUpdate();
   Print("EA v5.30 | MinScore:",MinScore," | HWM:$",hwm);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int r)
{
   int h[]={h_ef1,h_es1,h_ef5,h_es5,h_ef15,h_es15,h_ef30,h_es30,h_e21,h_e50,h_rsi1,h_rsi5};
   for(int i=0;i<ArraySize(h);i++) IndicatorRelease(h[i]);
   PanelDelete();
}

//=== TICK ===========================================================

void OnTick()
{
   double bal=AccountInfoDouble(ACCOUNT_BALANCE);
   double eq =AccountInfoDouble(ACCOUNT_EQUITY);
   if(bal>hwm) hwm=bal;

   double ddPct=(hwm>0)?(hwm-eq)/hwm*100.0:0.0;

   // DD cutoff
   if(!ddOn && ddPct>=MaxDD_Pct)
   {
      ddOn=true; ddStop=false; ddResume=0;
      CloseAll();
      if(DD_Action==DD_STOP_TOTAL) ddStop=true;
      else if(DD_Action==DD_PAUSE_ONEDAY)
      {
         MqlDateTime d; TimeToStruct(TimeCurrent(),d);
         d.hour=Hour_Start; d.min=0; d.sec=0;
         ddResume=StructToTime(d)+86400;
      }
      else { ddOn=false; hwm=bal; }
      PanelUpdate(); return;
   }
   if(ddOn && ddStop)           { PanelUpdate(); return; }
   if(ddOn && ddResume>0)
   {
      if(TimeCurrent()>=ddResume) { ddOn=false; ddResume=0; hwm=bal; }
      else                        { PanelUpdate(); return; }
   }
   if(ddOn) { PanelUpdate(); return; }

   // === RESET BALANCE HARIAN ===
   // dayStartBal direset tiap hari baru saat tidak ada posisi terbuka
   {
      MqlDateTime dn; TimeToStruct(TimeCurrent(),dn);
      if(dn.day != dayStartDay && NPos()==0)
      {
         dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);
         dayStartDay = dn.day;
         // Reset TP Stop harian
         if(tpStopOn && !tpStopTotal && tpStopResume==0)
            tpStopOn = false; // resume otomatis awal hari baru
      }
   }

   // === TP STOP CHECK ===
   if(UseTPStop && !tpStopOn)
   {
      double dailyProfit = AccountInfoDouble(ACCOUNT_BALANCE) - dayStartBal;
      bool hitUSD = (TPStop_USD > 0 && dailyProfit >= TPStop_USD);
      bool hitPct = (TPStop_Pct > 0 && dayStartBal > 0 &&
                     dailyProfit / dayStartBal * 100.0 >= TPStop_Pct);

      if(hitUSD || hitPct)
      {
         tpStopOn = true; tpStopTotal=false; tpStopResume=0;
         string reason = hitUSD
            ? "USD target $"+DoubleToString(TPStop_USD,2)
            : "PCT target "+DoubleToString(TPStop_Pct,1)+"%";
         Print("TP STOP! Profit harian: $",DoubleToString(dailyProfit,2),
               " | Alasan: ",reason," | Aksi: ",EnumToString(TP_Action));
         CloseAll();

         if(TP_Action == TP_STOP_TOTAL)
            tpStopTotal = true;
         else if(TP_Action == TP_PAUSE_ONEDAY)
         {
            MqlDateTime dt; TimeToStruct(TimeCurrent(),dt);
            dt.hour=Hour_Start; dt.min=0; dt.sec=0;
            tpStopResume = StructToTime(dt)+86400;
            Print("TP Stop: Resume besok jam ",Hour_Start,":00 → ",TimeToString(tpStopResume));
         }
         else // TP_CONTINUE — lanjut terus, tidak berhenti
            tpStopOn = false;

         PanelUpdate(); return;
      }
   }

   // Cek resume TP Stop (berhenti sehari)
   if(tpStopOn && tpStopResume>0 && TimeCurrent()>=tpStopResume)
   {
      tpStopOn=false; tpStopResume=0;
      dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);
      dayStartDay = -1; // force reset hari ini
      Print("TP Stop selesai. Resume trading. Balance: $",dayStartBal);
   }

   // Blokir entry jika TP Stop masih aktif
   if(tpStopOn && tpStopTotal)  { PanelUpdate(); return; }
   if(tpStopOn && tpStopResume>0){ PanelUpdate(); return; }

   ManageTP(); ManageTrail();
   PanelUpdate();

   if(UseTimeFilter && !TimeOK()) return;
   if(NPos()>=MaxPositions) return;

   // Baca indikator
   double ef1[2],es1[2],ef5[2],es5[2],ef15[2],es15[2],ef30[2],es30[2];
   double e21[1],e50[1],rsi1[3],rsi5[2];
   if(!Buf(h_ef1,ef1,2)||!Buf(h_es1,es1,2)) return;
   if(!Buf(h_ef5,ef5,2)||!Buf(h_es5,es5,2)) return;
   if(!Buf(h_ef15,ef15,2)||!Buf(h_es15,es15,2)) return;
   if(!Buf(h_ef30,ef30,2)||!Buf(h_es30,es30,2)) return;
   if(!Buf(h_e21,e21,1)||!Buf(h_e50,e50,1)) return;
   if(!Buf(h_rsi1,rsi1,3)||!Buf(h_rsi5,rsi5,2)) return;

   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);

   //--- TREND WAJIB: min 2/3 TF searah
   int tb=((ef5[0]>es5[0])?1:0)+((ef15[0]>es15[0])?1:0)+((ef30[0]>es30[0])?1:0);
   int ts=((ef5[0]<es5[0])?1:0)+((ef15[0]<es15[0])?1:0)+((ef30[0]<es30[0])?1:0);
   if(tb<2 && ts<2) { lastBS=0; lastSS=0; return; }

   //--- CORE SCORES (3 poin) ---
   int sb=0, ss=0;

   // C1: EMA M1 alignment
   if(ef1[0]>es1[0]) sb++;
   if(ef1[0]<es1[0]) ss++;

   // C2: RSI tidak di zona ekstrem
   if(rsi1[0]>RSI_OS && rsi1[0]<RSI_OB) sb++;
   if(rsi1[0]>RSI_OS && rsi1[0]<RSI_OB) ss++;

   // C3: Candle M5 konfirmasi arah (bullish/bearish candle cukup)
   double o1=iOpen(_Symbol,PERIOD_M5,1), c1=iClose(_Symbol,PERIOD_M5,1);
   double body1=MathAbs(c1-o1);
   if(c1>o1 && body1>pip*1.0) sb++; // bullish candle minimal 1 pip
   if(c1<o1 && body1>pip*1.0) ss++; // bearish candle minimal 1 pip

   //--- BONUS SCORES (4 poin, opsional) ---

   // B1: EMA 21/50 Dynamic SR
   if(UseBonus_EMASR)
   {
      double z=EMA_SR_Pip*pip;
      if(MathAbs(ask-e21[0])<=z||MathAbs(ask-e50[0])<=z) sb++;
      if(MathAbs(bid-e21[0])<=z||MathAbs(bid-e50[0])<=z) ss++;
   }

   // B2: Fair Value Gap
   // Bullish FVG: high[i+1] < low[i-1] — harga sekarang dalam gap
   // Bearish FVG: low[i+1]  > high[i-1] — harga sekarang dalam gap
   if(UseBonus_FVG)
   {
      double minG=FVG_MinPip*pip;
      bool fb=false,fs=false;
      for(int i=1;i<=FVG_Lookback&&!fb&&!fs;i++)
      {
         double hL=iHigh(_Symbol,PERIOD_M5,i+1); // high candle kiri
         double lR=iLow (_Symbol,PERIOD_M5,i-1); // low candle kanan
         double lL=iLow (_Symbol,PERIOD_M5,i+1); // low candle kiri
         double hR=iHigh(_Symbol,PERIOD_M5,i-1); // high candle kanan
         // Bullish: gap = hL < lR, harga ask masuk gap
         if(lR-hL>=minG && ask>=hL && ask<=lR) fb=true;
         // Bearish: gap = lL > hR, harga bid masuk gap
         if(lL-hR>=minG && bid>=hR && bid<=lL) fs=true;
      }
      if(fb) sb++;
      if(fs) ss++;
   }

   // B3: Break of Structure
   // Cari highest high & lowest low dalam lookback (mulai candle 2)
   // BOS bull: close M5[1] > highest → harga break ke atas
   // BOS bear: close M5[1] < lowest  → harga break ke bawah
   if(UseBonus_BOS)
   {
      double hi=-DBL_MAX, lo=DBL_MAX;
      for(int i=2;i<=BOS_Lookback;i++)
      {
         hi=MathMax(hi,iHigh(_Symbol,PERIOD_M5,i));
         lo=MathMin(lo,iLow (_Symbol,PERIOD_M5,i));
      }
      double cl=iClose(_Symbol,PERIOD_M5,1);
      if(hi>-DBL_MAX && cl>hi) sb++;
      if(lo<DBL_MAX  && cl<lo) ss++;
   }

   // B4: RSI Momentum — baru keluar zona ekstrem (2 candle lalu masih di dalamnya)
   if(UseBonus_RSIMom)
   {
      if(rsi1[2]<=RSI_OS  && rsi1[0]>RSI_OS)  sb++;
      if(rsi1[2]>=RSI_OB  && rsi1[0]<RSI_OB)  ss++;
   }

   lastBS=sb; lastSS=ss;

   //--- ENTRY ---
   double lot    = CalcLot();
   double slDist = CalcSLDist(lot); // Hard SL dalam price distance

   if(tb>=2 && sb>=MinScore)
   {
      double slB = (slDist>0) ? NormalizeDouble(ask-slDist,_Digits) : 0;
      if(trade.Buy(lot,_Symbol,ask,slB,0,"B:"+IntegerToString(sb)))
      { nTrades++; Print("BUY @",ask," SL:",slB," S:",sb,"/7 Lot:",lot); }
   }
   if(ts>=2 && ss>=MinScore)
   {
      double slS = (slDist>0) ? NormalizeDouble(bid+slDist,_Digits) : 0;
      if(trade.Sell(lot,_Symbol,bid,slS,0,"S:"+IntegerToString(ss)))
      { nTrades++; Print("SELL @",bid," SL:",slS," S:",ss,"/7 Lot:",lot); }
   }
}

//=== HELPERS ========================================================

bool Buf(int h,double &b[],int n)
{ if(CopyBuffer(h,0,0,n,b)<n) return false; ArraySetAsSeries(b,true); return true; }

double CalcLot()
{
   if(!UseDynamicLot) return MinLot;
   double bal=AccountInfoDouble(ACCOUNT_BALANCE);
   double stp=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   double raw=(bal*RiskPct/100.0)/1000.0;
   raw=MathFloor(raw/stp)*stp;
   raw=MathMax(raw,MathMax(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),MinLot));
   raw=MathMin(raw,MathMin(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),MaxLot));
   return NormalizeDouble(raw,2);
}

// Hitung SL distance dalam price dari target USD
// Contoh: HardSL_USD=$1.50, lot=0.01 XAUUSD → berapa pip SL-nya?
double CalcSLDist(double lot)
{
   if(HardSL_USD<=0 || lot<=0) return 0;
   double tickVal  = SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tickVal<=0 || tickSize<=0) return 0;
   // USD per pip = tickVal/tickSize * pip * lot
   double usdPerPip = (tickVal/tickSize) * pip * lot;
   if(usdPerPip<=0) return 0;
   double slPip = HardSL_USD / usdPerPip;
   return NormalizeDouble(slPip * pip, _Digits);
}

int NPos(){
   int c=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
      if(posInfo.SelectByIndex(i)&&posInfo.Symbol()==_Symbol&&posInfo.Magic()==MagicNumber) c++;
   return c;
}

void CloseAll()
{
   ulong t[]; int n=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      if(!posInfo.SelectByIndex(i)) continue;
      if(posInfo.Symbol()!=_Symbol||posInfo.Magic()!=MagicNumber) continue;
      ArrayResize(t,n+1); t[n++]=posInfo.Ticket();
   }
   for(int i=0;i<n;i++) if(PositionSelectByTicket(t[i])) trade.PositionClose(t[i]);
}

void ManageTP()
{
   ulong t[]; int n=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      if(!posInfo.SelectByIndex(i)) continue;
      if(posInfo.Symbol()!=_Symbol||posInfo.Magic()!=MagicNumber) continue;
      ArrayResize(t,n+1); t[n++]=posInfo.Ticket();
   }
   for(int i=0;i<n;i++)
      if(PositionSelectByTicket(t[i]) && posInfo.Profit()>=TakeProfit_USD)
         trade.PositionClose(t[i]);
}

void ManageTrail()
{
   ulong t[]; int n=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      if(!posInfo.SelectByIndex(i)) continue;
      if(posInfo.Symbol()!=_Symbol||posInfo.Magic()!=MagicNumber) continue;
      ArrayResize(t,n+1); t[n++]=posInfo.Ticket();
   }
   for(int i=0;i<n;i++)
   {
      ulong tk=t[i];
      if(!PositionSelectByTicket(tk)) continue;
      double sl=posInfo.StopLoss();
      double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
      double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
      double td=Trail_Stop_Pip*pip, ts=Trail_Step_Pip*pip;
      if(posInfo.PositionType()==POSITION_TYPE_BUY && posInfo.Profit()>=Trail_StartUSD)
      {
         double ns=NormalizeDouble(bid-td,_Digits);
         if(ns>sl+ts||sl==0) if(PositionSelectByTicket(tk)) trade.PositionModify(tk,ns,0);
      }
      else if(posInfo.PositionType()==POSITION_TYPE_SELL && posInfo.Profit()>=Trail_StartUSD)
      {
         double ns=NormalizeDouble(ask+td,_Digits);
         if(ns<sl-ts||sl==0) if(PositionSelectByTicket(tk)) trade.PositionModify(tk,ns,0);
      }
   }
}

bool TimeOK()
{
   MqlDateTime d; TimeToStruct(TimeCurrent(),d);
   int dow=d.day_of_week, hr=d.hour;

   // Blokir weekend
   if(dow==0||dow==6) return false;

   // Jumat sore: close semua posisi SEKALI, lalu tetap boleh entry
   if(CloseOnFriday && dow==5 && hr>=Friday_StopHour)
   {
      if(!frClosed && NPos()>0) { CloseAll(); frClosed=true; }
      // Tetap return false — tidak entry baru setelah jam tutup Jumat
      return false;
   }

   // Reset flag Jumat saat hari lain
   if(dow!=5) frClosed=false;

   // Di luar jam trading
   if(hr<Hour_Start || hr>=Hour_End) return false;

   return true;
}

// Cek sesi untuk panel saja (tanpa side effect CloseAll)
bool IsInSession()
{
   MqlDateTime d; TimeToStruct(TimeCurrent(),d);
   int dow=d.day_of_week, hr=d.hour;
   if(dow==0||dow==6) return false;
   if(CloseOnFriday && dow==5 && hr>=Friday_StopHour) return false;
   if(hr<Hour_Start || hr>=Hour_End) return false;
   return true;
}

//=== PANEL ==========================================================

void PanelCreate()
{
   OR(PRE"bg",Panel_X,Panel_Y,PW,PH,Panel_BG);
   OT(PRE"ttl",Panel_X+8,Panel_Y+6, "  ★ SCALPING EA v5.3 ★",Col_Title,9,true);
   OT(PRE"sym",Panel_X+8,Panel_Y+22,"",Col_Label,FSZ,false);
   OT(PRE"div",Panel_X+4,Panel_Y+34,"------------------------------",C'50,50,80',8,false);
   int y=Panel_Y+46;
   string lb[]={"Status","Session","Balance","Equity","DD%","Float P/L","Positions","TP","Lot","Score B|S","TP Stop","Trades"};
   string vk[]={"st","ss","ba","eq","dd","fl","po","tp","lt","sc","ts","tr"};
   for(int i=0;i<ArraySize(lb);i++)
   {
      OT(PRE"l_"+vk[i],Panel_X+8,  y,lb[i],Col_Label,FSZ,false);
      OT(PRE"v_"+vk[i],Panel_X+118,y,"",   Col_Value,FSZ,false);
      y+=RH;
   }
   ChartRedraw();
}

void OT(string n,int x,int y,string t,color c,int fs,bool b)
{
   ObjectDelete(0,n);
   ObjectCreate(0,n,OBJ_LABEL,0,0,0);
   ObjectSetInteger(0,n,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,n,OBJPROP_YDISTANCE,y);
   ObjectSetString( 0,n,OBJPROP_TEXT,t);
   ObjectSetString( 0,n,OBJPROP_FONT,b?FNT" Bold":FNT);
   ObjectSetInteger(0,n,OBJPROP_FONTSIZE,b?fs+1:fs);
   ObjectSetInteger(0,n,OBJPROP_COLOR,c);
   ObjectSetInteger(0,n,OBJPROP_BACK,false);
   ObjectSetInteger(0,n,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,n,OBJPROP_CORNER,CORNER_LEFT_UPPER);
}

void OR(string n,int x,int y,int w,int h,color bg)
{
   ObjectDelete(0,n);
   ObjectCreate(0,n,OBJ_RECTANGLE_LABEL,0,0,0);
   ObjectSetInteger(0,n,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,n,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,n,OBJPROP_XSIZE,w);
   ObjectSetInteger(0,n,OBJPROP_YSIZE,h);
   ObjectSetInteger(0,n,OBJPROP_BGCOLOR,bg);
   ObjectSetInteger(0,n,OBJPROP_BORDER_TYPE,BORDER_FLAT);
   ObjectSetInteger(0,n,OBJPROP_COLOR,C'60,60,100');
   ObjectSetInteger(0,n,OBJPROP_BACK,false);
   ObjectSetInteger(0,n,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,n,OBJPROP_CORNER,CORNER_LEFT_UPPER);
}

void OB(string n,int x,int y,int w,int h,string t,color tc,color bg)
{
   ObjectDelete(0,n);
   ObjectCreate(0,n,OBJ_BUTTON,0,0,0);
   ObjectSetInteger(0,n,OBJPROP_XDISTANCE,x); ObjectSetInteger(0,n,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,n,OBJPROP_XSIZE,w);     ObjectSetInteger(0,n,OBJPROP_YSIZE,h);
   ObjectSetString( 0,n,OBJPROP_TEXT,t);      ObjectSetString( 0,n,OBJPROP_FONT,FNT);
   ObjectSetInteger(0,n,OBJPROP_FONTSIZE,FSZ);ObjectSetInteger(0,n,OBJPROP_COLOR,tc);
   ObjectSetInteger(0,n,OBJPROP_BGCOLOR,bg);  ObjectSetInteger(0,n,OBJPROP_BORDER_COLOR,C'80,80,80');
   ObjectSetInteger(0,n,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,n,OBJPROP_SELECTABLE,true); ObjectSetInteger(0,n,OBJPROP_BACK,false);
}

void SV(string k,string t,color c)
{ ObjectSetString(0,PRE"v_"+k,OBJPROP_TEXT,t); ObjectSetInteger(0,PRE"v_"+k,OBJPROP_COLOR,c); }

void PanelUpdate()
{
   double bal=AccountInfoDouble(ACCOUNT_BALANCE);
   double eq =AccountInfoDouble(ACCOUNT_EQUITY);
   double ddp=(hwm>0)?(hwm-eq)/hwm*100.0:0.0;
   int    np =NPos();
   double fl =0;
   for(int i=PositionsTotal()-1;i>=0;i--)
      if(posInfo.SelectByIndex(i)&&posInfo.Symbol()==_Symbol&&posInfo.Magic()==MagicNumber)
         fl+=posInfo.Profit();

   // Sym + spread
   ObjectSetString(0,PRE"sym",OBJPROP_TEXT,
      _Symbol+"  spd:"+DoubleToString(SymbolInfoInteger(_Symbol,SYMBOL_SPREAD)*_Point/pip,1)+"p");

   // Status
   string st; color sc;
   if(ddOn&&ddStop)               {st="DD STOP";    sc=Col_Loss;}
   else if(ddOn&&ddResume>0)      {st="DD Pause";   sc=Col_Warning;}
   else if(ddOn)                  {st="DD Hit!";    sc=Col_Warning;}
   else if(tpStopOn&&tpStopTotal) {st="TP STOP";    sc=Col_Loss;}
   else if(tpStopOn&&tpStopResume>0){st="TP Pause"; sc=Col_Warning;}
   else if(tpStopOn)              {st="TP Hit!";    sc=Col_Warning;}
   else if(UseTimeFilter&&!IsInSession()){st="Off-Hours"; sc=Col_Label;}
   else if(np==0)                 {st="Waiting";    sc=Col_Label;}
   else                           {st="Trading";    sc=Col_Profit;}
   SV("st",st,sc);

   // Session
   MqlDateTime d; TimeToStruct(TimeCurrent(),d);
   bool frs=d.day_of_week==5&&d.hour>=Friday_StopHour;
   bool we =d.day_of_week==0||d.day_of_week==6;
   bool inh=d.hour>=Hour_Start&&d.hour<Hour_End;
   string ss2; color sc2;
   if(we)       {ss2="Weekend";   sc2=Col_Label;}
   else if(frs) {ss2="Fri ✓";    sc2=Col_Profit;}
   else if(!inh){ss2=IntegerToString(Hour_Start)+"-"+IntegerToString(Hour_End)+" OFF"; sc2=Col_Label;}
   else         {ss2=IntegerToString(Hour_Start)+"-"+IntegerToString(Hour_End)+" ON";  sc2=Col_Profit;}
   SV("ss",ss2,sc2);

   SV("ba","$"+DoubleToString(bal,2),Col_Value);
   SV("eq","$"+DoubleToString(eq,2),(eq>=bal)?Col_Profit:Col_Loss);

   color dc=(ddp<=0)?Col_Profit:(ddp<MaxDD_Pct*0.5)?Col_Value:(ddp<MaxDD_Pct)?Col_Warning:Col_Loss;
   SV("dd",DoubleToString(ddp,1)+"% / "+DoubleToString(MaxDD_Pct,0)+"% HWM:$"+DoubleToString(hwm,0),dc);

   SV("fl",(fl>=0?"+":"")+DoubleToString(fl,2),(fl>=0)?Col_Profit:Col_Loss);
   SV("po",IntegerToString(np)+" / "+IntegerToString(MaxPositions),Col_Value);
   SV("tp","$"+DoubleToString(TakeProfit_USD,2),Col_Value);

   double lot=CalcLot();
   SV("lt",DoubleToString(lot,2)+(UseDynamicLot?" ("+DoubleToString(RiskPct,1)+"%)":""),Col_Value);

   // Score — warna hijau jika sudah cukup
   color skc=(MathMax(lastBS,lastSS)>=MinScore)?Col_Profit:Col_Label;
   SV("sc","B:"+IntegerToString(lastBS)+" S:"+IntegerToString(lastSS)+" /"+IntegerToString(MinScore),skc);

   // TP Stop status
   string tsTxt; color tsCol;
   if(!UseTPStop)
   { tsTxt="OFF"; tsCol=Col_Label; }
   else if(tpStopOn && tpStopTotal)
   { tsTxt="STOP TOTAL"; tsCol=Col_Loss; }
   else if(tpStopOn && tpStopResume>0)
   {
      tsTxt="Pause → "+TimeToString(tpStopResume,TIME_MINUTES);
      tsCol=Col_Warning;
   }
   else if(tpStopOn)
   { tsTxt="Hit!"; tsCol=Col_Warning; }
   else
   {
      double dp=AccountInfoDouble(ACCOUNT_BALANCE)-dayStartBal;
      double pct=(dayStartBal>0)?dp/dayStartBal*100.0:0.0;
      tsTxt="$"+DoubleToString(dp,2)+" ("+DoubleToString(pct,1)+"%)";
      tsCol=(dp>=0)?Col_Profit:Col_Loss;
   }
   SV("ts",tsTxt,tsCol);

   SV("tr",IntegerToString(nTrades),Col_Value);

   ChartRedraw();
}

void PanelDelete() { ObjectsDeleteAll(0,PRE); ChartRedraw(); }

void OnChartEvent(const int id,const long &lp,const double &dp,const string &sp)
{
   if(id!=CHARTEVENT_OBJECT_CLICK) return;
   double bal=AccountInfoDouble(ACCOUNT_BALANCE);
   if(sp==PRE"btn_stop") { ddStop=true; HideDDBtn(); PanelUpdate(); }
   else if(sp==PRE"btn_day")
   {
      MqlDateTime d; TimeToStruct(TimeCurrent(),d);
      d.hour=Hour_Start; d.min=0; d.sec=0;
      ddResume=StructToTime(d)+86400; HideDDBtn(); PanelUpdate();
   }
   else if(sp==PRE"btn_cont") { ddOn=false; ddStop=false; ddResume=0; hwm=bal; HideDDBtn(); PanelUpdate(); }
}

void ShowDDBtn()
{
   int bx=Panel_X,by=Panel_Y+PH+5,bw=PW,bh=26;
   OR(PRE"ddbg",bx,by,bw,105,C'40,10,10');
   OT(PRE"ddtl",bx+8,by+5,"DD Hit! Pilih:",clrOrangeRed,9,true);
   OB(PRE"btn_stop",bx+5,by+24,bw-10,bh,"[1] Berhenti Total",      clrWhite,C'140,20,20');
   OB(PRE"btn_day", bx+5,by+54,bw-10,bh,"[2] Berhenti Sehari",     clrWhite,C'140,90,10');
   OB(PRE"btn_cont",bx+5,by+84,bw-10,bh,"[3] Lanjut Sekarang",     clrWhite,C'10,100,20');
   ChartRedraw();
}

void HideDDBtn()
{
   string obs[]={PRE"ddbg",PRE"ddtl",PRE"btn_stop",PRE"btn_day",PRE"btn_cont"};
   for(int i=0;i<ArraySize(obs);i++) ObjectDelete(0,obs[i]);
   ChartRedraw();
}
//+------------------------------------------------------------------+