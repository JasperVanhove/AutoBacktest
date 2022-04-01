import pandas as pd
import talib

from models.Strategies.Strategy import Strategy


class EmaStochRsiDivergence(Strategy):
    def __init__(self, symbol, timeframe, atr_multiplier=1.5, rr=2):
        super(EmaStochRsiDivergence, self).__init__(symbol, timeframe, atr_multiplier, rr)

        self.name = '200-EMA + Stochastic cross + RSI Divergence Strategy'
        self.short_name = 'EMA_STOCH_RSI_DIV'
        self.ema_period = 200

        self.rsi_period = 14

        self.stoch_period = 14
        self.fastk = 3
        self.fastd = 3
        self.fastd_ma = 0

        self.zero_line = 0
        self.swing_lockback_period = 10

        self.div_lookback_period = 10
        self.trigger_candle = 1
        self.pivot_period = 5
        self.max_pivot = 10
        self.div_max_candles = 100

    def set_indicators(self):
        self.df = self.df.loc[self.df.notnull().all(axis=1).argmax():]
        self.df.reset_index(inplace=True)

        self.df['EMA'] = talib.EMA(self.df['Close'], timeperiod=self.ema_period).astype(float).ffill()
        self.df['RSI'] = talib.RSI(self.df['Close'], timeperiod=self.rsi_period).astype(float).ffill()

        self.df['K'] = self._STOCHK(self.df, period=self.fastk, stoch_period=self.stoch_period).astype(float).ffill()
        self.df['D'] = self._STOCHD(self.df, period=self.fastd, column='K').astype(float).ffill()

        self.df['pivot'] = self.df.apply(lambda x: self._set_pivot_points(self.df, x.name, self.pivot_period, self.pivot_period), axis=1)
        self.df['divSignal'] = self.df.apply(lambda row: self._set_div_signal(row), axis=1)

    def _get_side(self, row):
        return 1 if float(row['Close']) > float(row['EMA']) else -1 if float(row['EMA']) > float(row['Close']) else 0

    def set_exit_signals(self, open_trade, index, row):
        if row['Has Open Position']:
            if open_trade['Side'] == 'Long':
                exit_value = 1 if row['High'] >= row['TP Price'] or row['Low'] <= row['SL Price'] else 0
                if exit_value:
                    row['Exit'] = exit_value
                    row['Exit Price'] = row['TP Price'] if row['High'] >= row['TP Price'] else row['SL Price']
                    row['Has Open Position'] = 0
            elif open_trade['Side'] == 'Short':
                exit_value = 1 if row['High'] >= row['SL Price'] or row['Low'] <= row['TP Price'] else 0
                if exit_value:
                    row['Exit'] = exit_value
                    row['Exit Price'] = row['SL Price'] if row['High'] >= row['SL Price'] else row['TP Price']
                    row['Has Open Position'] = 0
            else:
                row['Exit'] = 0
        else:
            row['Exit'] = 0

        self.df.iloc[index] = row

    def _enter_trade(self, row):
        if row['Side'] == 1:
            return 1 if self.crossover(row.name, 'K', 'D') and self._has_divergence([1, 2], row.name, self.div_lookback_period) else 0
        else:
            return 1 if self.crossover(row.name, 'D', 'K') and self._has_divergence([-1, -2], row.name, self.div_lookback_period) else 0

    def _get_stoploss_price(self, row):
        prev_index = row.name - 1 if row.name > 0 else 0

        max_values = self.df['High'].rolling(self.swing_lockback_period).max()
        min_values = self.df['Low'].rolling(self.swing_lockback_period).min()

        if bool(self.df['SL Price'].iloc[prev_index]):
            return float(self.df['SL Price'].iloc[prev_index])
        else:
            if row['Enter']:
                if row['Side'] == 1:
                    return float(min_values.iloc[row.name] * 0.99)
                else:
                    return float(max_values.iloc[row.name] * 1.01)
            else:
                return 0

    def _get_takeprofit_price(self, row):
        prev_index = row.name - 1 if row.name > 0 else 0

        if bool(self.df['TP Price'].iloc[prev_index]):
            return float(self.df['TP Price'].iloc[prev_index])
        else:
            if row['Enter']:
                if row['Side'] == 1:
                    return float(row['Close'] + self.risk_reward * (row['Close'] - row['SL Price']))
                else:
                    return float(row['Close'] - self.risk_reward * (row['SL Price'] - row['Close']))
            else:
                return 0

    def _set_pivot_points(self, df, l, n1, n2):  # n1 n2 before and after candle l
        if l - n1 < 0 or l + n2 >= len(df):
            return 0

        pividlow = 1
        pividhigh = 1
        for i in range(l - n1, l + n2 + 1):
            if (df['Close'].iloc[l] > df['Close'].iloc[i]):
                pividlow = 0
            if (df['Close'].iloc[l] < df['Close'].iloc[i]):
                pividhigh = 0
        if pividlow and pividhigh:
            return 3
        elif pividlow:
            return 1
        elif pividhigh:
            return 2
        else:
            return 0

    def bull_hidden_divergences(self, candleid, pl_index):
        arrived = False
        previous_candle = candleid - self.trigger_candle
        array_filter = pl_index < previous_candle
        filtered_pl_index = pl_index[array_filter]
        end = min(self.max_pivot + 1, len(filtered_pl_index) + 1)
        virtual_line_start = previous_candle - 1
        if self.df['RSI'].iloc[candleid] > self.df['RSI'].iloc[previous_candle] or self.df['Close'].iloc[candleid] > self.df['Close'].iloc[previous_candle]:
            for x in range(-1, -end, -1):
                lenght = candleid - filtered_pl_index[x] + self.pivot_period
                if filtered_pl_index[x] == 0 or lenght > self.div_max_candles:
                    continue
                if lenght > 5 and \
                        self.df['RSI'].iloc[previous_candle] < self.df['RSI'].iloc[filtered_pl_index[x]] and self.df['Close'].iloc[previous_candle] > self.df['Close'].iloc[filtered_pl_index[x]]:
                    slope1 = (self.df['RSI'].iloc[previous_candle] - self.df['RSI'].iloc[filtered_pl_index[x]]) / (previous_candle - filtered_pl_index[x])
                    virtual_line1 = self.df['RSI'].iloc[previous_candle] - slope1
                    slope2 = (self.df['Close'].iloc[previous_candle] - self.df['Close'].iloc[filtered_pl_index[x]]) / (previous_candle - filtered_pl_index[x])
                    virtual_line2 = self.df['Low'].iloc[previous_candle] - slope2
                    arrived = True
                    for y in range(virtual_line_start, filtered_pl_index[x] + 1, -1):
                        if self.df['RSI'].iloc[y] < virtual_line1 or self.df['Close'].iloc[y] < virtual_line2:
                            arrived = False
                            break
                        virtual_line1 -= slope1
                        virtual_line2 -= slope2

        return arrived

    def bull_regular_divergences(self, candleid, pl_index):
        arrived = False
        previous_candle = candleid - self.trigger_candle
        array_filter = pl_index < previous_candle
        filtered_pl_index = pl_index[array_filter]
        end = min(self.max_pivot + 1, len(filtered_pl_index) + 1)
        virtual_line_start = previous_candle - 1

        if self.df['RSI'].iloc[candleid] > self.df['RSI'].iloc[previous_candle] or self.df['Close'].iloc[candleid] > self.df['Close'].iloc[previous_candle]:
            for x in range(-1, -end, -1):
                lenght = candleid - filtered_pl_index[x] + self.pivot_period
                if filtered_pl_index[x] == 0 or lenght > self.div_max_candles:
                    continue
                if lenght > 5 and \
                        self.df['RSI'].iloc[previous_candle] > self.df['RSI'].iloc[filtered_pl_index[x]] and self.df['Close'].iloc[previous_candle] < self.df['Close'].iloc[filtered_pl_index[x]]:
                    slope1 = (self.df['RSI'].iloc[previous_candle] - self.df['RSI'].iloc[filtered_pl_index[x]]) / (previous_candle - filtered_pl_index[x])
                    virtual_line1 = self.df['RSI'].iloc[previous_candle] - slope1
                    slope2 = (self.df['Close'].iloc[previous_candle] - self.df['Close'].iloc[filtered_pl_index[x]]) / (previous_candle - filtered_pl_index[x])
                    virtual_line2 = self.df['Low'].iloc[previous_candle] - slope2
                    arrived = True
                    for y in range(virtual_line_start, filtered_pl_index[x] + 1, -1):
                        if self.df['RSI'].iloc[y] < virtual_line1 or self.df['Close'].iloc[y] < virtual_line2:
                            arrived = False
                            break
                        virtual_line1 -= slope1
                        virtual_line2 -= slope2

        return arrived

    def bear_hidden_divergences(self, candleid, ph_index):
        arrived = False
        previous_candle = candleid - self.trigger_candle
        array_filter = ph_index < previous_candle
        filtered_ph_index = ph_index[array_filter]
        end = min(self.max_pivot + 1, len(filtered_ph_index) + 1)
        virtual_line_start = previous_candle - 1
        if self.df['RSI'].iloc[candleid] < self.df['RSI'].iloc[previous_candle] or self.df['Close'].iloc[candleid] < self.df['Close'].iloc[previous_candle]:
            for x in range(-1, -end, -1):
                lenght = candleid - filtered_ph_index[x] + self.pivot_period
                if filtered_ph_index[x] == 0 or lenght > self.div_max_candles:
                    continue
                if lenght > 5 and \
                        self.df['RSI'].iloc[previous_candle] > self.df['RSI'].iloc[filtered_ph_index[x]] and self.df['Close'].iloc[previous_candle] < self.df['Close'].iloc[filtered_ph_index[x]]:
                    slope1 = (self.df['RSI'].iloc[previous_candle] - self.df['RSI'].iloc[filtered_ph_index[x]]) / (previous_candle - filtered_ph_index[x])
                    virtual_line1 = self.df['RSI'].iloc[previous_candle] - slope1
                    slope2 = (self.df['Close'].iloc[previous_candle] - self.df['Close'].iloc[filtered_ph_index[x]]) / (previous_candle - filtered_ph_index[x])
                    virtual_line2 = self.df['High'].iloc[previous_candle] - slope2
                    arrived = True
                    for y in range(virtual_line_start, filtered_ph_index[x] + 1, -1):
                        if self.df['RSI'].iloc[y] > virtual_line1 or self.df['Close'].iloc[y] > virtual_line2:
                            arrived = False
                            break
                        virtual_line1 -= slope1
                        virtual_line2 -= slope2

        return arrived

    def bear_regular_divergences(self, candleid, ph_index):
        arrived = False
        previous_candle = candleid - self.trigger_candle
        array_filter = ph_index < previous_candle
        filtered_ph_index = ph_index[array_filter]
        end = min(self.max_pivot + 1, len(filtered_ph_index) + 1)
        virtual_line_start = previous_candle - 1
        if self.df['RSI'].iloc[candleid] < self.df['RSI'].iloc[previous_candle] or self.df['Close'].iloc[candleid] < self.df['Close'].iloc[previous_candle]:
            for x in range(-1, -end, -1):
                lenght = candleid - filtered_ph_index[x] + self.pivot_period
                if filtered_ph_index[x] == 0 or lenght > self.div_max_candles:
                    continue
                if lenght > 5 and \
                        self.df['RSI'].iloc[previous_candle] < self.df['RSI'].iloc[filtered_ph_index[x]] and self.df['Close'].iloc[previous_candle] > self.df['Close'].iloc[filtered_ph_index[x]]:
                    slope1 = (self.df['RSI'].iloc[previous_candle] - self.df['RSI'].iloc[filtered_ph_index[x]]) / (previous_candle - filtered_ph_index[x])
                    virtual_line1 = self.df['RSI'].iloc[previous_candle] - slope1
                    slope2 = (self.df['Close'].iloc[previous_candle] - self.df['Close'].iloc[filtered_ph_index[x]]) / (previous_candle - filtered_ph_index[x])
                    virtual_line2 = self.df['High'].iloc[previous_candle] - slope2
                    arrived = True
                    for y in range(virtual_line_start, filtered_ph_index[x] + 1, -1):
                        if self.df['RSI'].iloc[y] > virtual_line1 or self.df['Close'].iloc[y] > virtual_line2:
                            arrived = False
                            break
                        virtual_line1 -= slope1
                        virtual_line2 -= slope2

        return arrived

    def _set_div_signal(self, x):
        candleid = int(x.name)

        pl_index = self.df.index[self.df["pivot"] == 1][-20:]
        ph_index = self.df.index[self.df["pivot"] == 2][-20:]

        if self.df['pivot'].iloc[candleid - self.trigger_candle] in (1, 2, -1, -2):
            is_hidden_bull_div = self.bull_hidden_divergences(candleid, pl_index)
            is_regular_bull_div = self.bull_regular_divergences(candleid, pl_index)
            is_hidden_bear_div = self.bear_hidden_divergences(candleid, ph_index)
            is_regular_bear_div = self.bear_regular_divergences(candleid, ph_index)

            return 1 if is_hidden_bull_div else 2 if is_regular_bull_div else -1 if is_hidden_bear_div else -2 if is_regular_bear_div else 0
        else:
            return 0

    def _has_divergence(self, div_sides, row_index, div_lookback_period):
        for index in range(row_index, row_index - div_lookback_period):
            if self.df['divSignal'].iloc[index] in div_sides:
                return True

        return False

    def _STOCH(self, ohlc, column='Close', period: int = 14):

        highest_high = ohlc[column].rolling(center=False, window=period).max() if column != 'Close' else ohlc['High'].rolling(center=False, window=period).max()
        lowest_low = ohlc[column].rolling(center=False, window=period).min() if column != 'Close' else ohlc['Low'].rolling(center=False, window=period).max()

        STOCH = pd.Series(
            (ohlc[column] - lowest_low) / (highest_high - lowest_low) * 100,
            name="{0} period STOCH %K".format(period),
        )

        return STOCH

    def _STOCHK(self, ohlc, period: int = 3, stoch_period: int = 14):
        return pd.Series(
            self._STOCH(ohlc, column='RSI', period=stoch_period).rolling(center=False, window=period).mean(),
            name="{0} period STOCH %K.".format(period),
        )

    def _STOCHD(self, ohlc, column='K', period: int = 3):
        return pd.Series(
            ohlc[column].rolling(center=False, window=period).mean(),
            name="{0} period STOCH %D.".format(period),
        )