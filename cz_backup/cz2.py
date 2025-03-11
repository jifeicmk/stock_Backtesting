import baostock as bs
import pandas as pd
import numpy as np
import talib
from datetime import datetime
import argparse

class BaseStrategy:
    def __init__(self, name, initial_capital, commission_rate):
        self.name = name
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = 0
        self.trades = []
        self.position_size = 0.7  # 仓位比例
        self.commission_rate = commission_rate  # 手续费率
        self.entry_price = 0  # 入场价格

    def _print_trade(self, trade):
        """打印交易信息"""
        formatted_price = f"¥{trade['price']:.2f}"
        formatted_amount = f"¥{trade['amount']:,.2f}"
        formatted_capital = f"¥{trade['capital']:,.2f}"
        
        RED = '\033[91m'
        GREEN = '\033[92m'
        BLUE = '\033[94m'
        YELLOW = '\033[93m'
        ENDC = '\033[0m'
        
        color = GREEN if trade['type'] == '买入' else RED
        
        trade_info = (
            f"{BLUE}{trade['date']}{ENDC} | "
            f"{YELLOW}{self.name:10}{ENDC} | "
            f"{color}{trade['type']:4}{ENDC} | "
            f"价格: {formatted_price:>10} | "
            f"数量: {trade['shares']:>8,d}股 | "
            f"金额: {formatted_amount:>12} | "
            f"资金: {formatted_capital:>12}"
        )
        print(trade_info)
        
        if self.position != 0:
            position_info = " " * 24 + f"{YELLOW}当前持仓: {self.position:,d}股{ENDC}"
            print(position_info)

    def execute_trade(self, date, price, signal, volume):
        """执行交易"""
        commission = 0
        available_capital = self.capital if self.position == 0 else self.capital + self.position * price
        max_position = int((available_capital * self.position_size) / price)
        
        if signal == 'BUY' and self.position == 0 and max_position > 0:
            shares = max_position
            cost = shares * price
            commission = cost * self.commission_rate
            
            if cost + commission <= self.capital:
                self.capital -= (cost + commission)
                self.position = shares
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
                self._print_trade(trade)
            else:
                print(f"资金不足：需要{cost + commission:.2f}，当前资金{self.capital:.2f}")
        
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
            self._print_trade(trade)

                
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
            self._print_trade(trade)

    def print_performance(self):
        """打印策略表现"""
        if not self.trades:
            print(f"\n{self.name}: 没有交易记录")
            return
            
        total_trades = len([t for t in self.trades if t['type'] == '卖出'])  # 只统计卖出交易
        winning_trades = 0
        total_profit = 0
        
        # 遍历所有交易对（买入-卖出）计算盈亏
        buy_trade = None
        for trade in self.trades:
            if trade['type'] == '买入':
                buy_trade = trade
            elif trade['type'] == '卖出' and buy_trade is not None:
                # 计算这次交易的盈亏（考虑手续费）
                buy_cost = buy_trade['amount'] + buy_trade['commission']
                sell_revenue = trade['amount'] - trade['commission']
                trade_profit = sell_revenue - buy_cost
                
                if trade_profit > 0:
                    winning_trades += 1
                total_profit += trade_profit
                buy_trade = None
        
        profit = self.capital - self.initial_capital
        returns = profit / self.initial_capital * 100
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        
        RED = '\033[91m'
        GREEN = '\033[92m'
        BLUE = '\033[94m'
        YELLOW = '\033[93m'
        ENDC = '\033[0m'
        
        print(f"\n{YELLOW}{self.name} 策略表现报告{ENDC}")
        print("-"*80)
        
        performance_info = (
            f"初始资金: ¥{self.initial_capital:,.2f} | "
            f"最终资金: ¥{self.capital:,.2f} | "
            f"总收益: {GREEN if profit >= 0 else RED}¥{profit:,.2f}{ENDC} | "
            f"收益率: {GREEN if returns >= 0 else RED}{returns:.2f}%{ENDC} | "
            f"交易次数: {total_trades} | "
            f"胜率: {GREEN if win_rate > 50 else RED}{win_rate:.1f}%{ENDC}"
        )
        print(performance_info)
        
        # 打印详细的交易统计
        print(f"总交易对数: {total_trades} | "
              f"盈利交易: {winning_trades} | "
              f"亏损交易: {total_trades - winning_trades} | "
              f"平均每笔盈亏: {total_profit/total_trades:,.2f}" if total_trades > 0 else "暂无交易")
        
        if self.position != 0:
            print(f"{YELLOW}警告: 还有未平仓位置 {self.position:,d}股{ENDC}")

    def calculate_signals(self, data):
        """计算整个数据集的信号"""
        df = data.copy()
        df['signal'] = 0
        
        # 初始化第一个信号
        df.iloc[0, df.columns.get_loc('signal')] = 0
        
        # 逐行计算信号
        for i in range(1, len(df)):
            signal = self.generate_signal(df.iloc[i], df.iloc[i-1])
            df.iloc[i, df.columns.get_loc('signal')] = signal
            
        return df

    def generate_signal(self, current_data, prev_data):
        """生成单个交易信号，子类必须实现这个方法"""
        return 0  # 默认返回持仓不变

