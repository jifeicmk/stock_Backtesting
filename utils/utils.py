import pandas as pd
from datetime import datetime

class TradeLogger:
    RED = '\033[91m'
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    ENDC = '\033[0m'

    @staticmethod
    def print_trade(trade, strategy_name, position):
        """打印交易信息"""
        formatted_price = f"¥{trade['price']:.2f}"
        formatted_amount = f"¥{trade['amount']:,.2f}"
        formatted_capital = f"¥{trade['capital']:,.2f}"
        
        color = TradeLogger.GREEN if trade['type'] == '买入' else TradeLogger.RED
        
        trade_info = (
            f"{TradeLogger.BLUE}{trade['date']}{TradeLogger.ENDC} | "
            f"{TradeLogger.YELLOW}{strategy_name:10}{TradeLogger.ENDC} | "
            f"{color}{trade['type']:4}{TradeLogger.ENDC} | "
            f"价格: {formatted_price:>10} | "
            f"数量: {trade['shares']:>8,d}股 | "
            f"金额: {formatted_amount:>12} | "
            f"资金: {formatted_capital:>12}"
        )
        print(trade_info)
        
        if position != 0:
            position_info = " " * 24 + f"{TradeLogger.YELLOW}当前持仓: {position:,d}股{TradeLogger.ENDC}"
            print(position_info)

