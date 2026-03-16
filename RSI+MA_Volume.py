import backtrader as bt

class CombinedStrategy(bt.Strategy):
    params = (
        ('fast_period', 5),
        ('slow_period', 20),
        ('exit_period', 10),
        ('rsi_period', 14),
        ('rsi_buy_level', 60),
        ('rsi_sell_level', 40),
        ('vol_period', 5),
        ('vol_buy_ratio', 1.5),
        ('vol_sell_ratio', 0.8),
        ('tradeValue', 500000),
        ('stop_loss', 0.05),      # 固定停損 5%
        ('trail_percent', 0.03),  # 創新高後回檔 3% 停利
    )

    def __init__(self):
        # 基礎指標定義
        self.fast_ma = bt.indicators.SMA(self.data.close, period=self.params.fast_period)
        self.slow_ma = bt.indicators.SMA(self.data.close, period=self.params.slow_period)
        self.exit_ma = bt.indicators.SMA(self.data.close, period=self.params.exit_period)
        self.ma_crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        self.vol_ma = bt.indicators.SMA(self.data.volume, period=self.params.vol_period)
        
        # 用於追蹤停利與停損的變數
        self.buy_price = None
        self.highest_price = None

    def next(self):
        current_equity = self.broker.getvalue()

        # --- 無持倉：進場邏輯 ---
        if not self.position:
            # 買入條件：5MA上穿20MA AND (RSI > 60 OR 量增 1.5倍)
            buy_sig = (self.ma_crossover > 0) and (
                (self.rsi[0] > self.params.rsi_buy_level) or 
                (self.data.volume[0] > self.vol_ma[0] * self.params.vol_buy_ratio)
            )
            
            if buy_sig:
                actual_invest = min(self.params.tradeValue, current_equity * 0.95)
                self.order_target_value(target=actual_invest)
                # 注意：buy_price 會在 notify_order 中正式成交時更新

        # --- 有持倉：出場邏輯 ---
        else:
            if self.buy_price is None or self.highest_price is None:
                return
            # 更新持倉期間最高價
            self.highest_price = max(self.highest_price, self.data.close[0])
            
            # 1. 固定停損：價格跌超過進場價的 5%
            stop_loss_signal = self.data.close[0] < self.buy_price * (1 - self.params.stop_loss)
            
            # 2. 移動停利：價格從最高點回檔超過 3%
            take_profit_signal = self.data.close[0] < self.highest_price * (1 - self.params.trail_percent)
            
            # 3. 原本的指標條件賣出 (跌破10MA AND RSI<40 AND 量縮)
            indicator_sell_sig = (self.data.close[0] < self.exit_ma[0]) and \
                                (self.rsi[0] < self.params.rsi_sell_level) and \
                                 (self.data.volume[0] < self.vol_ma[0] * self.params.vol_sell_ratio)

            if stop_loss_signal:
                print(f"【固定停損觸發】日期: {self.data.datetime.date(0)}")
                self.close()
            elif take_profit_signal:
                print(f"【移動停利觸發】日期: {self.data.datetime.date(0)}")
                self.close()
            elif indicator_sell_sig:
                print(f"【指標訊號賣出】日期: {self.data.datetime.date(0)}")
                self.close()

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                self.highest_price = order.executed.price  # 初始化最高價
                print(f"買入執行: {self.buy_price:.2f}, 日期 {self.data.datetime.date(0)}")
            elif order.issell():
                print(f"賣出執行: {order.executed.price:.2f}, 日期 {self.data.datetime.date(0)}")
                # 重置追蹤變數
                self.buy_price = None
                self.highest_price = None