class EnhancedStrategy(BaseStrategy):
    def __init__(self, initial_capital=1000000):
        super().__init__("增强策略", initial_capital)
        
    def calculate_signals(self, data):
        df = data.copy()
        
        # 计算技术指标
        # 移动平均线
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        
        # MACD
        df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['EMA12'] - df['EMA26']
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 成交量指标
        df['Volume_MA'] = df['volume'].rolling(window=20).mean()
        
        # 生成交易信号
        df['signal'] = 0
        
        # 简化买入条件
        buy_condition = (
            (df['MA5'] > df['MA10']) &  # 短期均线上穿中期均线
            (df['MACD'] > df['Signal']) &  # MACD金叉
            (df['RSI'] < 65)  # RSI未严重超买
        )
        
        # 简化卖出条件
        sell_condition = (
            (df['MA5'] < df['MA10']) |  # 短期均线下穿中期均线
            (df['MACD'] < df['Signal']) |  # MACD死叉
            (df['RSI'] > 75)  # RSI超买
        )
        
        # 设置信号
        df.loc[buy_condition, 'signal'] = 1
        df.loc[sell_condition, 'signal'] = -1
        
        # 简化信号过滤
        min_holding_period = 3  # 减少最小持仓周期
        last_signal_idx = None
        
        for i in range(len(df)):
            if df.iloc[i]['signal'] != 0:
                if last_signal_idx is None or (i - last_signal_idx) >= min_holding_period:
                    last_signal_idx = i
                else:
                    df.iloc[i, df.columns.get_loc('signal')] = 0
        
        return df

class MACDStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("MACD策略", initial_capital, commission_rate)
        self.fast = 12
        self.slow = 26
        self.signal = 9
        self.stop_loss = 0.03

    def calculate_signals(self, data):
        data['macd'], data['macd_signal'], data['macd_hist'] = talib.MACD(
            data['close'], fastperiod=self.fast, slowperiod=self.slow, signalperiod=self.signal)
        return data

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        if prev_row['macd_hist'] < 0 and row['macd_hist'] > 0:
            signal = 'BUY'
        elif prev_row['macd_hist'] > 0 and row['macd_hist'] < 0:
            signal = 'SELL'
            
        if self.position > 0 and row['close'] < self.entry_price * (1 - self.stop_loss):
            signal = 'SELL'
            
        return signal

class KDJStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("KDJ策略", initial_capital, commission_rate)
        self.k_period = 9
        self.stop_loss = 0.03

    def calculate_signals(self, data):
        high_list = data['high'].rolling(self.k_period).max()
        low_list = data['low'].rolling(self.k_period).min()
        rsv = (data['close'] - low_list) / (high_list - low_list) * 100
        
        data['k'] = rsv.rolling(3).mean()
        data['d'] = data['k'].rolling(3).mean()
        data['j'] = 3 * data['k'] - 2 * data['d']
        return data

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        if prev_row['k'] < prev_row['d'] and row['k'] > row['d'] and row['k'] < 30:
            signal = 'BUY'
        elif prev_row['k'] > prev_row['d'] and row['k'] < row['d'] and row['k'] > 70:
            signal = 'SELL'
            
        if self.position > 0 and row['close'] < self.entry_price * (1 - self.stop_loss):
            signal = 'SELL'
            
        return signal

class BollingerStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("布林带策略", initial_capital, commission_rate)
        self.period = 20
        self.std_dev = 2
        self.stop_loss = 0.03
        self.profit_target = 0.05

    def calculate_signals(self, data):
        # 计算布林带
        data['middle'] = talib.SMA(data['close'], self.period)
        std = talib.STDDEV(data['close'], self.period)
        data['upper'] = data['middle'] + (std * self.std_dev)
        data['lower'] = data['middle'] - (std * self.std_dev)
        
        # 计算额外指标
        data['rsi'] = talib.RSI(data['close'], timeperiod=14)
        data['volume_ma'] = talib.SMA(data['volume'], 20)
        return data

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        # 买入条件：
        # 1. 价格触及下轨
        # 2. RSI < 30 (超卖)
        # 3. 成交量大于20日均量
        if (row['close'] <= row['lower'] and 
            row['rsi'] < 30 and 
            row['volume'] > row['volume_ma'] * 1.2):
            signal = 'BUY'
            
        # 卖出条件：
        # 1. 价格触及上轨
        # 2. RSI > 70 (超买)
        # 3. 成交量放大
        elif (row['close'] >= row['upper'] and 
              row['rsi'] > 70 and 
              row['volume'] > row['volume_ma'] * 1.5):
            signal = 'SELL'
            
        # 止损止盈
        if self.position > 0:
            if row['close'] < self.entry_price * (1 - self.stop_loss):
                signal = 'SELL'
            elif row['close'] > self.entry_price * (1 + self.profit_target):
                signal = 'SELL'
                
        return signal

class DualMAVolumeStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("双均线量策略", initial_capital, commission_rate)
        self.fast_period = 5
        self.slow_period = 20
        self.volume_period = 20
        self.stop_loss = 0.03
        self.profit_target = 0.05

    def calculate_signals(self, data):
        # 计算快慢均线
        data['fast_ma'] = talib.EMA(data['close'], self.fast_period)
        data['slow_ma'] = talib.EMA(data['close'], self.slow_period)
        
        # 计算成交量指标
        data['volume_ma'] = talib.SMA(data['volume'], self.volume_period)
        data['volume_ratio'] = data['volume'] / data['volume_ma']
        
        # 计算趋势强度
        data['adx'] = talib.ADX(data['high'], data['low'], data['close'], timeperiod=14)
        return data

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        # 买入条件：
        # 1. 快线上穿慢线
        # 2. 成交量是均量的1.5倍以上
        # 3. ADX > 25 (趋势强)
        if (prev_row['fast_ma'] <= prev_row['slow_ma'] and 
            row['fast_ma'] > row['slow_ma'] and 
            row['volume_ratio'] > 1.5 and
            row['adx'] > 25):
            signal = 'BUY'
            
        # 卖出条件：
        # 1. 快线下穿慢线
        # 2. 成交量放大
        # 3. ADX > 20
        elif (prev_row['fast_ma'] >= prev_row['slow_ma'] and 
              row['fast_ma'] < row['slow_ma'] and 
              row['volume_ratio'] > 1.2 and
              row['adx'] > 20):
            signal = 'SELL'
            
        # 止损止盈
        if self.position > 0:
            if row['close'] < self.entry_price * (1 - self.stop_loss):
                signal = 'SELL'
            elif row['close'] > self.entry_price * (1 + self.profit_target):
                signal = 'SELL'
                
        return signal

class MeanReversionStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("均值回归策略", initial_capital, commission_rate)
        self.lookback = 20
        self.std_dev = 2
        self.stop_loss = 0.03
        self.profit_target = 0.05

    def calculate_signals(self, data):
        # 计算移动平均和标准差
        data['ma'] = talib.SMA(data['close'], self.lookback)
        data['std'] = talib.STDDEV(data['close'], self.lookback)
        data['upper'] = data['ma'] + (data['std'] * self.std_dev)
        data['lower'] = data['ma'] - (data['std'] * self.std_dev)
        
        # 计算z-score
        data['z_score'] = (data['close'] - data['ma']) / data['std']
        data['rsi'] = talib.RSI(data['close'], timeperiod=14)
        return data

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        # 当价格显著偏离均值且RSI显示超买超卖时交易
        if row['z_score'] < -self.std_dev and row['rsi'] < 30:
            signal = 'BUY'
        elif row['z_score'] > self.std_dev and row['rsi'] > 70:
            signal = 'SELL'
            
        # 止损止盈
        if self.position > 0:
            if row['close'] < self.entry_price * (1 - self.stop_loss):
                signal = 'SELL'
            elif row['close'] > self.entry_price * (1 + self.profit_target):
                signal = 'SELL'
                
        return signal

class TrendFollowingStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("趋势跟踪策略", initial_capital, commission_rate)
        self.short_period = 20
        self.long_period = 50
        self.atr_period = 14
        self.stop_multiple = 2

    def calculate_signals(self, data):
        # 计算多个时间周期的趋势指标
        data['ema_short'] = talib.EMA(data['close'], self.short_period)
        data['ema_long'] = talib.EMA(data['close'], self.long_period)
        
        # 计算ATR用于止损
        data['atr'] = talib.ATR(data['high'], data['low'], data['close'], self.atr_period)
        
        # 计算MACD
        data['macd'], data['signal'], data['hist'] = talib.MACD(data['close'])
        
        # 计算趋势强度
        data['adx'] = talib.ADX(data['high'], data['low'], data['close'], timeperiod=14)
        return data

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        # 趋势确认条件
        trend_up = (row['ema_short'] > row['ema_long'] and 
                   row['hist'] > 0 and 
                   row['adx'] > 25)
        
        trend_down = (row['ema_short'] < row['ema_long'] and 
                     row['hist'] < 0 and 
                     row['adx'] > 25)
        
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

class VolumeBasedStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("量价分析策略", initial_capital, commission_rate)
        self.volume_ma_period = 20
        self.price_ma_period = 10
        self.volume_threshold = 1.5
        self.stop_loss = 0.03

    def calculate_signals(self, data):
        # 计算成交量和价格的移动平均
        data['volume_ma'] = talib.SMA(data['volume'], self.volume_ma_period)
        data['price_ma'] = talib.SMA(data['close'], self.price_ma_period)
        
        # 计算量比
        data['volume_ratio'] = data['volume'] / data['volume_ma']
        
        # 计算价格动量
        data['momentum'] = talib.MOM(data['close'], timeperiod=10)
        
        # 计算OBV（能量潮指标）
        data['obv'] = talib.OBV(data['close'], data['volume'])
        data['obv_ma'] = talib.SMA(data['obv'], 20)
        
        return data

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        # 放量上涨买入条件
        volume_surge = row['volume_ratio'] > self.volume_threshold
        price_up = row['close'] > row['price_ma']
        obv_confirm = row['obv'] > row['obv_ma']
        
        if volume_surge and price_up and obv_confirm:
            signal = 'BUY'
        
        # 放量下跌卖出条件
        elif (volume_surge and 
              row['close'] < row['price_ma'] and 
              row['momentum'] < 0):
            signal = 'SELL'
            
        # 止损
        if self.position > 0:
            if row['close'] < self.entry_price * (1 - self.stop_loss):
                signal = 'SELL'
            
        return signal

class StatisticalArbitrageStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("统计套利策略", initial_capital, commission_rate)
        self.lookback = 30
        self.entry_threshold = 2.0
        self.exit_threshold = 0.5
        self.stop_loss = 0.03

    def calculate_signals(self, data):
        # 计算价格相对强弱
        data['returns'] = data['close'].pct_change()
        data['rolling_mean'] = data['returns'].rolling(self.lookback).mean()
        data['rolling_std'] = data['returns'].rolling(self.lookback).std()
        data['zscore'] = (data['returns'] - data['rolling_mean']) / data['rolling_std']
        
        # 计算波动率
        data['volatility'] = data['rolling_std'] * np.sqrt(252)
        
        # 计算动量指标
        data['momentum'] = data['close'].pct_change(5)
        return data

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        # 基于z-score的交易信号
        if row['zscore'] < -self.entry_threshold and row['momentum'] < 0:
            signal = 'BUY'
        elif row['zscore'] > self.entry_threshold and row['momentum'] > 0:
            signal = 'SELL'
            
        # 止损和平仓
        if self.position > 0:
            if row['close'] < self.entry_price * (1 - self.stop_loss):
                signal = 'SELL'
            elif abs(row['zscore']) < self.exit_threshold:
                signal = 'SELL'
                
        return signal

class EventDrivenStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("事件驱动策略", initial_capital, commission_rate)
        self.volume_threshold = 3.0
        self.price_threshold = 0.05
        self.stop_loss = 0.03

    def calculate_signals(self, data):
        # 计算成交量异常
        data['volume_ma'] = talib.SMA(data['volume'], 20)
        data['volume_ratio'] = data['volume'] / data['volume_ma']
        
        # 计算价格变动
        data['price_change'] = data['close'].pct_change()
        data['price_ma'] = talib.SMA(data['close'], 20)
        
        # 计算波动率
        data['volatility'] = talib.STDDEV(data['close'], timeperiod=20)
        return data

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        # 成交量突增且价格上涨
        volume_surge = row['volume_ratio'] > self.volume_threshold
        price_up = row['price_change'] > self.price_threshold
        trend_confirm = row['close'] > row['price_ma']
        
        if volume_surge and price_up and trend_confirm:
            signal = 'BUY'
        elif volume_surge and row['price_change'] < -self.price_threshold:
            signal = 'SELL'
            
        # 止损
        if self.position > 0:
            if row['close'] < self.entry_price * (1 - self.stop_loss):
                signal = 'SELL'
                
        return signal

class QualityRotationStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("质量轮动策略", initial_capital, commission_rate)
        self.rsi_period = 14
        self.momentum_period = 20
        self.stop_loss = 0.03

    def calculate_signals(self, data):
        # 计算技术质量指标
        data['rsi'] = talib.RSI(data['close'], timeperiod=self.rsi_period)
        data['momentum'] = data['close'].pct_change(self.momentum_period)
        data['volatility'] = talib.STDDEV(data['close'], timeperiod=20)
        
        # 计算趋势指标
        data['ma_short'] = talib.SMA(data['close'], 5)
        data['ma_long'] = talib.SMA(data['close'], 20)
        data['trend'] = data['ma_short'] - data['ma_long']
        return data

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        # 基于多个技术指标的质量评分
        quality_good = (row['rsi'] > 50 and 
                       row['momentum'] > 0 and 
                       row['trend'] > 0)
        
        quality_bad = (row['rsi'] < 50 and 
                      row['momentum'] < 0 and 
                      row['trend'] < 0)
        
        if quality_good and self.position <= 0:
            signal = 'BUY'
        elif quality_bad and self.position > 0:
            signal = 'SELL'
            
        # 止损
        if self.position > 0:
            if row['close'] < self.entry_price * (1 - self.stop_loss):
                signal = 'SELL'
                
        return signal

class RiskParityStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("风险平价策略", initial_capital, commission_rate)
        self.volatility_window = 20
        self.risk_threshold = 0.02
        self.stop_loss = 0.03

    def calculate_signals(self, data):
        # 计算波动率指标
        data['volatility'] = talib.STDDEV(data['close'].pct_change(), timeperiod=self.volatility_window)
        data['volatility_ma'] = talib.SMA(data['volatility'], self.volatility_window)
        
        # 计算趋势指标
        data['ma_short'] = talib.EMA(data['close'], 10)
        data['ma_long'] = talib.EMA(data['close'], 30)
        
        # 计算动量
        data['momentum'] = talib.MOM(data['close'], timeperiod=10)
        return data

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        # 基于风险调整的交易信号
        low_risk = row['volatility'] < row['volatility_ma']
        trend_up = row['ma_short'] > row['ma_long']
        
        if low_risk and trend_up and row['momentum'] > 0:
            signal = 'BUY'
        elif (row['volatility'] > row['volatility_ma'] * 1.5 or 
              row['ma_short'] < row['ma_long']):
            signal = 'SELL'
            
        # 止损
        if self.position > 0:
            if row['close'] < self.entry_price * (1 - self.stop_loss):
                signal = 'SELL'
                
        return signal

class EnhancedHybridStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("增强混合策略", initial_capital, commission_rate)
        # 参数设置
        self.short_period = 5
        self.medium_period = 10
        self.long_period = 20
        self.volume_ma_period = 20
        self.atr_period = 14
        self.rsi_period = 14
        self.min_holding_days = 3
        self.last_signal_date = None
        
        # 动态止损参数
        self.initial_stop_loss = 0.02
        self.trailing_stop = 0.03
        self.max_profit = 0
        
        # 仓位管理参数
        self.max_position_size = 0.8
        self.min_position_size = 0.2
        self.position_step = 0.1
        
        # 当前行数据
        self._current_row = None

    def set_current_row(self, row):
        """设置当前行数据"""
        self._current_row = row

    def calculate_signals(self, data):
        df = data.copy()
        
        # 1. 趋势指标
        df['ma_short'] = talib.EMA(df['close'], self.short_period)
        df['ma_medium'] = talib.EMA(df['close'], self.medium_period)
        df['ma_long'] = talib.EMA(df['close'], self.long_period)
        
        # 2. MACD指标
        df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(
            df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        
        # 3. RSI指标
        df['rsi'] = talib.RSI(df['close'], timeperiod=self.rsi_period)
        
        # 4. 布林带
        df['bb_middle'], df['bb_upper'], df['bb_lower'] = talib.BBANDS(
            df['close'], timeperiod=20, nbdevup=2, nbdevdn=2)
        
        # 5. ATR和波动率
        df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=self.atr_period)
        df['volatility'] = df['atr'] / df['close']
        
        # 6. 成交量分析
        df['volume_ma'] = talib.SMA(df['volume'], self.volume_ma_period)
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # 7. 趋势强度
        df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
        
        # 8. 动量指标
        df['momentum'] = talib.MOM(df['close'], timeperiod=10)
        
        return df

    def calculate_position_size(self, row):
        """动态计算仓位大小"""
        # 基础仓位从最小值开始
        position_size = self.min_position_size
        
        # 根据趋势强度增加仓位
        if row['adx'] > 25:
            position_size += self.position_step
        if row['adx'] > 35:
            position_size += self.position_step
            
        # 根据RSI调整仓位
        if 40 <= row['rsi'] <= 60:
            position_size += self.position_step
            
        # 根据波动率调整仓位
        if row['volatility'] < 0.02:
            position_size += self.position_step
            
        # 确保仓位在允许范围内
        return min(max(position_size, self.min_position_size), self.max_position_size)

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        # 计算综合得分
        score = 0
        
        # 1. 趋势得分
        if row['ma_short'] > row['ma_medium'] > row['ma_long']:
            score += 2
        elif row['ma_short'] < row['ma_medium'] < row['ma_long']:
            score -= 2
            
        # 2. MACD得分
        if row['macd_hist'] > 0 and prev_row['macd_hist'] <= 0:
            score += 1.5
        elif row['macd_hist'] < 0 and prev_row['macd_hist'] >= 0:
            score -= 1.5
            
        # 3. RSI得分
        if row['rsi'] < 30:
            score += 1
        elif row['rsi'] > 70:
            score -= 1
            
        # 4. 布林带得分
        if row['close'] < row['bb_lower']:
            score += 1
        elif row['close'] > row['bb_upper']:
            score -= 1
            
        # 5. 成交量得分
        if row['volume_ratio'] > 1.5 and row['close'] > prev_row['close']:
            score += 1
        elif row['volume_ratio'] > 1.5 and row['close'] < prev_row['close']:
            score -= 1
            
        # 6. 趋势强度确认
        if row['adx'] > 25:
            score = score * 1.2
            
        # 生成交易信号
        if score >= 3 and self.position <= 0:
            signal = 'BUY'
        elif score <= -3 and self.position > 0:
            signal = 'SELL'
            
        # 动态止损止盈
        if self.position > 0:
            # 更新最大利润
            current_profit = (row['close'] - self.entry_price) / self.entry_price
            self.max_profit = max(self.max_profit, current_profit)
            
            # 止损条件
            stop_loss = max(self.initial_stop_loss, 
                          self.max_profit - self.trailing_stop)
            
            if current_profit < -self.initial_stop_loss or \
               (self.max_profit > self.trailing_stop and \
                current_profit < self.max_profit - self.trailing_stop):
                signal = 'SELL'
                self.max_profit = 0
        
        return signal

    def execute_trade(self, date, price, signal, volume):
        """重写执行交易方法，加入动态仓位管理"""
        if signal == 'BUY' and self.position <= 0:
            position_size = self.calculate_position_size(self._current_row)
            available_capital = self.capital
            max_shares = int((available_capital * position_size) / price)
            shares = min(max_shares, int(volume * 0.1))
            
            if shares > 0:
                cost = shares * price
                commission = cost * self.commission_rate
                
                if cost + commission <= self.capital:
                    self.position = shares
                    self.capital -= (cost + commission)
                    self.entry_price = price
                    self.max_profit = 0
                    
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
                    self._print_trade(trade)
                    
        elif signal == 'SELL' and self.position > 0:
            shares = self.position
            revenue = shares * price
            commission = revenue * self.commission_rate
            
            self.capital += (revenue - commission)
            self.position = 0
            self.entry_price = 0
            self.max_profit = 0
            
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
            self._print_trade(trade)

