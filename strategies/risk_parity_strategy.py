import talib
import numpy as np
import pandas as pd
from strategies.base_strategy import BaseStrategy
from utils.utils import TradeLogger

class RiskParityStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("风险平价策略", initial_capital, commission_rate)
        # 参数设置
        self.volatility_period = 20
        self.ma_period = 20
        self.risk_target = 0.15  # 目标年化波动率
        self.max_leverage = 2.0  # 最大杠杆倍数
        self.min_position = 0.1  # 最小仓位比例
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
        
        # 计算波动率
        df['volatility'] = talib.STDDEV(df['close'], timeperiod=self.volatility_period) / df['close']
        df['annualized_vol'] = df['volatility'] * np.sqrt(252)  # 年化波动率
        
        # 计算动态风险调整因子
        df['risk_adjustment'] = self.risk_target / df['annualized_vol']
        df['risk_adjustment'] = df['risk_adjustment'].clip(upper=self.max_leverage)
        
        # 计算趋势信号
        df['trend'] = np.where(df['close'] > df['ma'], 1, -1)
        
        # 计算RSI
        df['rsi'] = talib.RSI(df['close'], timeperiod=14)
        
        # 计算ATR
        df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        
        # 计算动态止损水平
        df['stop_level'] = df['close'] - 2 * df['atr']
        
        return df

    def _calculate_position_size(self, row):
        """计算目标仓位大小"""
        risk_adj = row['risk_adjustment']
        trend = row['trend']
        rsi = row['rsi']
        
        # 基于RSI调整仓位
        rsi_factor = 1.0
        if rsi > 70:
            rsi_factor = 0.5
        elif rsi < 30:
            rsi_factor = 1.5
        
        # 计算目标仓位
        target_position = risk_adj * trend * rsi_factor
        
        # 限制仓位范围
        target_position = np.clip(target_position, -self.max_leverage, self.max_leverage)
        
        return target_position

    def generate_signal(self, row, prev_row):
        """生成交易信号"""
        # 检查是否有足够的数据来计算指标
        if pd.isna(row['ma']) or pd.isna(row['volatility']):
            return 'HOLD'
            
        current_price = row['close']
        target_position = self._calculate_position_size(row)
        
        # 检查是否需要止损或止盈
        if self.position > 0:
            profit_pct = (current_price - self.entry_price) / self.entry_price
            if profit_pct <= -self.stop_loss or profit_pct >= self.profit_target:
                return 'SELL'
            # 检查动态止损
            if current_price < row['stop_level']:
                return 'SELL'
        
        # 生成交易信号
        if target_position > self.min_position and self.position <= 0:
            return 'BUY'
        elif target_position < -self.min_position or \
             (self.position > 0 and target_position < self.min_position):
            return 'SELL'
        
        return 'HOLD'

    def execute_trade(self, date, price, signal, volume):
        """执行交易"""
        if signal == 'BUY' and self.position <= 0:
            # 计算可买入股数
            target_position = self._calculate_position_size(self._current_row)
            target_value = self.capital * abs(target_position)
            max_shares = int(target_value / (price * (1 + self.commission_rate)))
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