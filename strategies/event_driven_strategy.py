import talib
import numpy as np
import pandas as pd
from strategies.base_strategy import BaseStrategy
from utils.utils import TradeLogger

class EventDrivenStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("事件驱动策略", initial_capital, commission_rate)
        # 参数设置
        self.volume_surge_threshold = 3.0  # 成交量突增阈值
        self.price_change_threshold = 0.05  # 价格变动阈值
        self.ma_period = 20
        self.volatility_period = 20
        self.rsi_period = 14
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.stop_loss = 0.03
        self.profit_target = 0.05
        self._current_row = None

    def set_current_row(self, row):
        """设置当前行数据"""
        self._current_row = row

    def calculate_signals(self, data):
        df = data.copy()
        
        # 计算价格和成交量的移动平均
        df['volume_ma'] = talib.SMA(df['volume'], timeperiod=self.ma_period)
        df['price_ma'] = talib.SMA(df['close'], timeperiod=self.ma_period)
        
        # 计算成交量比率和价格变动
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        df['price_change'] = df['close'].pct_change()
        
        # 计算波动率
        df['volatility'] = talib.STDDEV(df['close'], timeperiod=self.volatility_period) / df['price_ma']
        
        # 计算RSI
        df['rsi'] = talib.RSI(df['close'], timeperiod=self.rsi_period)
        
        # 计算MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(
            df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        
        # 计算布林带
        df['bb_middle'], df['bb_upper'], df['bb_lower'] = talib.BBANDS(
            df['close'], timeperiod=20, nbdevup=2, nbdevdn=2)
        
        # 识别价格突破
        df['price_breakout'] = (df['close'] > df['bb_upper']) | (df['close'] < df['bb_lower'])
        
        return df

    def generate_signal(self, row, prev_row):
        """生成交易信号"""
        # 检查是否有足够的数据来计算指标
        if pd.isna(row['volume_ma']) or pd.isna(row['price_ma']):
            return 'HOLD'
            
        current_price = row['close']
        volume_ratio = row['volume_ratio']
        price_change = row['price_change']
        rsi = row['rsi']
        volatility = row['volatility']
        price_breakout = row['price_breakout']
        
        # 检查是否需要止损或止盈
        if self.position > 0:
            profit_pct = (current_price - self.entry_price) / self.entry_price
            if profit_pct <= -self.stop_loss or profit_pct >= self.profit_target:
                return 'SELL'
        
        # 生成交易信号
        # 1. 成交量突增事件
        volume_surge = volume_ratio > self.volume_surge_threshold
        
        # 2. 价格突破事件
        price_surge = abs(price_change) > self.price_change_threshold
        
        # 3. RSI超买超卖事件
        rsi_signal = (rsi < self.rsi_oversold) or (rsi > self.rsi_overbought)
        
        # 综合判断交易信号
        if (volume_surge or price_surge) and price_change > 0 and \
           rsi < self.rsi_overbought:  # 放宽条件
            return 'BUY'
        elif ((volume_surge and price_change < 0) or \
             rsi > self.rsi_overbought or \
             (self.position > 0 and volatility > row['volatility'].mean() * 1.2)):  # 降低波动率阈值
            return 'SELL'
        
        return 'HOLD'

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