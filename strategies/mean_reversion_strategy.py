import talib
import numpy as np
import pandas as pd
from strategies.base_strategy import BaseStrategy
from utils.utils import TradeLogger

class MeanReversionStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("均值回归策略", initial_capital, commission_rate)
        # 缩短均值回归周期
        self.ma_short = 3  # 原为5
        self.ma_medium = 8  # 原为10
        self.ma_long = 15  # 原为20
        
        # 调整偏离阈值
        self.std_dev_period = 15  # 原为20
        self.entry_std_dev = 1.5  # 原为2.0
        self.exit_std_dev = 0.5  # 原为1.0
        
        # 调整RSI参数
        self.rsi_period = 10  # 原为14
        self.rsi_upper = 75  # 原为70
        self.rsi_lower = 25  # 原为30
        
        # 风控参数
        self.stop_loss = 0.03  # 3%止损
        self.profit_target = 0.05  # 5%止盈
        self.trailing_stop = 0.02  # 2%追踪止损
        self.volume_period = 5
        self._current_row = None

    def calculate_signals(self, data):
        df = data.copy()
        
        # 计算移动平均
        df['ma_short'] = talib.SMA(df['close'], timeperiod=self.ma_short)
        df['ma_medium'] = talib.SMA(df['close'], timeperiod=self.ma_medium)
        df['ma_long'] = talib.SMA(df['close'], timeperiod=self.ma_long)
        
        # 计算标准差通道
        df['std_dev'] = talib.STDDEV(df['close'], timeperiod=self.std_dev_period)
        df['upper_band'] = df['ma_medium'] + (df['std_dev'] * self.entry_std_dev)
        df['lower_band'] = df['ma_medium'] - (df['std_dev'] * self.entry_std_dev)
        
        # 计算RSI
        df['rsi'] = talib.RSI(df['close'], timeperiod=self.rsi_period)
        
        # 计算价格动量
        df['momentum'] = talib.MOM(df['close'], timeperiod=10)
        
        # 计算成交量指标
        df['volume_ma'] = talib.SMA(df['volume'], timeperiod=20)
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        return df

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        # 计算价格偏离度
        price_deviation = (row['close'] - row['ma_medium']) / row['std_dev']
        
        # 买入条件：
        # 1. 价格低于下轨
        price_low = row['close'] < row['lower_band']
        
        # 2. RSI超卖
        rsi_low = row['rsi'] < self.rsi_lower
        
        # 3. 动量反转
        momentum_up = row['momentum'] > prev_row['momentum']
        
        # 4. 均线支撑
        ma_support = row['ma_short'] > prev_row['ma_short']
        
        # 5. 成交量确认
        volume_confirm = row['volume_ratio'] > 0.8
        
        # 卖出条件：
        # 1. 价格高于上轨
        price_high = row['close'] > row['upper_band']
        
        # 2. RSI超买
        rsi_high = row['rsi'] > self.rsi_upper
        
        # 3. 动量减弱
        momentum_down = row['momentum'] < prev_row['momentum']
        
        # 4. 均线阻力
        ma_resistance = row['ma_short'] < prev_row['ma_short']
        
        if self.position <= 0:
            # 买入信号需要满足至少2个条件
            conditions = [price_low, rsi_low, momentum_up, ma_support]
            if sum(conditions) >= 2 and volume_confirm:
                signal = 'BUY'
        else:
            # 动态止损价格计算
            if hasattr(self, 'highest_price'):
                trailing_stop_price = self.highest_price * (1 - self.trailing_stop)
            else:
                trailing_stop_price = self.entry_price * (1 - self.stop_loss)
            
            # 更新最高价
            if row['close'] > getattr(self, 'highest_price', 0):
                self.highest_price = row['close']
            
            # 止损条件判断
            stop_loss_triggered = (row['close'] < trailing_stop_price)
            
            # 止盈条件判断
            take_profit = ((row['close'] - self.entry_price) / self.entry_price > self.profit_target)
            
            # 卖出信号需要满足至少2个条件或触发止损/止盈
            conditions = [price_high, rsi_high, momentum_down, ma_resistance]
            if sum(conditions) >= 2 or stop_loss_triggered or take_profit:
                signal = 'SELL'
                if hasattr(self, 'highest_price'):
                    delattr(self, 'highest_price')
        
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