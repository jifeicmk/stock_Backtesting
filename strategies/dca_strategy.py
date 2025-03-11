import talib
import numpy as np
from strategies.base_strategy import BaseStrategy
from utils.utils import TradeLogger

class DCAStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("定投策略", initial_capital, commission_rate)
        # 定投参数
        self.investment_period = 5  # 每5个交易日定投一次
        self.base_position = 0.1  # 基础仓位比例（10%）
        self.max_position = 0.8  # 最大仓位比例（80%）
        self.days_count = 0  # 交易日计数器
        
        # 技术指标参数
        self.ma_short = 5
        self.ma_long = 20
        self.rsi_period = 14
        self.volume_period = 10
        
        # 止损参数
        self.stop_loss = 0.1  # 总体止损线（10%）
        self.position_stop = 0.05  # 单次加仓止损线（5%）
        self._position_size = 0.0  # 用于存储当前交易的仓位大小

    def calculate_signals(self, data):
        df = data.copy()
        
        # 计算均线
        df['ma_short'] = talib.EMA(df['close'], self.ma_short)
        df['ma_long'] = talib.EMA(df['close'], self.ma_long)
        
        # 计算RSI
        df['rsi'] = talib.RSI(df['close'], timeperiod=self.rsi_period)
        
        # 计算成交量
        df['volume_ma'] = talib.SMA(df['volume'], self.volume_period)
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # 计算波动率
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(20).std()
        
        # 计算市场强度
        df['market_strength'] = ((df['close'] - df['ma_long']) / df['ma_long']) * 100
        
        return df

    def calculate_position_size(self, row):
        """计算本次加仓的仓位大小"""
        # 基础定投金额
        position_size = self.base_position
        
        # 根据RSI调整仓位
        if row['rsi'] < 30:  # RSI超卖
            position_size *= 1.5
        elif row['rsi'] > 70:  # RSI超买
            position_size *= 0.5
            
        # 根据市场强度调整仓位
        if row['market_strength'] < -10:  # 市场弱势
            position_size *= 1.3
        elif row['market_strength'] > 10:  # 市场强势
            position_size *= 0.7
            
        # 根据波动率调整仓位
        if row['volatility'] > 0.02:  # 高波动
            position_size *= 0.8
            
        # 确保不超过最大仓位
        total_position = self.position * row['close'] / self.capital
        if total_position + position_size > self.max_position:
            position_size = max(0, self.max_position - total_position)
            
        return position_size

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        self.days_count += 1
        
        # 检查是否需要定投
        if self.days_count >= self.investment_period:
            self.days_count = 0  # 重置计数器
            
            # 市场条件检查
            market_conditions = (
                row['volume_ratio'] > 0.8 and  # 成交量正常
                row['volatility'] < 0.03  # 波动率可接受
            )
            
            if market_conditions:
                # 计算加仓金额
                position_size = self.calculate_position_size(row)
                if position_size > 0:
                    self._position_size = position_size
                    signal = 'BUY'
        
        # 止损检查
        if self.position > 0:
            # 计算总体收益率
            total_profit = (row['close'] - self.entry_price) / self.entry_price
            
            # 如果总体亏损超过止损线，清仓
            if total_profit < -self.stop_loss:
                self._position_size = 1.0  # 全部卖出
                signal = 'SELL'
            # 如果单次加仓亏损超过止损线，部分止损
            elif total_profit < -self.position_stop:
                self._position_size = 0.2  # 卖出20%仓位
                signal = 'SELL'
        
        return signal

    def execute_trade(self, date, price, signal, volume):
        """执行交易"""
        if signal == 'BUY':
            # 计算可以买入的股数
            available_capital = self.capital * self._position_size
            shares = int(available_capital / price)
            
            if shares > 0:
                cost = shares * price
                commission = cost * self.commission_rate
                
                if cost + commission <= self.capital:
                    self.position += shares
                    self.capital -= (cost + commission)
                    # 更新平均成本
                    self.entry_price = (self.entry_price * (self.position - shares) + price * shares) / self.position
                    
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
            # 确定卖出数量
            shares = int(self.position * self._position_size)
            if shares > 0:
                revenue = shares * price
                commission = revenue * self.commission_rate
                
                self.capital += (revenue - commission)
                self.position -= shares
                
                # 如果全部卖出，重置入场价格
                if self.position == 0:
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