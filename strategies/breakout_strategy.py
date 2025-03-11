import talib
import numpy as np
import pandas as pd
from strategies.base_strategy import BaseStrategy
from utils.utils import TradeLogger
from config.config import BREAKOUT_CONFIG

class BreakoutStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("突破策略", initial_capital, commission_rate)
        # 从配置文件加载参数
        self.price_period = BREAKOUT_CONFIG['price_period']
        self.volume_period = BREAKOUT_CONFIG['volume_period']
        self.breakout_threshold = BREAKOUT_CONFIG['breakout_threshold']
        self.volume_threshold = BREAKOUT_CONFIG['volume_threshold']
        
        # 趋势确认参数
        self.ma_short = BREAKOUT_CONFIG['ma_short']
        self.ma_long = BREAKOUT_CONFIG['ma_long']
        self.rsi_period = BREAKOUT_CONFIG['rsi_period']
        
        # MACD参数
        self.macd_fast = BREAKOUT_CONFIG['macd_fast']
        self.macd_slow = BREAKOUT_CONFIG['macd_slow']
        self.macd_signal = BREAKOUT_CONFIG['macd_signal']
        
        # 波动率参数
        self.volatility_period = BREAKOUT_CONFIG['volatility_period']
        self.min_volatility = BREAKOUT_CONFIG['min_volatility']
        self.max_volatility = BREAKOUT_CONFIG['max_volatility']
        self.atr_period = BREAKOUT_CONFIG['atr_period']
        
        # 动量参数
        self.momentum_period = BREAKOUT_CONFIG['momentum_period']
        
        # 风控参数
        self.stop_loss = BREAKOUT_CONFIG['stop_loss']
        self.profit_target = BREAKOUT_CONFIG['profit_target']
        self.trailing_stop = BREAKOUT_CONFIG['trailing_stop']
        
        # 仓位管理参数
        self.max_position_pct = BREAKOUT_CONFIG['max_position_pct']
        self.max_volume_pct = BREAKOUT_CONFIG['max_volume_pct']

    def calculate_signals(self, data):
        df = data.copy()
        
        # 计算价格突破指标
        df['price_high'] = df['high'].rolling(self.price_period).max()
        df['price_low'] = df['low'].rolling(self.price_period).min()
        
        # 计算成交量突破指标
        df['volume_ma'] = df['volume'].rolling(self.volume_period).mean()
        df['volume_std'] = df['volume'].rolling(self.volume_period).std()
        
        # 计算趋势指标
        df['ma_short'] = talib.EMA(df['close'], self.ma_short)
        df['ma_long'] = talib.EMA(df['close'], self.ma_long)
        df['rsi'] = talib.RSI(df['close'], timeperiod=self.rsi_period)
        
        # 计算动量指标
        df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(
            df['close'], 
            fastperiod=self.macd_fast, 
            slowperiod=self.macd_slow, 
            signalperiod=self.macd_signal
        )
        
        # 计算波动率
        df['volatility'] = df['close'].pct_change().rolling(self.volatility_period).std()
        df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=self.atr_period)
        df['atr_ratio'] = df['atr'] / df['close']
        
        # 计算趋势强度
        df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=10)
        
        # 计算价格动量
        df['momentum'] = df['close'].pct_change(self.momentum_period)
        
        return df

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        # 波动率检查
        volatility_ok = (self.min_volatility <= row['volatility'] <= self.max_volatility)
        
        # 上涨突破条件
        price_breakout_up = (row['close'] > prev_row['price_high'] * self.breakout_threshold)
        volume_breakout = (row['volume'] > row['volume_ma'] * self.volume_threshold)
        
        # 趋势确认条件
        trend_confirm = (
            row['ma_short'] > row['ma_long'] or  # 均线多头排列
            row['close'] > row['ma_short'] or  # 价格在短期均线上方
            row['macd_hist'] > 0 or  # MACD柱状图为正
            row['momentum'] > 0  # 动量为正
        )
        
        # 动量条件
        momentum_good = (
            row['rsi'] < 70 and  # RSI不过热
            row['atr_ratio'] < 0.05  # 波动率可控
        )
        
        # 下跌突破条件
        price_breakout_down = (row['close'] < prev_row['price_low'] / self.breakout_threshold)
        
        # 趋势反转条件
        trend_reverse = (
            row['ma_short'] < row['ma_long'] or
            row['close'] < row['ma_short'] or
            row['macd_hist'] < 0 or
            row['momentum'] < 0
        )
        
        if self.position <= 0 and volatility_ok:
            # 买入条件：只需满足价格突破和任意一个确认条件
            if price_breakout_up and (volume_breakout or trend_confirm) and momentum_good:
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
            
            # 趋势反转条件判断
            trend_reversal = price_breakout_down and trend_reverse
            
            if stop_loss_triggered or take_profit or trend_reversal:
                signal = 'SELL'
                if hasattr(self, 'highest_price'):
                    delattr(self, 'highest_price')
        
        return signal

    def execute_trade(self, date, price, signal, volume):
        """执行交易"""
        if signal == 'BUY' and self.position <= 0:
            # 计算可买入股数
            position_size = min(
                self.max_position_pct * self.capital / price,  # 使用配置的最大仓位比例
                volume * self.max_volume_pct  # 使用配置的最大成交量比例
            )
            
            shares = int(position_size)
            if shares > 0:
                cost = shares * price
                commission = cost * self.commission_rate
                
                if cost + commission <= self.capital:
                    self.position = shares
                    self.capital -= (cost + commission)
                    self.entry_price = price
                    self.highest_price = price
                    
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