def run_strategy(strategy, start_date, end_date, data=None):
    if data is None:
        rs = bs.query_history_k_data_plus("sh.000001",
            "date,code,open,high,low,close,volume,amount",
            start_date=start_date,
            end_date=end_date,
            frequency="d")
        
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        data = pd.DataFrame(data_list, columns=rs.fields)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            data[col] = data[col].astype(float)
    
    df = strategy.calculate_signals(data.copy())
    
    for i in range(1, len(df)):
        date = df['date'].iloc[i]
        price = df['close'].iloc[i]
        volume = df['volume'].iloc[i]
        
        # 判断是否是最后一个交易日
        is_last_day = (i == len(df) - 1)
        
        # 设置当前行数据（用于增强混合策略）
        if hasattr(strategy, 'set_current_row'):
            strategy.set_current_row(df.iloc[i])
        
        signal = strategy.generate_signal(df.iloc[i], df.iloc[i-1])
        
        # 如果是最后一个交易日且还有持仓，强制平仓
        if is_last_day and strategy.position > 0:
            signal = 'SELL'
            print(f"\n{strategy.name} 回测结束，强制平仓")
        
        if signal != 'HOLD':
            strategy.execute_trade(date, price, signal, volume)

def export_to_excel(strategies, stock_code, stock_name, start_date, end_date, data):
    """导出回测结果到Excel"""
    simple_code = stock_code.split('.')[1]
    current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"回测报告_{simple_code}_{stock_name}_{current_time}.xlsx"
    
    with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # 1. 创建回测说明sheet
        info_df = pd.DataFrame({
            '项目': ['股票代码', '股票名称', '回测起始日期', '回测结束日期', '初始资金', '回测说明'],
            '内容': [
                stock_code,
                stock_name,
                start_date,
                end_date,
                '¥1,000,000',
                '本回测包含12个策略：\n'
                '1. 增强策略：结合均线、RSI和MACD\n'
                '2. MACD策略：基于MACD金叉死叉\n'
                '3. KDJ策略：基于KDJ指标交叉\n'
                '4. 布林带策略：基于布林带通道\n'
                '5. 双均线量策略：结合均线和成交量\n'
                '6. 均值回归策略：基于价格回归均值\n'
                '7. 趋势跟踪策略：多周期趋势确认\n'
                '8. 量价分析策略：成交量价格配合\n'
                '9. 统计套利策略：基于统计套利模型\n'
                '10. 事件驱动策略：基于量价异动\n'
                '11. 质量轮动策略：多指标综合评分\n'
                '12. 风险平价策略：基于风险度量\n'
                '\n每个策略都包含止损止盈机制，考虑了交易成本，并在回测结束时强制平仓。'
            ]
        })
        info_df.to_excel(writer, sheet_name='回测说明', index=False)
        
        # 2. 创建策略表现对比sheet
        performance_data = []
        for strategy in strategies:
            profit = strategy.capital - strategy.initial_capital
            returns = profit / strategy.initial_capital
            total_trades = len([t for t in strategy.trades if t['type'] == '卖出'])
            winning_trades = sum(1 for i in range(0, len(strategy.trades), 2) 
                               if i+1 < len(strategy.trades) and 
                               strategy.trades[i+1]['amount'] - strategy.trades[i+1]['commission'] > 
                               strategy.trades[i]['amount'] + strategy.trades[i]['commission'])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            performance_data.append({
                '策略名称': strategy.name,
                '最终资金': round(strategy.capital, 2),
                '总收益': round(profit, 2),
                '收益率(%)': round(returns * 100, 2),
                '交易次数': total_trades,
                '胜率(%)': round(win_rate * 100, 2),
                '平均每笔盈亏': round(profit/total_trades if total_trades > 0 else 0, 2)
            })
        
        perf_df = pd.DataFrame(performance_data)
        
        # 添加回测信息到表头
        header_df = pd.DataFrame({
            '回测信息': [
                f'股票代码: {stock_code}',
                f'股票名称: {stock_name}',
                f'回测期间: {start_date} 至 {end_date}',
                f'初始资金: ¥{strategies[0].initial_capital:,.2f}',
                ''
            ]
        })
        
        # 将header_df和perf_df写入同一个sheet
        header_df.to_excel(writer, sheet_name='策略表现对比', index=False)
        perf_df.to_excel(writer, sheet_name='策略表现对比', startrow=len(header_df)+1, index=False)
        
        # 3. 为每个策略创建交易记录sheet
        for strategy in strategies:
            trades_df = pd.DataFrame(strategy.trades)
            if not trades_df.empty:
                # 添加成本价列
                trades_df['成本价'] = None
                buy_price = None
                for i in range(len(trades_df)):
                    if trades_df.iloc[i]['type'] == '买入':
                        buy_price = trades_df.iloc[i]['price']
                    trades_df.iloc[i, trades_df.columns.get_loc('成本价')] = buy_price
                
                # 修改列名为中文
                trades_df.columns = [
                    '交易日期', '交易类型', '成交价格', '成交数量', 
                    '成交金额', '手续费', '剩余资金', '成本价'
                ]
                
                sheet_name = f'{strategy.name}交易记录'
                trades_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # 设置列宽
                worksheet = writer.sheets[sheet_name]
                worksheet.set_column('A:A', 12)
                worksheet.set_column('B:B', 8)
                worksheet.set_column('C:C', 10)
                worksheet.set_column('D:D', 12)
                worksheet.set_column('E:H', 15)

