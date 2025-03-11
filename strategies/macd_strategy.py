import talib
from strategies.base_strategy import BaseStrategy

class MACDStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("MACD策略", initial_capital, commission_rate)
        self.fast = 6
        self.slow = 13
        self.signal = 5
        self.stop_loss = 0.015
        self.profit_target = 0.025
        self.volume_ma_period = 5

    def calculate_signals(self, data):
        data['macd'], data['macd_signal'], data['macd_hist'] = talib.MACD(
            data['close'], fastperiod=self.fast, slowperiod=self.slow, signalperiod=self.signal)
        data['volume_ma'] = talib.SMA(data['volume'], self.volume_ma_period)
        data['volume_ratio'] = data['volume'] / data['volume_ma']
        data['rsi'] = talib.RSI(data['close'], timeperiod=10)
        data['adx'] = talib.ADX(data['high'], data['low'], data['close'], timeperiod=10)
        data['ema5'] = talib.EMA(data['close'], timeperiod=5)
        data['ema10'] = talib.EMA(data['close'], timeperiod=10)
        return data

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        macd_buy = ((prev_row['macd_hist'] < 0 and row['macd_hist'] > 0) or 
                    (row['macd_hist'] > prev_row['macd_hist'] * 1.05))
        volume_buy = row['volume_ratio'] > 1.1
        rsi_buy = row['rsi'] < 65
        adx_buy = row['adx'] > 15
        trend_buy = row['ema5'] > row['ema10']
        
        if macd_buy and volume_buy and rsi_buy and adx_buy and trend_buy:
            signal = 'BUY'
            
        macd_sell = ((prev_row['macd_hist'] > 0 and row['macd_hist'] < 0) or 
                     (row['macd_hist'] < prev_row['macd_hist'] * 0.95))
        volume_sell = row['volume_ratio'] > 1.1
        rsi_sell = row['rsi'] > 35
        trend_sell = row['ema5'] < row['ema10']
        
        if macd_sell and volume_sell and rsi_sell and trend_sell:
            signal = 'SELL'
            
        if self.position > 0:
            current_profit = (row['close'] - self.entry_price) / self.entry_price
            
            if current_profit > 0.02:
                stop_loss = max(self.stop_loss, current_profit - 0.015)
            else:
                stop_loss = self.stop_loss
                
            if current_profit < -stop_loss:
                signal = 'SELL'
            elif current_profit > self.profit_target:
                signal = 'SELL'
                
        return signal 