import backtrader as bt

class TrendBBStrategy(bt.Strategy):
    params = (
        ('ma_period', 50),      # 長期趨勢均線
        ('bb_period', 20),      # 布林通道週期
        ('bb_dev', 2.0),        # 布林通道標準差
        ('tradeValue', 500000), # 單筆預計投入金額
    )

    def __init__(self):
        # 1. 定義移動平均線 (判斷大趨勢)
        self.ma50 = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.ma_period
        )

        # 2. 定義布林通道
        self.bb = bt.indicators.BollingerBands(
            self.data.close, 
            period=self.params.bb_period, 
            devfactor=self.params.bb_dev
        )

        # 為了方便讀取，給軌道取別名
        self.top = self.bb.lines.top
        self.bot = self.bb.lines.bot

    def next(self):
        current_equity = self.broker.getvalue()
        
        # 取得當前價格與軌道值
        close = self.data.close[0]
        open_price = self.data.open[0]

        # --- 無持倉：進場邏輯 ---
        if not self.position:
            # 多頭趨勢：收盤 > MA50 且 觸及布林下軌 (低接)
            if close > self.ma50[0] and close <= self.bot[0]:
                actual_invest = min(self.params.tradeValue, current_equity * 0.95)
                self.order_target_value(target=actual_invest)
                self.log(f"【做多進場】價格: {close}, 日期: {self.data.datetime.date(0)}")

            # 空頭趨勢：收盤 < MA50 且 觸及布林上軌 (高拋)
            # 註：Backtrader 做空需確保券商設定允許，此處以 sell 表示
            elif close < self.ma50[0] and close >= self.top[0]:
                actual_invest = min(self.params.tradeValue, current_equity * 0.95)
                self.order_target_value(target=-actual_invest) # 負值代表放空目標價值
                self.log(f"【做空進場】價格: {close}, 日期: {self.data.datetime.date(0)}")

        # --- 有持倉：出場邏輯 ---
        else:
            # 持有多單 (Long Position)
            if self.position.size > 0:
                # 停利：觸及布林上軌
                if close >= self.top[0]:
                    self.close()
                    self.log(f"【多單停利】價格: {close}, 日期: {self.data.datetime.date(0)}")
                
                # 停損：開盤與收盤皆破下軌
                elif close < self.bot[0] and open_price < self.bot[0]:
                    self.close()
                    self.log(f"【多單停損】價格: {close}, 日期: {self.data.datetime.date(0)}")

            # 持有空單 (Short Position)
            elif self.position.size < 0:
                # 停利：觸及布林下軌
                if close <= self.bot[0]:
                    self.close()
                    self.log(f"【空單停利】價格: {close}, 日期: {self.data.datetime.date(0)}")
                
                # 停損：開盤與收盤皆破上軌
                elif close > self.top[0] and open_price > self.top[0]:
                    self.close()
                    self.log(f"【空單停損】價格: {close}, 日期: {self.data.datetime.date(0)}")

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                self.highest_price = order.executed.price  # 初始化最高價
                self.log(f"買入執行: {self.buy_price:.2f}, 日期 {self.data.datetime.date(0)}")
            elif order.issell():
                self.log(f"賣出執行: {order.executed.price:.2f}, 日期 {self.data.datetime.date(0)}")
                # 重置追蹤變數
                self.buy_price = None
                self.highest_price = None