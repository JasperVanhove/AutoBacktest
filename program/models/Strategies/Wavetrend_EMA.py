import pandas as pd
import talib

from program.models.Strategies.Strategy import Strategy

class WavetrendEMA(Strategy):
    def __init__(self, symbol, timeframe, atr_multiplier=1.5, rr=2):
        super(WavetrendEMA, self).__init__(symbol, timeframe, atr_multiplier, rr)

        self.name = '200-EMA + Wavetrend Strategy'
        self.short_name = 'EMA_Wavetrend'

        self.ema_period = 200

        self.wt_channel_lenght = 9
        self.wt_average_lenght = 12
        self.wt_ma_lenght = 3
        self.wt_overbought = 10
        self.wt_oversold = -10

        self.zero_line = 0

        self.swing_lockback_period = 10

    def set_indicators(self):
        self.df = self.df.loc[self.df.notnull().all(axis=1).argmax():]
        self.df.reset_index(inplace=True)

        self.df['EMA'] = talib.EMA(self.df['Close'], timeperiod=self.ema_period).astype(float).ffill()
        self.df['ATR'] = talib.ATR(self.df['High'], self.df['Low'], self.df['Close'], timeperiod=self.atr_period).astype(float).ffill()
        self.df['WT1'] = self._set_wavetrend(self.wt_channel_lenght, self.wt_average_lenght, self.wt_ma_lenght, 1)
        self.df['WT2'] = self._set_wavetrend(self.wt_channel_lenght, self.wt_average_lenght, self.wt_ma_lenght, 2)

        self.df['CrossUp'] = self.df.apply(lambda row: self.crossover(row.name, 'WT1', 'WT2'), axis=1).fillna(0).astype(int)
        self.df['CrossDown'] = self.df.apply(lambda row: self.crossover(row.name, 'WT2', 'WT1'), axis=1).fillna(0).astype(int)

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
                    row['TP Price'] = 0
                    row['SL Price'] = 0
            elif open_trade['Side'] == 'Short':
                exit_value = 1 if row['High'] >= row['SL Price'] or row['Low'] <= row['TP Price'] else 0
                if exit_value:
                    row['Exit'] = exit_value
                    row['Exit Price'] = row['SL Price'] if row['High'] >= row['SL Price'] else row['TP Price']
                    row['Has Open Position'] = 0
                    row['TP Price'] = 0
                    row['SL Price'] = 0
            else:
                row['Exit'] = 0
        else:
            row['Exit'] = 0

        self.df.iloc[index] = row

    def _enter_trade(self, row):
        if row['Side'] == 1:
            return 1 if row['CrossUp'] == 1 and row['WT2'] <= self.wt_oversold else 0
        else:
            return 1 if row['CrossDown'] == 1 and row['WT1'] >= self.wt_overbought else 0

    def _get_stoploss_price(self, row):
        prev_index = row.name - 1 if row.name > 0 else 0

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

    def _set_wavetrend(self, channelLenght, avg, MAlenght, wtType):
        source = ((self.df['High'] + self.df['Low'] + self.df['Close']) / 3)
        esa = talib.EMA(source, timeperiod=channelLenght)
        de = talib.EMA(abs(source - esa), timeperiod=channelLenght)
        ci = (source - esa) / (0.015 * de)
        wt1 = talib.EMA(ci, avg)
        if wtType == 1:
            return pd.Series(wt1)
        elif wtType == 2:
            wt2 = talib.SMA(wt1, MAlenght)
            return pd.Series(wt2)
