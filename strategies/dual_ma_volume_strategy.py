import talib
import numpy as np
from strategies.base_strategy import BaseStrategy
from utils.utils import TradeLogger
import pandas as pd

class DualMAVolumeStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("双均线量策略", initial_capital, commission_rate)
        self.fast_period = 3
        self.slow_period = 10
        self.volume_period = 7
        self.stop_loss = 0.02
        self.profit_target = 0.03
        self._current_row = None

    def calculate_signals(self, data):
        df = data.copy()
        
        # 计算快慢均线
        df['fast_ma'] = talib.EMA(df['close'], self.fast_period)
        df['slow_ma'] = talib.EMA(df['close'], self.slow_period)
        
        # 计算成交量指标
        df['volume_ma'] = talib.SMA(df['volume'], self.volume_period)
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # 计算趋势强度和动量
        df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
        df['roc'] = talib.ROC(df['close'], timeperiod=10)
        
        # 计算额外的技术指标
        df['rsi'] = talib.RSI(df['close'], timeperiod=14)
        df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(
            df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        return df

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        # 买入条件：
        # 1. 快线上穿慢线
        # 2. 成交量是均量的1.1倍以上（降低要求）
        # 3. ADX > 15 (降低要求)
        # 4. ROC > -1 (允许轻微下跌)
        # 5. RSI < 70 (非超买)
        # 6. MACD柱状图向上
        if (prev_row['fast_ma'] <= prev_row['slow_ma'] and 
            row['fast_ma'] > row['slow_ma'] and 
            row['volume_ratio'] > 1.1 and
            row['adx'] > 15 and
            row['roc'] > -1 and
            row['rsi'] < 70 and
            row['macd_hist'] > prev_row['macd_hist']):
            signal = 'BUY'
            
        # 卖出条件：
        # 1. 快线下穿慢线
        # 2. 成交量放大
        # 3. ADX > 15
        # 4. RSI > 30 (非超卖)
        elif (prev_row['fast_ma'] >= prev_row['slow_ma'] and 
              row['fast_ma'] < row['slow_ma'] and 
              row['volume_ratio'] > 1.1 and
              row['adx'] > 15 and
              row['rsi'] > 30):
            signal = 'SELL'
            
        # 止损止盈
        if self.position > 0:
            if row['close'] < self.entry_price * (1 - self.stop_loss):
                signal = 'SELL'
            elif row['close'] > self.entry_price * (1 + self.profit_target):
                signal = 'SELL'
                
        return signal

    def execute_trade(self, date, price, signal, volume):
        """执行交易"""
        if signal == 'BUY' and self.position <= 0:
            # 计算可买入股数
            available_capital = self.capital
            max_shares = int(available_capital / (price * (1 + self.commission_rate)))
            shares = min(max_shares, int(volume * 0.1))  # 限制单次交易量
            
            if shares > 0:
                cost = shares * price
                commission = cost * self.commission_rate
                
                if cost + commission <= self.capital:
                    self.position = shares
                    self.capital -= (cost + commission)
                    self.entry_price = price
                    
                    trade = {
                        'date': date,
                        'type': '买入',
                        'price': price,
                        'shares': shares,
                        'amount': cost,
                        'commission': commission,
                        'capital': self.capital
                    }
                    self.trades.append(trade)
                    TradeLogger.print_trade(trade, self.name, self.position)
                    
        elif signal == 'SELL' and self.position > 0:
            shares = self.position
            revenue = shares * price
            commission = revenue * self.commission_rate
            
            self.capital += (revenue - commission)
            self.position = 0
            self.entry_price = 0
            
            trade = {
                'date': date,
                'type': '卖出',
                'price': price,
                'shares': shares,
                'amount': revenue,
                'commission': commission,
                'capital': self.capital
            }
            self.trades.append(trade)
            TradeLogger.print_trade(trade, self.name, self.position) 