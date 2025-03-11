import talib
from strategies.base_strategy import BaseStrategy
from utils.utils import TradeLogger

class EnhancedHybridStrategy(BaseStrategy):
    def __init__(self, initial_capital, commission_rate):
        super().__init__("增强混合策略", initial_capital, commission_rate)
        # 降低MACD参数以提高灵敏度
        self.fast_period = 8  # 原为12
        self.slow_period = 17  # 原为26
        self.signal_period = 7  # 原为9
        
        # 调整RSI参数
        self.rsi_period = 10  # 原为14
        self.rsi_upper = 75  # 原为70
        self.rsi_lower = 25  # 原为30
        
        # 调整均线参数
        self.ma_short = 5  # 原为10
        self.ma_long = 15  # 原为20
        
        # 调整布林带参数
        self.bb_period = 15  # 原为20
        self.bb_std = 1.8  # 原为2.0
        
        # 风控参数
        self.stop_loss = 0.03  # 3%止损
        self.profit_target = 0.05  # 5%止盈
        self.trailing_stop = 0.02  # 2%追踪止损
        
        # 参数设置 - 缩短周期以增加交易频率
        self.short_period = 3
        self.medium_period = 7
        self.volume_ma_period = 10
        self.atr_period = 10
        self.min_holding_days = 2
        self.last_signal_date = None
        
        # 动态止损参数 - 调整止损设置
        self.initial_stop_loss = 0.015
        self.max_profit = 0
        
        # 仓位管理参数 - 更积极的仓位管理
        self.max_position_size = 0.9
        self.min_position_size = 0.3
        self.position_step = 0.15
        
        # 当前行数据
        self._current_row = None

    def set_current_row(self, row):
        """设置当前行数据"""
        self._current_row = row

    def calculate_signals(self, data):
        df = data.copy()
        
        # 计算MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(
            df['close'], 
            fastperiod=self.fast_period, 
            slowperiod=self.slow_period, 
            signalperiod=self.signal_period
        )
        
        # 计算RSI
        df['rsi'] = talib.RSI(df['close'], timeperiod=self.rsi_period)
        
        # 计算均线
        df['ma_short'] = talib.SMA(df['close'], timeperiod=self.ma_short)
        df['ma_medium'] = talib.EMA(df['close'], self.medium_period)
        df['ma_long'] = talib.SMA(df['close'], timeperiod=self.ma_long)
        
        # 计算布林带
        df['bb_middle'], df['bb_upper'], df['bb_lower'] = talib.BBANDS(
            df['close'], 
            timeperiod=self.bb_period,
            nbdevup=self.bb_std,
            nbdevdn=self.bb_std
        )
        
        # 计算成交量指标
        df['volume_ma'] = talib.SMA(df['volume'], timeperiod=20)
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # 5. ATR和波动率
        df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=self.atr_period)
        df['volatility'] = df['atr'] / df['close']
        
        # 6. 趋势强度
        df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
        
        # 7. 动量指标
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
        if row['rsi'] < self.rsi_lower or row['rsi'] > self.rsi_upper:
            position_size -= self.position_step
            
        # 根据波动率调整仓位
        if row['volatility'] < 0.02:
            position_size += self.position_step
            
        # 确保仓位在允许范围内
        return min(max(position_size, self.min_position_size), self.max_position_size)

    def generate_signal(self, row, prev_row):
        signal = 'HOLD'
        
        # 买入条件：
        # 1. MACD金叉或柱状图转正
        macd_buy = (prev_row['macd_hist'] < 0 and row['macd_hist'] > 0) or \
                   (row['macd'] > row['macd_signal'] and prev_row['macd'] <= prev_row['macd_signal'])
        
        # 2. RSI超卖回升
        rsi_buy = row['rsi'] < self.rsi_lower and row['rsi'] > prev_row['rsi']
        
        # 3. 均线支撑或金叉
        ma_buy = (row['close'] > row['ma_short'] > row['ma_long']) or \
                 (row['ma_short'] > row['ma_long'] and prev_row['ma_short'] <= prev_row['ma_long'])
        
        # 4. 布林带支撑
        bb_buy = row['close'] < (row['bb_lower'] * 1.02)  # 允许价格略高于下轨
        
        # 5. 成交量确认
        volume_confirm = row['volume_ratio'] > 0.8  # 降低成交量要求
        
        # 卖出条件：
        # 1. MACD死叉或柱状图转负
        macd_sell = (prev_row['macd_hist'] > 0 and row['macd_hist'] < 0) or \
                    (row['macd'] < row['macd_signal'] and prev_row['macd'] >= prev_row['macd_signal'])
        
        # 2. RSI超买回落
        rsi_sell = row['rsi'] > self.rsi_upper and row['rsi'] < prev_row['rsi']
        
        # 3. 均线阻力或死叉
        ma_sell = (row['close'] < row['ma_short'] < row['ma_long']) or \
                  (row['ma_short'] < row['ma_long'] and prev_row['ma_short'] >= prev_row['ma_long'])
        
        # 4. 布林带压力
        bb_sell = row['close'] > (row['bb_upper'] * 0.98)  # 允许价格略低于上轨
        
        if self.position <= 0:
            # 买入信号需要满足至少2个条件（原为3个）
            conditions = [macd_buy, rsi_buy, ma_buy, bb_buy]
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
            
            # 卖出信号需要满足至少2个条件（原为3个）或触发止损/止盈
            conditions = [macd_sell, rsi_sell, ma_sell, bb_sell]
            if sum(conditions) >= 2 or stop_loss_triggered or take_profit:
                signal = 'SELL'
                if hasattr(self, 'highest_price'):
                    delattr(self, 'highest_price')
        
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
                    TradeLogger.print_trade(trade, self.name, self.position)
                    
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
            TradeLogger.print_trade(trade, self.name, self.position) 