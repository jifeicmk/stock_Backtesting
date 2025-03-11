"""
策略参数配置文件
包含所有交易策略的参数设置
"""

# 双均线量策略参数
DUAL_MA_VOLUME_CONFIG = {
    'fast_period': 5,
    'slow_period': 20,
    'volume_ma_period': 20,
    'volume_threshold': 1.5,
    'stop_loss': 0.02,
    'profit_target': 0.04
}

# 均值回归策略参数
MEAN_REVERSION_CONFIG = {
    'ma_period': 20,
    'std_dev_period': 20,
    'std_dev_multiplier': 2,
    'rsi_period': 14,
    'rsi_oversold': 30,
    'rsi_overbought': 70,
    'stop_loss': 0.02,
    'profit_target': 0.04
}

# 趋势跟踪策略参数
TREND_FOLLOWING_CONFIG = {
    'short_period': 20,
    'medium_period': 60,
    'long_period': 120,
    'atr_period': 14,
    'atr_multiplier': 1.5,
    'adx_period': 14,
    'adx_threshold': 25,
    'stop_loss': 0.02
}

# 量价分析策略参数
VOLUME_BASED_CONFIG = {
    'volume_ma_period': 20,
    'price_ma_period': 20,
    'volume_threshold': 2.0,
    'price_change_threshold': 0.02,
    'obv_ma_period': 20,
    'mfi_period': 14,
    'mfi_oversold': 20,
    'mfi_overbought': 80,
    'stop_loss': 0.03,
    'profit_target': 0.05
}

# 统计套利策略参数
STATISTICAL_ARBITRAGE_CONFIG = {
    'lookback_period': 60,
    'zscore_threshold': 2.0,
    'ma_period': 20,
    'std_period': 20,
    'correlation_period': 60,
    'stop_loss': 0.03,
    'profit_target': 0.05
}

# 事件驱动策略参数
EVENT_DRIVEN_CONFIG = {
    'volume_surge_threshold': 3.0,
    'price_change_threshold': 0.05,
    'ma_period': 20,
    'volatility_period': 20,
    'rsi_period': 14,
    'rsi_oversold': 30,
    'rsi_overbought': 70,
    'stop_loss': 0.03,
    'profit_target': 0.05
}

# 布林带策略参数
BOLLINGER_CONFIG = {
    'period': 20,
    'std_dev': 2,
    'stop_loss': 0.03,
    'profit_target': 0.05
}

# MACD策略参数
MACD_CONFIG = {
    'fast_period': 12,
    'slow_period': 26,
    'signal_period': 9,
    'stop_loss': 0.03,
    'profit_target': 0.05
}

# KDJ策略参数
KDJ_CONFIG = {
    'fastk_period': 9,
    'slowk_period': 3,
    'slowd_period': 3,
    'stop_loss': 0.03,
    'profit_target': 0.05
}

# 增强混合策略参数
ENHANCED_HYBRID_CONFIG = {
    'ma_short': 5,
    'ma_long': 20,
    'rsi_period': 14,
    'rsi_oversold': 30,
    'rsi_overbought': 70,
    'volume_ma_period': 20,
    'volume_threshold': 2.0,
    'stop_loss': 0.03,
    'profit_target': 0.05
}

# 质量轮动策略参数
QUALITY_ROTATION_CONFIG = {
    'ma_period': 20,
    'momentum_period': 60,
    'volatility_period': 20,
    'quality_threshold': 0.7,
    'momentum_threshold': 0.02,
    'stop_loss': 0.03,
    'profit_target': 0.05
}

# 风险平价策略参数
RISK_PARITY_CONFIG = {
    'volatility_period': 60,
    'ma_period': 20,
    'risk_target': 0.15,
    'max_leverage': 2.0,
    'min_position': 0.1,
    'stop_loss': 0.03,
    'profit_target': 0.05
}

# 突破策略参数
BREAKOUT_CONFIG = {
    # 突破参数
    'price_period': 10,  # 价格突破观察周期
    'volume_period': 5,  # 成交量突破观察周期
    'breakout_threshold': 1.008,  # 突破阈值（0.8%）
    'volume_threshold': 1.2,  # 成交量突破阈值（1.2倍）
    
    # 趋势确认参数
    'ma_short': 3,  # 短期均线周期
    'ma_long': 10,  # 长期均线周期
    'rsi_period': 8,  # RSI周期
    
    # MACD参数
    'macd_fast': 8,  # MACD快线周期
    'macd_slow': 17,  # MACD慢线周期
    'macd_signal': 9,  # MACD信号线周期
    
    # 波动率参数
    'volatility_period': 10,  # 波动率计算周期
    'min_volatility': 0.005,  # 最小波动率要求
    'max_volatility': 0.05,   # 最大波动率限制
    'atr_period': 10,  # ATR计算周期
    
    # 动量参数
    'momentum_period': 3,  # 动量计算周期
    
    # 风控参数
    'stop_loss': 0.02,  # 止损比例（2%）
    'profit_target': 0.03,  # 止盈比例（3%）
    'trailing_stop': 0.015,  # 追踪止损比例（1.5%）
    
    # 仓位管理
    'max_position_pct': 0.3,  # 最大仓位比例（30%）
    'max_volume_pct': 0.1,  # 最大成交量使用比例（10%）
} 