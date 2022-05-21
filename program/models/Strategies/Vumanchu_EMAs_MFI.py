import pandas as pd
import talib

from program.models.Strategies.Strategy import Strategy

class VumanchuEmasMfi(Strategy):
    def __init__(self, symbol, timeframe, atr_multiplier=1.5, rr=2):
        super(VumanchuEmasMfi, self).__init__(symbol, timeframe, atr_multiplier, rr)

        self.name = '50/200-EMA\'s + Wavetrend + MFI Strategy (Trade Pro)'
        self.short_name = 'Multi_EMA_Vumanchu_MFI'
        self.long_ema_period = 200
        self.short_ema_period = 50

        self.mfi_period = 60
        self.mfi_multiplier = 150
        self.mfi_posY = 2.5

        self.wt_channel_lenght = 9
        self.wt_average_lenght = 12
        self.wt_ma_lenght = 3

        self.zero_line = 0

        self.swing_lockback_period = 10
        self.pullback_period = 15

    def set_indicators(self):
        self.df = self.df.loc[self.df.notnull().all(axis=1).argmax():]
        self.df.reset_index(inplace=True)

        self.df['Long EMA'] = talib.EMA(self.df['Close'], timeperiod=self.long_ema_period).astype(float).ffill()
        self.df['Short EMA'] = talib.EMA(self.df['Close'], timeperiod=self.short_ema_period).astype(float).ffill()
        self.df['ATR'] = talib.ATR(self.df['High'], self.df['Low'], self.df['Close'], timeperiod=self.atr_period).astype(float).ffill()
        self.df['WT1'] = self._set_wavetrend(1).astype(float).ffill()
        self.df['WT2'] = self._set_wavetrend(2).astype(float).ffill()
        self.df['MFI'] = self._set_MFI().astype(float).ffill()

        self.df['CrossUp'] = self.df.apply(lambda row: self.crossover(row.name, 'WT1', 'WT2'), axis=1).fillna(0).astype(int)
        self.df['CrossDown'] = self.df.apply(lambda row: self.crossover(row.name, 'WT2', 'WT1'), axis=1).fillna(0).astype(int)

    def _get_side(self, row):
        return 1 if float(row['Close']) > float(row['Short EMA']) > float(row['Long EMA']) else -1 if float(row['Long EMA']) > float(row['Short EMA']) > float(row['Close']) else 0

    def _enter_trade(self, row):
        if row['Side'] == 1:
            # return 1 if row['CrossUp'] == 1 and row['WT2'] < self.zero_line and row['MFI'] > 0 else 0
            return 1 if row['CrossUp'] == 1 and row['MFI'] > 0 and row['WT2'] < self.zero_line and self._check_pullback(row) else 0
        else:
            # return 1 if row['CrossDown'] == 1 and row['WT2'] > self.zero_line and row['MFI'] < 0 else 0
            return 1 if row['CrossDown'] == 1 and row['MFI'] < 0 and row['WT2'] > self.zero_line and self._check_pullback(row) else 0

    def _get_stoploss_price(self, row):
        prev_index = row.name - 1 if row.name > 0 else 0

        # Todo: Look at the charts and use ATR OR Swing High/Low, not both
        max_values = self.df['High'].rolling(self.swing_lockback_period).max()
        min_values = self.df['Low'].rolling(self.swing_lockback_period).min()

        if bool(self.df['SL Price'].iloc[prev_index]):
            return float(self.df['SL Price'].iloc[prev_index])
        else:
            if row['Enter']:
                if row['Side'] == 1:
                    return float(min_values.iloc[row.name] - (float(row['ATR']) * self.atr_multiplier))
                else:
                    return float(max_values.iloc[row.name] + (float(row['ATR']) * self.atr_multiplier))
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

    def _set_wavetrend(self, wtType):
        source = ((self.df['High'] + self.df['Low'] + self.df['Close']) / 3)
        esa = talib.EMA(source, timeperiod=self.wt_channel_lenght)
        de = talib.EMA(abs(source - esa), timeperiod=self.wt_channel_lenght)
        ci = (source - esa) / (0.015 * de)
        wt1 = talib.EMA(ci, self.wt_average_lenght)
        if wtType == 1:
            return pd.Series(wt1)
        elif wtType == 2:
            wt2 = talib.SMA(wt1, self.wt_ma_lenght, )
            return pd.Series(wt2)

    def _set_MFI(self):
        source = (((self.df['Close'] - self.df['Open']) / (self.df['High'] - self.df['Low'])) * self.mfi_multiplier).astype(float).ffill()
        mfi = talib.SMA(source, self.mfi_period) - self.mfi_posY

        return mfi

    def _check_pullback(self, row):
        start_index = row.name - self.pullback_period
        last_pullback_data = self.df.iloc[start_index:row.name]

        if row['Side'] == 1:
            trend_rows = last_pullback_data[last_pullback_data['Side'] == 1]
            pullback_rows = last_pullback_data[last_pullback_data['Side'] == 0]

            if trend_rows.size != 0 and pullback_rows.size != 0 and trend_rows.index.min() < pullback_rows.index.max():
                return True
            else:
                return False
        elif row['Side'] == -1:
            trend_rows = last_pullback_data[last_pullback_data['Side'] == -1]
            pullback_rows = last_pullback_data[last_pullback_data['Side'] == 0]

            if trend_rows.size != 0 and pullback_rows.size != 0 and trend_rows.index.min() < pullback_rows.index.max():
                return True
            else:
                return False
        else:
            return False
