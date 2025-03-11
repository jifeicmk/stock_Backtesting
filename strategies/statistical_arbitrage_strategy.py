import talib
import numpy as np
import pandas as pd
from strategies.base_strategy import BaseStrategy
from utils.utils import TradeLogger

class StatisticalArbitrageStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("统计套利策略", initial_capital, commission_rate)
        # 参数设置
        self.lookback_period = 60  # 回看期
        self.zscore_threshold = 2.0  # z-score阈值
        self.ma_period = 20
        self.std_period = 20
        self.correlation_period = 60
        self.stop_loss = 0.03
        self.profit_target = 0.05
        self._current_row = None

    def set_current_row(self, row):
        """设置当前行数据"""
        self._current_row = row

    def calculate_signals(self, data):
        df = data.copy()
        
        # 计算移动平均和标准差
        df['ma'] = talib.SMA(df['close'], timeperiod=self.ma_period)
        df['std'] = talib.STDDEV(df['close'], timeperiod=self.std_period)
        
        # 计算z-score
        df['zscore'] = (df['close'] - df['ma']) / df['std']
        
        # 计算价格动量
        df['momentum'] = df['close'].pct_change(self.lookback_period)
        
        # 计算波动率
        df['volatility'] = df['std'] / df['ma']
        
        # 计算自相关系数
        df['autocorr'] = df['close'].rolling(window=self.correlation_period).apply(
            lambda x: x.autocorr(), raw=False)
        
        # 计算历史分位数
        df['percentile'] = df['close'].rolling(window=self.lookback_period).apply(
            lambda x: pd.Series(x).rank().iloc[-1] / len(x))
        
        return df

    def generate_signal(self, row, prev_row):
        """生成交易信号"""
        # 检查是否有足够的数据来计算指标
        if pd.isna(row['ma']) or pd.isna(row['zscore']):
            return 'HOLD'
            
        current_price = row['close']
        zscore = row['zscore']
        momentum = row['momentum']
        volatility = row['volatility']
        autocorr = row['autocorr']
        percentile = row['percentile']
        
        # 检查是否需要止损或止盈
        if self.position > 0:
            profit_pct = (current_price - self.entry_price) / self.entry_price
            if profit_pct <= -self.stop_loss or profit_pct >= self.profit_target:
                return 'SELL'
        
        # 生成交易信号
        if zscore < -self.zscore_threshold and \
           (momentum < 0 or volatility < row['volatility'].mean()) and \
           (autocorr > 0 or percentile < 0.3):  # 放宽条件
            return 'BUY'
        elif zscore > self.zscore_threshold or \
             (momentum > 0 and percentile > 0.7):  # 放宽条件
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