class ExcelExporter:
    @staticmethod
    def export_results(strategies, stock_code, stock_name, start_date, end_date, data):
        """导出回测结果到Excel"""
        try:
            # 生成文件名
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
                        '本回测包含14个策略：\n'
                        '1. 增强混合策略：结合多个技术指标的综合策略\n'
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
                        '13. 波段策略：多指标波段操作\n'
                        '14. 突破策略：价量配合突破\n'
                        '\n每个策略都包含止损止盈机制，考虑了交易成本，并在回测结束时强制平仓。'
                    ]
                })
                info_df.to_excel(writer, sheet_name='回测说明', index=False)
                
                # 设置回测说明sheet的格式
                worksheet = writer.sheets['回测说明']
                worksheet.set_column('A:A', 15)
                worksheet.set_column('B:B', 50)
                
                # 2. 创建策略表现对比sheet
                performance_data = []
                for strategy in strategies:
                    perf = strategy.calculate_performance()
                    total_profit = strategy.capital - strategy.initial_capital
                    return_rate = (total_profit / strategy.initial_capital) * 100
                    
                    # 确保回撤日期是有效的
                    drawdown_start = strategy.drawdown_start if hasattr(strategy, 'drawdown_start') and strategy.drawdown_start else '无回撤'
                    drawdown_end = strategy.drawdown_end if hasattr(strategy, 'drawdown_end') and strategy.drawdown_end else '无回撤'
                    
                    # 尝试解析日期字符串
                    try:
                        if drawdown_start != '无回撤' and drawdown_end != '无回撤':
                            start_date_obj = datetime.strptime(drawdown_start, '%Y-%m-%d')
                            end_date_obj = datetime.strptime(drawdown_end, '%Y-%m-%d')
                            
                            # 确保开始日期在结束日期之前
                            if start_date_obj > end_date_obj:
                                drawdown_start, drawdown_end = drawdown_end, drawdown_start
                    except:
                        # 如果解析失败，使用默认值
                        pass
                    
                    performance_data.append({
                        '策略名称': strategy.name,
                        '最终资金': strategy.capital,
                        '总收益': total_profit,
                        '收益率(%)': return_rate,
                        '交易次数': perf['total_trades'],
                        '胜率(%)': perf['win_rate'],
                        '平均每笔盈亏': perf['avg_profit'],
                        '最大回撤(%)': perf['max_drawdown'],
                        '回撤开始时间': drawdown_start,
                        '回撤结束时间': drawdown_end
                    })
                
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
                
                # 将header_df和performance_data写入同一个sheet
                header_df.to_excel(writer, sheet_name='策略表现对比', index=False)
                perf_df = pd.DataFrame(performance_data)
                perf_df.to_excel(writer, sheet_name='策略表现对比', startrow=len(header_df)+1, index=False)
                
                # 设置策略表现对比sheet的格式
                worksheet = writer.sheets['策略表现对比']
                money_format = workbook.add_format({'num_format': '¥#,##0.00'})
                percent_format = workbook.add_format({'num_format': '0.00'})  # 改为显示两位小数
                date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
                
                worksheet.set_column('A:A', 15)  # 策略名称
                worksheet.set_column('B:B', 15, money_format)  # 最终资金
                worksheet.set_column('C:C', 15, money_format)  # 总收益
                worksheet.set_column('D:D', 12, percent_format)  # 收益率
                worksheet.set_column('E:E', 10)  # 交易次数
                worksheet.set_column('F:F', 10, percent_format)  # 胜率
                worksheet.set_column('G:G', 15, money_format)  # 平均每笔盈亏
                worksheet.set_column('H:H', 12, percent_format)  # 最大回撤
                
                # 特别处理回撤时间列，将日期格式化
                for row_idx, row in enumerate(performance_data):
                    try:
                        if row['回撤开始时间'] != '无回撤':
                            date_obj = datetime.strptime(row['回撤开始时间'], '%Y-%m-%d')
                            worksheet.write_datetime(row_idx + len(header_df) + 2, 8, date_obj, date_format)
                        else:
                            worksheet.write_string(row_idx + len(header_df) + 2, 8, '无回撤')
                            
                        if row['回撤结束时间'] != '无回撤':
                            date_obj = datetime.strptime(row['回撤结束时间'], '%Y-%m-%d')
                            worksheet.write_datetime(row_idx + len(header_df) + 2, 9, date_obj, date_format)
                        else:
                            worksheet.write_string(row_idx + len(header_df) + 2, 9, '无回撤')
                    except:
                        # 如果日期解析失败，使用普通文本
                        pass
                
                # 设置列宽
                worksheet.set_column('I:J', 20)  # 回撤时间
                
                # 3. 为每个策略创建交易记录sheet
                for strategy in strategies:
                    if strategy.trades:
                        trades_df = pd.DataFrame(strategy.trades)
                        
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
                        
                        sheet_name = f'{strategy.name}交易记录'[:31]  # Excel工作表名最大31字符
                        trades_df.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                        # 设置交易记录sheet的格式
                        worksheet = writer.sheets[sheet_name]
                        worksheet.set_column('A:A', 12, date_format)  # 交易日期
                        worksheet.set_column('B:B', 8)  # 交易类型
                        worksheet.set_column('C:C', 10, money_format)  # 成交价格
                        worksheet.set_column('D:D', 12)  # 成交数量
                        worksheet.set_column('E:H', 15, money_format)  # 金额相关列
                
            print(f"\n回测报告已导出到: {filename}")
            
        except Exception as e:
            print(f"导出Excel时发生错误: {str(e)}")

    @staticmethod
    def get_strategy_description(strategy_name):
        """获取策略说明"""
        descriptions = {
            '波段策略': '''
            波段策略是一种结合多个技术指标来捕捉市场波动的交易策略。主要特点：
            1. 使用MACD、RSI、布林带和KDJ等多重技术指标
            2. 买入条件需满足至少3个指标确认（RSI超卖回升、价格接近布林带下轨、MACD金叉等）
            3. 卖出同样需要多重指标确认或触发止损/止盈
            4. 采用ATR动态调整仓位，控制风险
            5. 使用追踪止损保护盈利
            ''',
            '突破策略': '''
            突破策略专注于捕捉价格和成交量的突破机会。主要特点：
            1. 监控20日价格高点和10日成交量突破
            2. 使用均线、MACD和RSI等指标确认趋势
            3. 要求成交量配合，突破时成交量需放大2倍以上
            4. 采用5%止损和10%止盈，外加2%追踪止损
            5. 使用ATR和趋势强度进行仓位管理
            '''
        }
        return descriptions.get(strategy_name, "暂无策略说明") 