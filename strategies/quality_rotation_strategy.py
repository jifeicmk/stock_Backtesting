import talib
import numpy as np
import pandas as pd
from strategies.base_strategy import BaseStrategy
from utils.utils import TradeLogger

class QualityRotationStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("质量轮动策略", initial_capital, commission_rate)
        # 参数设置
        self.ma_period = 20
        self.momentum_period = 60
        self.volatility_period = 20
        self.quality_threshold = 0.7  # 质量分数阈值
        self.momentum_threshold = 0.02  # 动量阈值
        self.stop_loss = 0.03
        self.profit_target = 0.05
        self._current_row = None

    def set_current_row(self, row):
        """设置当前行数据"""
        self._current_row = row

    def calculate_signals(self, data):
        df = data.copy()
        
        # 计算移动平均
        df['ma'] = talib.SMA(df['close'], timeperiod=self.ma_period)
        
        # 计算动量指标
        df['momentum'] = df['close'].pct_change(self.momentum_period)
        df['momentum_ma'] = talib.SMA(df['momentum'], timeperiod=self.ma_period)
        
        # 计算波动率
        df['volatility'] = talib.STDDEV(df['close'], timeperiod=self.volatility_period) / df['ma']
        
        # 计算ROC（变动率）
        df['roc'] = talib.ROC(df['close'], timeperiod=self.momentum_period)
        
        # 计算RSI
        df['rsi'] = talib.RSI(df['close'], timeperiod=14)
        
        # 计算质量分数
        df['quality_score'] = self._calculate_quality_score(df)
        
        # 计算趋势强度
        df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
        
        return df

    def _calculate_quality_score(self, df):
        """计算质量分数"""
        # 1. 趋势质量
        trend_quality = (df['close'] > df['ma']).astype(float)
        
        # 2. 动量质量
        momentum_quality = (df['momentum'] > 0).astype(float)
        
        # 3. 波动率质量（波动率越低越好）
        volatility_quality = 1 - (df['volatility'] / df['volatility'].rolling(window=self.volatility_period).max())
        
        # 4. RSI质量（避免过度超买超卖）
        rsi_quality = 1 - abs(df['rsi'] - 50) / 50
        
        # 综合质量分数
        quality_score = (trend_quality + momentum_quality + volatility_quality + rsi_quality) / 4
        
        return quality_score

    def generate_signal(self, row, prev_row):
        """生成交易信号"""
        # 检查是否有足够的数据来计算指标
        if pd.isna(row['ma']) or pd.isna(row['quality_score']):
            return 'HOLD'
            
        current_price = row['close']
        quality_score = row['quality_score']
        momentum = row['momentum']
        adx = row['adx']
        
        # 检查是否需要止损或止盈
        if self.position > 0:
            profit_pct = (current_price - self.entry_price) / self.entry_price
            if profit_pct <= -self.stop_loss or profit_pct >= self.profit_target:
                return 'SELL'
        
        # 生成交易信号
        if quality_score > self.quality_threshold and \
           momentum > self.momentum_threshold and \
           adx > 25 and \
           current_price > row['ma']:
            return 'BUY'
        elif quality_score < self.quality_threshold or \
             momentum < -self.momentum_threshold or \
             current_price < row['ma']:
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