import talib
import numpy as np
import pandas as pd
from strategies.base_strategy import BaseStrategy
from utils.utils import TradeLogger

class VolumeBasedStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("量价分析策略", initial_capital, commission_rate)
        self.volume_ma_period = 10
        self.price_ma_period = 5
        self.volume_threshold = 1.3
        self.stop_loss = 0.02
        self.profit_target = 0.04
        self._current_row = None

    def calculate_signals(self, data):
        df = data.copy()
        
        # 计算成交量和价格的移动平均
        df['volume_ma'] = talib.EMA(df['volume'], self.volume_ma_period)
        df['price_ma'] = talib.EMA(df['close'], self.price_ma_period)
        df['price_ma_slow'] = talib.EMA(df['close'], 20)
        
        # 计算量比和趋势
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        df['momentum'] = talib.MOM(df['close'], timeperiod=10)
        df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
        
        # 计算OBV和其他指标
        df['obv'] = talib.OBV(df['close'], df['volume'])
        df['obv_ma'] = talib.EMA(df['obv'], 20)
        df['rsi'] = talib.RSI(df['close'], timeperiod=14)
        
        return df

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        # 买入条件：
        # 1. 放量上涨
        # 2. 价格在均线上方
        # 3. OBV确认
        # 4. ADX和RSI确认趋势
        volume_surge = row['volume_ratio'] > self.volume_threshold
        price_trend = (row['close'] > row['price_ma'] and 
                      row['price_ma'] > row['price_ma_slow'])
        obv_confirm = row['obv'] > row['obv_ma']
        trend_confirm = row['adx'] > 20 and row['rsi'] < 70
        
        if (volume_surge and price_trend and 
            obv_confirm and trend_confirm and 
            row['momentum'] > 0):
            signal = 'BUY'
        
        # 卖出条件
        elif (volume_surge and 
              row['close'] < row['price_ma'] and 
              row['momentum'] < 0 and
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