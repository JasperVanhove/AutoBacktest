import talib

from program.models.Strategies.Strategy import Strategy


class DoubleEmaMacdCross(Strategy):
    def __init__(self, symbol, timeframe, atr_multiplier=3, rr=3):
        super(DoubleEmaMacdCross, self).__init__(symbol, timeframe, atr_multiplier, rr)

        self.name = '20/50-EMAs + MACD Strategy'
        self.short_name = 'Double EMA-MACD'

        self.long_ema_period = 50
        self.short_ema_period = 20

        self.MACD_fast_period = 12
        self.MACD_slow_period = 26

        self.pullback_period = 15
        self.zero_line = 0

    def set_indicators(self):
        self.df = self.df.loc[self.df.notnull().all(axis=1).argmax():]
        self.df.reset_index(inplace=True)

        self.df['LongEMA'] = talib.EMA(self.df['Close'], timeperiod=self.long_ema_period).astype(float).ffill()
        self.df['ShortEMA'] = talib.EMA(self.df['Close'], timeperiod=self.short_ema_period).astype(float).ffill()

        self.df['ATR'] = talib.ATR(self.df['High'], self.df['Low'], self.df['Close'], timeperiod=self.atr_period).astype(float).ffill()

        self.df['MACD Line'], self.df['MACD Signal'], self.df['MACD Histogram'] = talib.MACD(self.df['Close'], self.MACD_fast_period, self.MACD_slow_period, 9)

    def _get_side(self, row):
        return 1 if float(row['Close']) > float(row['ShortEMA']) > float(row['LongEMA']) else -1 if float(row['LongEMA']) > float(row['ShortEMA']) > float(row['Close']) else 0

    def _enter_trade(self, row):
        return 1 if self._check_pullback(row) and self._check_histogram_crossover(row) else 0

    def _get_stoploss_price(self, row):
        prev_index = row.name - 1 if row.name > 0 else 0

        if bool(self.df['SL Price'].iloc[prev_index]):
            return float(self.df['SL Price'].iloc[prev_index])
        else:
            if row['Enter']:
                if row['Side'] == 1:
                    return float(float(row['Low']) - (float(row['ATR']) * self.atr_multiplier))
                else:
                    return float(float(row['High']) + (float(row['ATR']) * self.atr_multiplier))
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

    def _check_histogram_crossover(self, row):
        current_index = row.name

        if row['Side'] == 1 and current_index > 0:
            return self.df['MACD Histogram'].iloc[current_index - 1] < self.zero_line < row['MACD Histogram']
        elif row['Side'] == -1 and current_index > 0:
            return self.df['MACD Histogram'].iloc[current_index - 1] > self.zero_line > row['MACD Histogram']
        else:
            return False
