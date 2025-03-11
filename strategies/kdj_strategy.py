import talib
from strategies.base_strategy import BaseStrategy

class KDJStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("KDJ策略", initial_capital, commission_rate)
        self.k_period = 5
        self.stop_loss = 0.015
        self.profit_target = 0.025
        self.volume_ma_period = 5
        self.trend_period = 10

    def calculate_signals(self, data):
        high_list = data['high'].rolling(self.k_period).max()
        low_list = data['low'].rolling(self.k_period).min()
        rsv = (data['close'] - low_list) / (high_list - low_list) * 100
        
        data['k'] = rsv.rolling(2).mean()
        data['d'] = data['k'].rolling(2).mean()
        data['j'] = 3 * data['k'] - 2 * data['d']
        
        data['volume_ma'] = talib.SMA(data['volume'], self.volume_ma_period)
        data['volume_ratio'] = data['volume'] / data['volume_ma']
        data['trend_ma'] = talib.EMA(data['close'], self.trend_period)
        data['rsi'] = talib.RSI(data['close'], timeperiod=10)
        data['adx'] = talib.ADX(data['high'], data['low'], data['close'], timeperiod=10)
        data['macd'], data['macd_signal'], data['macd_hist'] = talib.MACD(
            data['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        return data

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        k_cross_buy = prev_row['k'] < prev_row['d'] and row['k'] > row['d']
        j_cross_buy = prev_row['j'] < prev_row['k'] and row['j'] > row['k'] and row['j'] < 20
        if ((k_cross_buy or j_cross_buy) and 
            row['k'] < 40 and
            row['close'] > row['trend_ma'] * 0.98 and
            row['volume_ratio'] > 1.1 and
            row['adx'] > 15 and
            row['macd_hist'] > prev_row['macd_hist']):
            signal = 'BUY'
            
        k_cross_sell = prev_row['k'] > prev_row['d'] and row['k'] < row['d']
        j_cross_sell = prev_row['j'] > prev_row['k'] and row['j'] < row['k'] and row['j'] > 80
        if ((k_cross_sell or j_cross_sell) and 
            row['k'] > 60 and
            row['close'] < row['trend_ma'] and
            row['volume_ratio'] > 1.1 and
            row['macd_hist'] < prev_row['macd_hist']):
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