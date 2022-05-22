import os
from pathlib import Path

import pandas as pd
import numpy as np
import talib as talib
from dotenv import load_dotenv


class Strategy:
    def __init__(self, symbol, timeframe, atr_multiplier=1.5, rr=2):
        load_dotenv()

        self.name = 'Base Strategy'
        self.short_name = 'Base'
        self.symbol = symbol
        self.tf = timeframe

        self.atr_period = 14
        self.atr_multiplier = atr_multiplier

        self.risk_reward = rr

        self.df = self._get_candle_data()

    def set_indicators(self):
        raise NotImplementedError()

    def set_basic_columns(self, index, row):
        row['Has Open Position'] = self._has_open_position(index)
        row['SL Price'] = self.df['SL Price'].iloc[index - 1 if index > 0 else 0]
        row['TP Price'] = self.df['TP Price'].iloc[index - 1 if index > 0 else 0]

        self.df.iloc[index] = row

    def add_equity(self, index, row, equity):
        row['Equity'] = equity

        self.df.iloc[index] = row

    def set_columns(self):
        self.df = self.df.append({
            'Side': 0,
            'Enter': 0,
            'Has Open Position': 0,
            'Entry Price': 0,
            'SL Price': 0,
            'TP Price': 0,
            'Exit': 0,
            'Exit Price': 0,
            'Equity': 0
        }, ignore_index=True)

        self.df['Exit'] = self.df['Exit'].fillna(0).astype(int)
        self.df['Enter'] = self.df['Enter'].fillna(0).astype(int)
        self.df['Has Open Position'] = self.df['Has Open Position'].fillna(0).astype(int)
        self.df['Entry Price'] = self.df['Entry Price'].fillna(0.0).astype(float)
        self.df['SL Price'] = self.df['SL Price'].fillna(0.0).astype(float)
        self.df['TP Price'] = self.df['TP Price'].fillna(0.0).astype(float)
        self.df['Exit Price'] = self.df['Exit Price'].fillna(0.0).astype(float)
        self.df['Equity'] = self.df['Equity'].fillna(0.0).astype(float)
        self.df['Side'] = self.df.apply(lambda row: self._get_side(row), axis=1).fillna(0).astype(int)

    def set_entry_signals(self, index, row):
        row['Enter'] = self._enter_trade(row)
        row['Entry Price'] = self._get_entry_price(row)
        row['SL Price'] = self._get_stoploss_price(row)
        row['TP Price'] = self._get_takeprofit_price(row)

        self.df.iloc[index] = row

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

    def _get_candle_data(self):
        path = Path(__file__).parent.parent.parent.parent / f'Historical_Data/{self.symbol}_{self.tf}.csv'
        df = pd.read_csv(path)
        df = df[df['Volume'] != 0]
        df.dropna(inplace=True)
        df.reset_index(drop=True, inplace=True)

        df = self._set_types(df)

        return df

    def _set_types(self, df):
        df['Open'] = df['Open'].astype(float)
        df['High'] = df['High'].astype(float)
        df['Low'] = df['Low'].astype(float)
        df['Close'] = df['Close'].astype(float)
        df['Volume'] = df['Volume'].astype(float)
        df['Open Time'] = pd.to_datetime(df['Open Time'], format='%Y-%m-%d')
        df['Close Time'] = pd.to_datetime(df['Close Time'], format='%Y-%m-%d')

        return df

    def _has_open_position(self, index):
        prev_index = index - 1 if index > 0 else 0
        if bool(self.df['Has Open Position'].iloc[prev_index]):
            return int(self.df['Has Open Position'].iloc[prev_index])
        else:
            return int(self.df['Enter'].iloc[prev_index] or 0)

    def _get_side(self, row):
        raise NotImplementedError()

    def _enter_trade(self, row):
        raise NotImplementedError()

    def _get_entry_price(self, row):
        return row['Close'] if row['Enter'] else 0

    def _get_stoploss_price(self, row):
        raise NotImplementedError()

    def _get_takeprofit_price(self, row):
        raise NotImplementedError()

    def crossover(self, index, param1, param2):
        # Return true if param1 crosses over param2
        return True if self.df[param1].iloc[index - 1] < self.df[param2].iloc[index - 1] and self.df[param1].iloc[index] > self.df[param2].iloc[index] else False