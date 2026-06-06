import time
import datetime
import os
import threading
from flask import Flask  # مكتبة لإنشاء سيرفر ويب مصغر
import pandas as pd
import ta
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# --- إعداد سيرفر الويب الوهمي ---
app = Flask('')

@app.route('/')
def home():
    return "🤖 Autonomous Trading Bot is Active and Running 24/7!"

# --- إعدادات Alpaca (يفضل وضعها كمتغيرات بيئة لاحقاً للأمان) ---
API_KEY = "PKME66J5QRKK7LJSNGESUZ7N5A"
SECRET_KEY = "2eTpmMnq1q6SERmefbRHYGx9azrym2bFpkfe17dvJ2Tk"
SYMBOL = "NVDA"
QTY = 10
TIMEFRAME = TimeFrame.Minute
TAKE_PROFIT_PCT = 0.015
STOP_LOSS_PCT = 0.005

trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

def is_market_open():
    try:
        clock = trading_client.get_clock()
        return clock.is_open
    except Exception:
        return False

def get_highly_accurate_signal():
    start_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=3)
    request_params = StockBarsRequest(symbol_or_symbols=SYMBOL, timeframe=TIMEFRAME, start=start_time)
    bars = data_client.get_stock_bars(request_params)
    df = bars.df.loc[SYMBOL]
    
    df['EMA_9'] = ta.trend.ema_indicator(df['close'], window=9)
    df['EMA_21'] = ta.trend.ema_indicator(df['close'], window=21)
    df['RSI'] = ta.momentum.rsi(df['close'], window=14)
    macd = ta.trend.macd(df['close'], window_slow=26, window_fast=12, window_sign=9)
    df['MACD'] = macd
    df['MACD_Signal'] = ta.trend.macd_signal(df['close'], window_slow=26, window_fast=12, window_sign=9)
    
    latest = df.iloc[-2]
    current_price = df.iloc[-1]['close']
    
    buy_condition = (
        latest['EMA_9'] > latest['EMA_21'] and
        40 < latest['RSI'] < 65 and
        latest['MACD'] > latest['MACD_Signal']
    )
    
    if buy_condition:
        return "STRONG_BUY", current_price
    return "HOLD", current_price

def has_open_position():
    try:
        positions = trading_client.get_all_positions()
        for p in positions:
            if p.symbol == SYMBOL:
                return True
        return False
    except Exception:
        return False

# حلقة التداول اللانهائية
def run_autonomous_bot():
    print("🤖 بدء تشغيل خوارزمية التداول المستقلة...")
    while True:
        try:
            if not is_market_open():
                print("💤 السوق مغلق حالياً...")
                time.sleep(300)
                continue
                
            if has_open_position():
                print("⏳ توجد صفقة مفتوحة، ننتظر الأوامر التلقائية المربوطة بها...")
                time.sleep(30)
                continue
                
            signal, price = get_highly_accurate_signal()
            if signal == "STRONG_BUY":
                take_profit_price = round(price * (1 + TAKE_PROFIT_PCT), 2)
                stop_loss_price = round(price * (1 - STOP_LOSS_PCT), 2)
                
                order_data = MarketOrderRequest(
                    symbol=SYMBOL, qty=QTY, side=OrderSide.BUY,
                    time_in_force=TimeInForce.GTC, order_class=OrderClass.BRACKET,
                    take_profit=TakeProfitRequest(limit_price=take_profit_price),
                    stop_loss=StopLossRequest(stop_price=stop_loss_price)
                )
                trading_client.submit_order(order_data=order_data)
                print(f"✅ تم دخول الصفقة بنجاح | الهدف: {take_profit_price} | الوقف: {stop_loss_price}")
                time.sleep(60)
        except Exception as e:
            print(f"⚠️ خطأ: {e}")
            time.sleep(10)
        time.sleep(15)

# تشغيل السيرفر والبوت معاً
if __name__ == "__main__":
    # تشغيل خوارزمية التداول في خيط خلفي منفصل لكي لا تعطّل السيرفر
    t = threading.Thread(target=run_autonomous_bot)
    t.start()
    
    # تشغيل سيرفر الويب على المنفذ الذي تحدده المنصة تلقائياً
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
