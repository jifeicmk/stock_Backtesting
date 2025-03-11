import talib
import numpy as np
import pandas as pd
from strategies.base_strategy import BaseStrategy
from utils.utils import TradeLogger

class TrendFollowingStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("趋势跟踪策略", initial_capital, commission_rate)
        self.short_period = 10
        self.long_period = 30
        self.atr_period = 14
        self.stop_multiple = 2.5
        self._current_row = None

    def calculate_signals(self, data):
        df = data.copy()
        
        # 计算多个时间周期的趋势指标
        df['ema_short'] = talib.EMA(df['close'], self.short_period)
        df['ema_long'] = talib.EMA(df['close'], self.long_period)
        
        # 计算ATR用于止损
        df['atr'] = talib.ATR(df['high'], df['low'], df['close'], self.atr_period)
        
        # 计算MACD
        df['macd'], df['signal'], df['hist'] = talib.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        
        # 计算趋势强度
        df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
        
        # 计算RSI
        df['rsi'] = talib.RSI(df['close'], timeperiod=14)
        return df

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        # 趋势确认条件
        trend_up = (row['ema_short'] > row['ema_long'] and 
                   row['hist'] > 0 and 
                   row['adx'] > 20 and
                   row['rsi'] < 70)
        
        trend_down = (row['ema_short'] < row['ema_long'] and 
                     row['hist'] < 0 and 
                     row['adx'] > 20 and
                     row['rsi'] > 30)
        
        if trend_up and prev_row['ema_short'] <= prev_row['ema_long']:
            signal = 'BUY'
        elif trend_down and prev_row['ema_short'] >= prev_row['ema_long']:
            signal = 'SELL'
            
        # 动态止损
        if self.position > 0:
            stop_price = self.entry_price - (row['atr'] * self.stop_multiple)
            if row['close'] < stop_price:
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