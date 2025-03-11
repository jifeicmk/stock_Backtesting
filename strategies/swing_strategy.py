import talib
import numpy as np
import pandas as pd
from strategies.base_strategy import BaseStrategy
from utils.utils import TradeLogger

class SwingStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("波段策略", initial_capital, commission_rate)
        # 技术指标参数
        self.fast_period = 5
        self.slow_period = 10
        self.signal_period = 9
        self.rsi_period = 14
        self.bb_period = 20
        self.atr_period = 14
        
        # 波段交易参数
        self.oversold_threshold = 30
        self.overbought_threshold = 70
        self.bb_dev = 2.0
        self.volume_ma_period = 20
        
        # 止损止盈参数
        self.stop_loss = 0.03
        self.profit_target = 0.05
        self.trailing_stop = 0.02

    def calculate_signals(self, data):
        df = data.copy()
        
        # 计算MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(
            df['close'], fastperiod=self.fast_period, 
            slowperiod=self.slow_period, signalperiod=self.signal_period)
        
        # 计算RSI
        df['rsi'] = talib.RSI(df['close'], timeperiod=self.rsi_period)
        
        # 计算布林带
        df['bb_middle'], df['bb_upper'], df['bb_lower'] = talib.BBANDS(
            df['close'], timeperiod=self.bb_period, 
            nbdevup=self.bb_dev, nbdevdn=self.bb_dev)
        
        # 计算ATR
        df['atr'] = talib.ATR(df['high'], df['low'], df['close'], 
                             timeperiod=self.atr_period)
        
        # 计算KDJ
        high_list = df['high'].rolling(9).max()
        low_list = df['low'].rolling(9).min()
        rsv = (df['close'] - low_list) / (high_list - low_list) * 100
        df['k'] = rsv.rolling(3).mean()
        df['d'] = df['k'].rolling(3).mean()
        df['j'] = 3 * df['k'] - 2 * df['d']
        
        # 计算成交量指标
        df['volume_ma'] = talib.SMA(df['volume'], self.volume_ma_period)
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # 计算趋势强度
        df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
        df['di_plus'] = talib.PLUS_DI(df['high'], df['low'], df['close'], timeperiod=14)
        df['di_minus'] = talib.MINUS_DI(df['high'], df['low'], df['close'], timeperiod=14)
        
        return df

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        # 买入条件：
        # 1. RSI超卖回升
        # 2. 价格接近布林带下轨
        # 3. MACD柱状图由负转正
        # 4. KDJ金叉
        # 5. 成交量放大
        # 6. ADX显示趋势开始
        rsi_buy = (prev_row['rsi'] < self.oversold_threshold and 
                  row['rsi'] > prev_row['rsi'])
        bb_buy = row['close'] < row['bb_lower'] * 1.01
        macd_buy = (prev_row['macd_hist'] < 0 and row['macd_hist'] > 0)
        kdj_buy = (prev_row['k'] < prev_row['d'] and row['k'] > row['d'])
        volume_buy = row['volume_ratio'] > 1.2
        trend_buy = (row['adx'] > 20 and row['di_plus'] > row['di_minus'])
        
        # 卖出条件：
        # 1. RSI超买回落
        # 2. 价格接近布林带上轨
        # 3. MACD柱状图由正转负
        # 4. KDJ死叉
        # 5. 成交量萎缩
        rsi_sell = (prev_row['rsi'] > self.overbought_threshold and 
                   row['rsi'] < prev_row['rsi'])
        bb_sell = row['close'] > row['bb_upper'] * 0.99
        macd_sell = (prev_row['macd_hist'] > 0 and row['macd_hist'] < 0)
        kdj_sell = (prev_row['k'] > prev_row['d'] and row['k'] < row['d'])
        volume_sell = row['volume_ratio'] < 0.8
        trend_sell = (row['adx'] > 20 and row['di_minus'] > row['di_plus'])
        
        # 生成交易信号
        if self.position <= 0:
            # 买入信号需要满足至少3个条件
            conditions = [rsi_buy, bb_buy, macd_buy, kdj_buy, volume_buy, trend_buy]
            if sum(conditions) >= 3:
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
            
            # 卖出信号需要满足至少3个条件或触发止损/止盈
            conditions = [rsi_sell, bb_sell, macd_sell, kdj_sell, volume_sell, trend_sell]
            if sum(conditions) >= 3 or stop_loss_triggered or take_profit:
                signal = 'SELL'
                if hasattr(self, 'highest_price'):
                    delattr(self, 'highest_price')
        
        return signal

    def execute_trade(self, date, price, signal, volume):
        """执行交易"""
        if signal == 'BUY' and self.position <= 0:
            # 计算可买入股数（考虑ATR进行风险控制）
            temp_df = pd.DataFrame({
                'high': [price] * 15,  # 使用15个相同的价格点来确保ATR能够计算
                'low': [price] * 15,
                'close': [price] * 15,
                'volume': [volume] * 15,
                'date': [date] * 15
            })
            atr = talib.ATR(temp_df['high'], temp_df['low'], temp_df['close'], timeperiod=self.atr_period).iloc[-1]
            
            if pd.isna(atr):  # 如果ATR仍然是NaN，使用价格的一个小比例作为替代
                atr = price * 0.002  # 使用0.2%作为默认波动率
            
            risk_per_share = atr * 2  # 使用2倍ATR作为每股风险
            position_size = min(0.02 * self.capital / risk_per_share,  # 最多风险2%资金
                              0.2 * self.capital / price)  # 最多使用20%资金
            
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