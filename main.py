import argparse
from data.data_provider import DataProvider
from utils.utils import ExcelExporter
from strategies.macd_strategy import MACDStrategy
from strategies.enhanced_hybrid_strategy import EnhancedHybridStrategy
from strategies.kdj_strategy import KDJStrategy
from strategies.bollinger_strategy import BollingerStrategy
from strategies.dual_ma_volume_strategy import DualMAVolumeStrategy
from strategies.mean_reversion_strategy import MeanReversionStrategy
from strategies.trend_following_strategy import TrendFollowingStrategy
from strategies.volume_based_strategy import VolumeBasedStrategy
from strategies.statistical_arbitrage_strategy import StatisticalArbitrageStrategy
from strategies.event_driven_strategy import EventDrivenStrategy
from strategies.quality_rotation_strategy import QualityRotationStrategy
from strategies.risk_parity_strategy import RiskParityStrategy
from strategies.dca_strategy import DCAStrategy
from strategies.swing_strategy import SwingStrategy
from strategies.breakout_strategy import BreakoutStrategy


def run_strategy(strategy, start_date, end_date, stock_code, data=None):
    """运行单个策略"""
    if data is None:
        data = DataProvider.get_stock_data(stock_code, start_date, end_date)
        if data is None:
            return
    
    # 确保数值列为float类型
    for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
        if col in data.columns:
            data[col] = data[col].astype(float)
    
    df = strategy.calculate_signals(data.copy())
    
    for i in range(1, len(df)):
        date = df['date'].iloc[i]
        price = float(df['close'].iloc[i])
        volume = float(df['volume'].iloc[i])
        
        # 判断是否是最后一个交易日
        is_last_day = (i == len(df) - 1)
        
        # 设置当前行数据（用于增强混合策略）
        if hasattr(strategy, 'set_current_row'):
            strategy.set_current_row(df.iloc[i])
        
        # 修改为传递当前行和前一行的数据
        signal = strategy.generate_signal(df.iloc[i], df.iloc[i-1])
        
        # 如果是最后一个交易日且还有持仓，强制平仓
        if is_last_day and strategy.position > 0:
            signal = 'SELL'
            print(f"\n{strategy.name} 回测结束，强制平仓")
        
        if signal != 'HOLD':
            strategy.execute_trade(date, price, signal, volume)

def main():
    parser = argparse.ArgumentParser(description='股票策略回测系统')
    parser.add_argument('stock_code', type=str, help='股票代码（例：sh.600000）')
    parser.add_argument('start_date', type=str, help='开始日期（YYYY-MM-DD）')
    parser.add_argument('end_date', type=str, help='结束日期（YYYY-MM-DD）')
    parser.add_argument('--capital', type=float, default=1000000, help='初始资金（默认100万）')
    parser.add_argument('--commission', type=float, default=0.0003, help='手续费率（默认0.03%）')
    
    args = parser.parse_args()

    # 获取股票名称
    stock_name = DataProvider.get_stock_name(args.stock_code)

    print("\n" + "="*80)
    print(f"股票代码: {args.stock_code}  股票名称: {stock_name}")
    print(f"回测期间: {args.start_date} 到 {args.end_date}")
    print(f"初始资金: ¥{args.capital:,.2f}")
    print(f"手续费率: {args.commission:.4%}")
    print("="*80)
    print("日期          |  策略名称  |  操作  |     价格    |    数量    |     金额      |     资金")
    print("-"*80)
    
    # 获取数据
    data = DataProvider.get_stock_data(args.stock_code, args.start_date, args.end_date)
    if data is None:
        return
    
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
        RiskParityStrategy(initial_capital=args.capital, commission_rate=args.commission),
        DCAStrategy(initial_capital=args.capital, commission_rate=args.commission),
        SwingStrategy(initial_capital=args.capital, commission_rate=args.commission),
        BreakoutStrategy(initial_capital=args.capital, commission_rate=args.commission)
    ]
    
    # 运行所有策略
    for strategy in strategies:
        run_strategy(strategy, args.start_date, args.end_date, args.stock_code, data)
    
    # 打印表现并导出
    print("\n" + "="*80)
    print(f"策略对比报告 - {args.stock_code} {stock_name}")
    print("="*80)
    
    for strategy in strategies:
        strategy.print_performance()

    ExcelExporter.export_results(strategies, args.stock_code, stock_name, 
                               args.start_date, args.end_date, data)

if __name__ == "__main__":
    main() 