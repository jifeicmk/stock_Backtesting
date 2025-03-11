import baostock as bs
import pandas as pd

class DataProvider:
    @staticmethod
    def get_stock_data(stock_code, start_date, end_date):
        """
        从baostock获取股票数据
        
        Args:
            stock_code (str): 股票代码（如：sh.600000）
            start_date (str): 开始日期（YYYY-MM-DD）
            end_date (str): 结束日期（YYYY-MM-DD）
            
        Returns:
            pd.DataFrame: 包含股票数据的DataFrame
        """
        # 登录系统
        lg = bs.login()
        if lg.error_code != '0':
            print('登录失败')
            return None
            
        try:
            # 获取股票数据
            rs = bs.query_history_k_data_plus(
                stock_code,
                "date,code,open,high,low,close,volume,amount",
                start_date=start_date,
                end_date=end_date,
                frequency="d"
            )
            
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            # 转换为DataFrame
            data = pd.DataFrame(data_list, columns=rs.fields)
            
            # 转换数据类型
            for col in ['open', 'high', 'low', 'close', 'volume']:
                data[col] = data[col].astype(float)
                
            return data
            
        finally:
            bs.logout()
    
    @staticmethod
    def get_stock_name(stock_code):
        """
        获取股票名称
        
        Args:
            stock_code (str): 股票代码
            
        Returns:
            str: 股票名称
        """
        lg = bs.login()
        try:
            rs = bs.query_stock_basic(code=stock_code)
            if rs.error_code == '0' and rs.next():
                return rs.get_row_data()[1]
            return "未知"
        finally:
            bs.logout() 