def add_famous_investor_strategies(strategies, data):
    """添加模拟知名投资者的策略"""
    # 暂时不添加任何策略
    return strategies

def main():
    parser = argparse.ArgumentParser(description='股票策略回测系统')
    parser.add_argument('stock_code', type=str, help='股票代码（例：sh.600000）')
    parser.add_argument('start_date', type=str, help='开始日期（YYYY-MM-DD）')
    parser.add_argument('end_date', type=str, help='结束日期（YYYY-MM-DD）')
    parser.add_argument('--capital', type=float, default=1000000, help='初始资金（默认100万）')
    parser.add_argument('--commission', type=float, default=0.0003, help='手续费率（默认0.03%）')
    
    args = parser.parse_args()

    lg = bs.login()
    print('登录系统: ' + ('成功' if lg.error_code == '0' else '失败'))

    # 获取股票名称
    rs = bs.query_stock_basic(code=args.stock_code)
    stock_name = "未知"
    if rs.error_code == '0' and rs.next():
        stock_name = rs.get_row_data()[1]

    print("\n" + "="*80)
    print(f"股票代码: {args.stock_code}  股票名称: {stock_name}")
    print(f"回测期间: {args.start_date} 到 {args.end_date}")
    print(f"初始资金: ¥{args.capital:,.2f}")
    print("="*80)
    print("日期          |  策略名称  |  操作  |     价格    |    数量    |     金额      |     资金")
    print("-"*80)
    
    # 获取数据
    rs = bs.query_history_k_data_plus(args.stock_code,
        "date,code,open,high,low,close,volume,amount",
        start_date=args.start_date,
        end_date=args.end_date,
        frequency="d")
    
    data_list = []
    while rs.error_code == '0' and rs.next():
        data_list.append(rs.get_row_data())
    
    data = pd.DataFrame(data_list, columns=rs.fields)
    for col in ['open', 'high', 'low', 'close', 'volume']:
        data[col] = data[col].astype(float)
    
    # 初始化策略列表
    strategies = [
        EnhancedHybridStrategy(initial_capital=args.capital, commission_rate=args.commission),
        MACDStrategy(initial_capital=args.capital, commission_rate=args.commission),
        KDJStrategy(initial_capital=args.capital, commission_rate=args.commission),
        BollingerStrategy(initial_capital=args.capital, commission_rate=args.commission),
        DualMAVolumeStrategy(initial_capital=args.capital, commission_rate=args.commission),
        MeanReversionStrategy(initial_capital=args.capital, commission_rate=args.commission),
        TrendFollowingStrategy(initial_capital=args.capital, commission_rate=args.commission),
        VolumeBasedStrategy(initial_capital=args.capital, commission_rate=args.commission),
        StatisticalArbitrageStrategy(initial_capital=args.capital, commission_rate=args.commission),
        EventDrivenStrategy(initial_capital=args.capital, commission_rate=args.commission),
        QualityRotationStrategy(initial_capital=args.capital, commission_rate=args.commission),
        RiskParityStrategy(initial_capital=args.capital, commission_rate=args.commission)
    ]
    
    # 运行所有策略
    for strategy in strategies: 
        run_strategy(strategy, args.start_date, args.end_date, data)
        # 强制平仓
        if strategy.position > 0:
            last_date = data['date'].iloc[-1]
            last_price = data['close'].iloc[-1]
            last_volume = data['volume'].iloc[-1]
            strategy.execute_trade(last_date, last_price, 'SELL', last_volume)
    
    # 打印表现并导出
    print("\n" + "="*80)
    print(f"策略对比报告 - {args.stock_code} {stock_name}")
    print("="*80)
    
    for strategy in strategies:
        strategy.print_performance()

    export_to_excel(strategies, args.stock_code, stock_name, args.start_date, args.end_date, data)
    
    bs.logout()

if __name__ == "__main__":
    main()