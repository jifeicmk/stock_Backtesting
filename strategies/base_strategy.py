import numpy as np
from utils.utils import TradeLogger

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
        self.max_capital = initial_capital
        self.max_drawdown = 0
        self.drawdown_start = None
        self.drawdown_end = None
        self.current_drawdown_start = None

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
                TradeLogger.print_trade(trade, self.name, self.position)
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
            TradeLogger.print_trade(trade, self.name, self.position)

    def calculate_performance(self):
        """计算策略表现"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'total_profit': self.capital - self.initial_capital,
                'profit_rate': (self.capital - self.initial_capital) / self.initial_capital * 100,
                'max_drawdown': 0,
                'drawdown_period': ''
            }

        # 计算交易统计
        profits = []
        running_capital = self.initial_capital
        running_max_capital = self.initial_capital
        current_drawdown = 0
        max_drawdown = 0
        
        for trade in self.trades:
            if trade['type'] == '买入':
                running_capital -= (trade['amount'] + trade['commission'])
            else:  # 卖出
                running_capital += (trade['amount'] - trade['commission'])
                profit = trade['amount'] - trade['commission'] - \
                        (self.trades[len(profits)]['amount'] + self.trades[len(profits)]['commission'])
                profits.append(profit > 0)
                
                # 更新最大资金和回撤
                if running_capital > running_max_capital:
                    running_max_capital = running_capital
                    current_drawdown = 0
                    self.current_drawdown_start = None
                else:
                    drawdown = (running_max_capital - running_capital) / running_max_capital * 100
                    if drawdown > current_drawdown:
                        current_drawdown = drawdown
                        if self.current_drawdown_start is None:
                            self.current_drawdown_start = trade['date']
                    
                    if current_drawdown > max_drawdown:
                        max_drawdown = current_drawdown
                        self.drawdown_start = self.current_drawdown_start
                        self.drawdown_end = trade['date']

        win_rate = (sum(profits) / len(profits) * 100) if profits else 0
        avg_profit = ((self.capital - self.initial_capital) / len(profits)) if profits else 0

        return {
            'total_trades': len(profits),
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'total_profit': self.capital - self.initial_capital,
            'profit_rate': (self.capital - self.initial_capital) / self.initial_capital * 100,
            'max_drawdown': max_drawdown,
            'drawdown_period': f"{self.drawdown_start} 至 {self.drawdown_end}" if self.drawdown_start else "无显著回撤"
        }

    def print_performance(self):
        """打印策略表现"""
        perf = self.calculate_performance()
        print(f"\n{self.name}:")
        print(f"最终资金: ¥{self.capital:,.2f}")
        print(f"总收益: ¥{perf['total_profit']:,.2f}")
        print(f"收益率: {perf['profit_rate']:.2f}%")
        print(f"交易次数: {perf['total_trades']}")
        print(f"胜率: {perf['win_rate']:.2f}%")
        print(f"平均每笔盈亏: ¥{perf['avg_profit']:,.2f}")
        print(f"最大回撤: {perf['max_drawdown']:.2f}%")
        print(f"最大回撤区间: {perf['drawdown_period']}")

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