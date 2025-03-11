import talib
from strategies.base_strategy import BaseStrategy

class BollingerStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("布林带策略", initial_capital, commission_rate)
        self.period = 10
        self.std_dev = 1.5
        self.stop_loss = 0.015
        self.profit_target = 0.025
        self.trend_period = 20
        self.volume_ma_period = 5

    def calculate_signals(self, data):
        # 计算布林带
        data['middle'] = talib.SMA(data['close'], self.period)
        std = talib.STDDEV(data['close'], self.period)
        data['upper'] = data['middle'] + (std * self.std_dev)
        data['lower'] = data['middle'] - (std * self.std_dev)
        
        # 计算额外指标
        data['rsi'] = talib.RSI(data['close'], timeperiod=10)
        data['volume_ma'] = talib.SMA(data['volume'], self.volume_ma_period)
        data['volume_ratio'] = data['volume'] / data['volume_ma']
        data['trend_ma'] = talib.EMA(data['close'], self.trend_period)
        data['macd'], data['macd_signal'], data['macd_hist'] = talib.MACD(
            data['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        data['adx'] = talib.ADX(data['high'], data['low'], data['close'], timeperiod=10)
        
        # 计算布林带宽度和位置
        data['bb_width'] = (data['upper'] - data['lower']) / data['middle']
        data['bb_position'] = (data['close'] - data['lower']) / (data['upper'] - data['lower'])
        return data

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        # 买入条件：
        # 1. 价格接近或触及下轨
        # 2. RSI < 40 (大幅扩大超卖区间)
        # 3. 成交量确认
        # 4. MACD柱状图向上
        # 5. ADX > 15 (降低趋势要求)
        # 6. 布林带开口足够大
        if (row['close'] <= row['lower'] * 1.02 and
            row['rsi'] < 40 and
            row['volume_ratio'] > 1.1 and
            row['macd_hist'] > prev_row['macd_hist'] and
            row['adx'] > 15 and
            row['bb_width'] > 0.025):
            signal = 'BUY'
            
        # 卖出条件：
        # 1. 价格接近或触及上轨
        # 2. RSI > 60 (大幅扩大超买区间)
        # 3. 成交量确认
        # 4. MACD柱状图向下
        # 5. 布林带开口开始收窄
        elif (row['close'] >= row['upper'] * 0.98 and
              row['rsi'] > 60 and
              row['volume_ratio'] > 1.1 and
              row['macd_hist'] < prev_row['macd_hist'] and
              row['bb_width'] < prev_row['bb_width']):
            signal = 'SELL'
            
        # 动态止损止盈
        if self.position > 0:
            current_profit = (row['close'] - self.entry_price) / self.entry_price
            
            # 根据盈利情况调整止损点
            if current_profit > 0.02:
                stop_loss = max(self.stop_loss, current_profit - 0.015)
            else:
                stop_loss = self.stop_loss
                
            if current_profit < -stop_loss:
                signal = 'SELL'
            elif current_profit > self.profit_target:
                signal = 'SELL'
                
        return signal 