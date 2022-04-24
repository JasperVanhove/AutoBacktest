import pandas as pd
import numpy as np
import talib

from program.models.Strategies.Strategy import Strategy


class SupertrendEmaTrailing(Strategy):
    def __init__(self, symbol, timeframe, atr_multiplier=3, rr=3):
        super(SupertrendEmaTrailing, self).__init__(symbol, timeframe, atr_multiplier, rr)

        self.name = '200-EMA + Supertrend and Trailing SL Strategy'
        self.short_name = 'Trailing Supertrend'

        self.ema_period = 200

        self.supertrend_period = 10
        self.supertrend_multiplier = 3

    def set_indicators(self):
        self.df = self.df.loc[self.df.notnull().all(axis=1).argmax():]
        self.df.reset_index(inplace=True)

        self.df['EMA'] = talib.EMA(self.df['Close'], timeperiod=self.ema_period).astype(float).ffill()
        self.df['ATR'] = talib.ATR(self.df['High'], self.df['Low'], self.df['Close'], timeperiod=self.atr_period).astype(float).ffill() * self.atr_multiplier
        self.df = self.df.join(self._set_supertrend())

        # remove first X NaN rows
        self.df = self.df.loc[199:]

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
                else:
                    row['SL Price'] = self._get_trailing_price(1, row)
            elif open_trade['Side'] == 'Short':
                exit_value = 1 if row['High'] >= row['SL Price'] or row['Low'] <= row['TP Price'] else 0
                if exit_value:
                    row['Exit'] = exit_value
                    row['Exit Price'] = row['SL Price'] if row['High'] >= row['SL Price'] else row['TP Price']
                    row['Has Open Position'] = 0
                    row['TP Price'] = 0
                    row['SL Price'] = 0
                else:
                    row['SL Price'] = self._get_trailing_price(0, row)
            else:
                row['Exit'] = 0
        else:
            row['Exit'] = 0

        self.df.iloc[index] = row

    def _enter_trade(self, row):
        if row['Side'] == 1:
            return 1 if bool(row['Supertrend']) else 0
        else:
            return 1 if not bool(row['Supertrend']) else 0

    def _get_stoploss_price(self, row):
        prev_index = row.name - 1 if row.name > 0 else 0

        if bool(self.df['SL Price'].iloc[prev_index]):
            return float(self.df['SL Price'].iloc[prev_index])
        else:
            if row['Enter']:
                if row['Side'] == 1:
                    return self._get_trailing_price(1, row)
                else:
                    return self._get_trailing_price(0, row)
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

    def _get_trailing_price(self, side, row):
        if bool(side):
            return float(row['Low'] - row['ATR']) if not bool(row['SL Price']) else max(row['SL Price'], float(row['Low'] - row['ATR']))
        else:
            return float(row['High'] + row['ATR']) if not bool(row['SL Price']) else min(row['SL Price'], float(row['High'] + row['ATR']))

    def _set_supertrend(self):
        high = self.df['High']
        low = self.df['Low']
        close = self.df['Close']

        # calculate ATR
        price_diffs = [high - low,
                       high - close.shift(),
                       close.shift() - low]
        true_range = pd.concat(price_diffs, axis=1)
        true_range = true_range.abs().max(axis=1)
        # default ATR calculation in supertrend indicator
        atr = true_range.ewm(alpha=1 / self.supertrend_period, min_periods=self.supertrend_period).mean()
        # df['atr'] = df['tr'].rolling(atr_period).mean()

        # HL2 is simply the average of high and low prices
        hl2 = (high + low) / 2
        # upperband and lowerband calculation
        # notice that final bands are set to be equal to the respective bands
        final_upperband = upperband = hl2 + (self.supertrend_multiplier * atr)
        final_lowerband = lowerband = hl2 - (self.supertrend_multiplier * atr)

        # initialize Supertrend column to True
        supertrend = [True] * len(self.df)

        for i in range(1, len(self.df.index)):
            curr, prev = i, i - 1

            # if current close price crosses above upperband
            if close[curr] > final_upperband[prev]:
                supertrend[curr] = True
            # if current close price crosses below lowerband
            elif close[curr] < final_lowerband[prev]:
                supertrend[curr] = False
            # else, the trend continues
            else:
                supertrend[curr] = supertrend[prev]

                # adjustment to the final bands
                if supertrend[curr] == True and final_lowerband[curr] < final_lowerband[prev]:
                    final_lowerband[curr] = final_lowerband[prev]
                if supertrend[curr] == False and final_upperband[curr] > final_upperband[prev]:
                    final_upperband[curr] = final_upperband[prev]

            # to remove bands according to the trend direction
            if supertrend[curr] == True:
                final_upperband[curr] = np.nan
            else:
                final_lowerband[curr] = np.nan

        return pd.DataFrame({
            'Supertrend': supertrend,
            'Final Lowerband': final_lowerband,
            'Final Upperband': final_upperband
        }, index=self.df.index)
