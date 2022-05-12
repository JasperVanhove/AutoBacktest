import csv
import warnings
from pathlib import Path

import pandas as pd
import plotly.express as px
from dateutil import relativedelta
from program.models.Strategies import Strategy

warnings.filterwarnings('ignore')
data_path = Path(__file__).parent.parent.parent / 'Data/'


class Backtest:
    def __init__(self, strategy: Strategy, starting_balance: float, risk: int, commission=0):
        super(Backtest, self).__init__()

        # TODO: Fees is contract size / price * 0.06%

        self.strategy = strategy
        self.starting_balance = starting_balance
        self.balance = starting_balance
        self.risk = risk
        self.has_open_position = False
        self.start_date = None
        self.end_date = None
        self.trades = []
        self.fees = 0
        self.commission = commission / 100

    def run(self):
        self.print_header()
        # set dataframe values
        self.strategy.set_indicators()
        self.strategy.set_columns()

        # make sure indexes pair with number of rows
        self.strategy.df = self.strategy.df.reset_index()

        self.strategy.df = self.strategy.df[:-1]

        self.start_date = self.strategy.df['Open Time'].iloc[0]
        self.end_date = self.strategy.df['Close Time'].iloc[-1]

        for index, row in self.strategy.df.iterrows():
            self.strategy.set_basic_columns(index, row)
            if not self.has_open_position:
                self.strategy.set_entry_signals(index, row)
                if row['Enter'] == 1:
                    self.open_position(row)
            else:
                self.strategy.set_exit_signals(self.trades[-1], index, row)
                if row['Exit'] == 1:
                    self.close_position(row)
                elif index == self.strategy.df.iloc[-1].name:
                    self.trades.pop()

        self.print_results()

    def print_header(self):
        print('\n')
        print('    _         _        ____             _    _            _   ')
        print('   / \  _   _| |_ ___ | __ )  __ _  ___| | _| |_ ___  ___| |_ ')
        print('  / _ \| | | | __/ _ \|  _ \ / _` |/ __| |/ / __/ _ \/ __| __|')
        print(' / ___ \ |_| | || (_) | |_) | (_| | (__|   <| ||  __/\__ \ |_')
        print('/_/   \_\__,_|\__\___/|____/ \__,_|\___|_|\_\\__\___||___/\__|')
        print('\n')
        print("\nBeginning new backtest for {} on {} timeframe using {} ({}:1 Risk/Reward - Atr: {}).".format(self.strategy.symbol, self.strategy.tf, self.strategy.name, self.strategy.risk_reward, self.strategy.atr_multiplier))

    def print_header_to_file(self):
        with open(data_path / f'Strategy_Results/{self.strategy.symbol}_{self.strategy.tf}_{self.strategy.short_name}_{self.strategy.risk_reward}RR_{self.strategy.atr_multiplier}ATR.txt', 'w') as f:
            f.write('\n')
            f.write('    _         _        ____             _    _            _   \n')
            f.write('   / \  _   _| |_ ___ | __ )  __ _  ___| | _| |_ ___  ___| |_ \n')
            f.write('  / _ \| | | | __/ _ \|  _ \ / _` |/ __| |/ / __/ _ \/ __| __|\n')
            f.write(' / ___ \ |_| | || (_) | |_) | (_| | (__|   <| ||  __/\__ \ |_\n')
            f.write('/_/   \_\__,_|\__\___/|____/ \__,_|\___|_|\_\\__\___||___/\__|\n')
            f.write('\n')
            f.write("\nBeginning new backtest for {} on {} timeframe using {} ({}:1 Risk/Reward - Atr: {}).\n".format(self.strategy.symbol, self.strategy.tf, self.strategy.name, self.strategy.risk_reward, self.strategy.atr_multiplier))

    def open_position(self, row):
        self.has_open_position = True
        quantity = self._get_trade_size(row)
        trading_fee = quantity * self.commission * 3  # 3X The fee amount: Entry, SL and TP order
        self.fees += trading_fee
        self.balance -= trading_fee

        self.trades.append({
            'Open Time': row['Open Time'],
            'Side': 'Long' if row['Side'] == 1 else 'Short',
            'Price': row['Entry Price'],
            'Take Profit': row['TP Price'],
            'Stop Loss': row['SL Price'],
            'Size': quantity
        })

    def close_position(self, row):
        self.has_open_position = False
        latest_position = self.trades[-1]
        close_price = row['Exit Price'] or row['Close']

        if latest_position['Side'] == 'Long':
            return_perc = (close_price - latest_position['Price']) / latest_position['Price']
            if close_price > latest_position['Price']:
                return_amount = return_perc * latest_position['Size']
                latest_position['Return'] = return_amount
                latest_position['Return Perc'] = return_perc
                latest_position['Outcome'] = '+'
                self.balance += return_amount
            elif close_price < latest_position['Price']:
                return_amount = return_perc * latest_position['Size']
                latest_position['Return'] = return_amount
                latest_position['Return Perc'] = return_perc
                latest_position['Outcome'] = '-'
                self.balance += return_amount
            else:
                latest_position['Outcome'] = '0'
                latest_position['Return Perc'] = 0
                latest_position['Return'] = 0
        elif latest_position['Side'] == 'Short':
            return_perc = (latest_position['Price'] - close_price) / latest_position['Price']
            if close_price > latest_position['Price']:
                return_amount = return_perc * latest_position['Size']
                latest_position['Return'] = return_amount
                latest_position['Return Perc'] = return_perc
                latest_position['Outcome'] = '-'
                self.balance += return_amount
            elif close_price < latest_position['Price']:
                return_amount = return_perc * latest_position['Size']
                latest_position['Return'] = return_amount
                latest_position['Return Perc'] = return_perc
                latest_position['Outcome'] = '+'
                self.balance += return_amount
            else:
                latest_position['Outcome'] = '0'
                latest_position['Return Perc'] = 0
                latest_position['Return'] = 0
        else:
            raise Exception('No position side was defined')

        latest_position['Close Price'] = close_price
        latest_position['Close Time'] = row['Close Time']
        latest_position['Balance'] = self.balance
        self.trades[-1] = latest_position

    def print_results(self):
        # Todo: Add extra result like avg trade duration
        # Todo: Put all the results in dictionary and use this to print/export
        if self.balance <= self.starting_balance:
            print('\n')
            print('\n')
            print('No positive Balance!')
            print('\n')
            print('\n')
            return

        self.print_header_to_file()

        abs_return = self.balance - self.starting_balance
        pc_return = 100 * abs_return / self.starting_balance
        amount_of_trades = len(self.trades)

        date_diff = relativedelta.relativedelta(self.end_date, self.start_date)
        months_diff = (date_diff.years * 12) + date_diff.months

        avg_monthly_return = pc_return / months_diff

        if amount_of_trades > 50 and avg_monthly_return >= 3.0:
            winning_trades = [trade for trade in self.trades if trade['Outcome'] == '+']
            losing_trades = [trade for trade in self.trades if trade['Outcome'] == '-']
            break_even_trades = [trade for trade in self.trades if trade['Outcome'] == '0']

            long_trades = [trade for trade in self.trades if trade['Side'] == 'Long']
            short_trades = [trade for trade in self.trades if trade['Side'] == 'Short']

            pc_win = 100 * len(winning_trades) / amount_of_trades
            pc_loss = 100 * len(losing_trades) / amount_of_trades
            pc_breakeven = 100 * len(break_even_trades) / amount_of_trades

            trades_df = self._create_dataframe_from_list(self.trades)
            wins_df = self._create_dataframe_from_list(winning_trades)
            loss_df = self._create_dataframe_from_list(losing_trades)
            long_df = self._create_dataframe_from_list(long_trades)
            short_df = self._create_dataframe_from_list(short_trades)

            self._write_equity_dataframe_to_file(trades_df)

            max_win = wins_df['Returns'].max()
            avg_win = wins_df['Returns'].mean()
            max_loss = loss_df['Returns'].min()
            avg_loss = loss_df['Returns'].min()

            grouper = (trades_df.Outcome != trades_df.Outcome.shift()).cumsum()
            longest_win_streak = trades_df.groupby(grouper).cumcount().max()  # Todo: Calculate this with a method

            profit_factor = wins_df['Returns'].sum() / abs(loss_df['Returns'].sum())

            peaks = trades_df['Equity'].cummax()
            drawdowns = (trades_df['Equity'] - peaks) / peaks
            max_drawdown_perc = min(drawdowns)
            #
            # data_df = pd.DataFrame.from_dict({'Date': trades_df['Time'].dt.normalize(), 'Daily Results Perc': trades_df['Return Perc'], 'Daily Results': trades_df['Returns']})
            # data_df.groupby(['Date']).sum()
            # all_dates = pd.DataFrame.from_dict({'Date': self.strategy.df['Open Time'].dt.normalize().drop_duplicates(), 'Daily Results Perc': 0, 'Daily Results': 0})
            #
            # df = pd.concat([data_df, all_dates])
            # daily_results = df.groupby(['Date']).sum()
            # daily_results['Date'] = daily_results.index

            with open(data_path / f'Strategy_Results/{self.strategy.symbol}_{self.strategy.tf}_{self.strategy.short_name}_{self.strategy.risk_reward}RR_{self.strategy.atr_multiplier}ATR.txt', 'a') as f:

                f.write("\n---------------------------------------------------\n")
                f.write("                 Backtest Results\n")
                f.write("---------------------------------------------------\n")
                f.write("Start date:              {}\n".format(self.start_date))
                f.write("End date:                {}\n".format(self.end_date))
                f.write("Starting balance:        ${}\n".format(round(self.starting_balance, 2)))
                f.write("Ending balance:          ${}\n".format(round(self.balance, 2)))
                f.write("Total return:            ${} ({}%)\n".format(round(abs_return, 2),
                                                                      round(pc_return, 1)))

                f.write("Instrument traded: {}\n".format(self.strategy.symbol))
                if self.commission:
                    f.write("Total fees:              ${}\n".format(round(self.fees, 3)))
                f.write("Total no. trades:        {}\n".format(amount_of_trades))
                f.write("Backtest win rate:       {}%\n".format(round(pc_win, 1)))
                f.write("Backtest loss rate:       {}%\n".format(round(pc_loss, 1)))
                if pc_breakeven:
                    f.write("\nInstrument breakeven rate (%):      {}\n".format(round(pc_breakeven, 1)))

                f.write("")

                f.write("Maximum drawdown:        {}%\n".format(round(max_drawdown_perc * 100, 2)))
                f.write("Profit Factor:            {}\n".format(round(profit_factor, 2)))
                f.write("Avg. Monthly Return Perc: {}%\n".format(round(avg_monthly_return, 2)))
                f.write("Max win:                 ${}\n".format(round(max_win, 2)))
                f.write("Average win:             ${}\n".format(round(avg_win, 2)))
                f.write("Max loss:                -${}\n".format(round(abs(max_loss), 2)))
                f.write("Average loss:            -${}\n".format(round(abs(avg_loss), 2)))
                f.write("Longest win streak:      {} trades\n".format(longest_win_streak))
                # f.write("Longest losing streak:   {} trades\n".format(longest_lose_streak))
                # f.write("Average trade duration:  {}\n".format(backtest_results['all_trades']['avg_trade_duration']))
                if len(long_trades) > 0:
                    losing_long_trades = [trade for trade in long_trades if trade['Outcome'] == '-']
                    winning_long_trades = [trade for trade in long_trades if trade['Outcome'] == '+']

                    long_win_df = self._create_dataframe_from_list(winning_long_trades)
                    long_loss_df = self._create_dataframe_from_list(losing_long_trades)

                    pc_loss_long = 100 * len(losing_long_trades) / len(long_trades)
                    pc_win_long = 100 * len(winning_long_trades) / len(long_trades)

                    max_long_win = long_win_df['Returns'].max()
                    avg_long_win = long_win_df['Returns'].mean()
                    max_long_loss = long_loss_df['Returns'].min()
                    avg_long_loss = long_loss_df['Returns'].min()

                    grouper = (long_df.Outcome != long_df.Outcome.shift()).cumsum()
                    longest_long_win_streak = long_df.groupby(grouper).cumcount().max()  # Todo: Calculate this with a method

                    f.write("\n            Summary of long trades\n")
                    f.write("----------------------------------------------\n")
                    f.write("Number of long trades:   {}\n".format(len(long_trades)))
                    f.write("Long win rate:           {}%\n".format(round(pc_win_long, 1)))
                    f.write("Long loss rate:           {}%\n".format(round(pc_loss_long, 1)))
                    f.write("Max win:                 ${}\n".format(round(max_long_win, 2)))
                    f.write("Average win:             ${}\n".format(round(avg_long_win, 2)))
                    f.write("Max loss:                -${}\n".format(round(abs(max_long_loss), 2)))
                    f.write("Average loss:            -${}\n".format(round(abs(avg_long_loss), 2)))
                    f.write("Longest win streak:      {} trades\n".format(longest_long_win_streak))
                else:
                    f.write("There were no long trades.\n")

                if len(short_trades) > 0:
                    winning_short_trades = [trade for trade in short_trades if trade['Outcome'] == '+']
                    losing_short_trades = [trade for trade in short_trades if trade['Outcome'] == '-']

                    short_win_df = self._create_dataframe_from_list(winning_short_trades)
                    short_loss_df = self._create_dataframe_from_list(losing_short_trades)

                    pc_win_short = 100 * len(winning_short_trades) / len(short_trades)
                    pc_loss_short = 100 * len(losing_short_trades) / len(short_trades)

                    max_short_win = short_win_df['Returns'].max()
                    avg_short_win = short_win_df['Returns'].mean()
                    max_short_loss = short_loss_df['Returns'].min()
                    avg_short_loss = short_loss_df['Returns'].min()

                    grouper = (short_df.Outcome != short_df.Outcome.shift()).cumsum()
                    longest_short_win_streak = short_df.groupby(grouper).cumcount().max()

                    f.write("\n            Summary of short trades\n")
                    f.write("----------------------------------------------\n")
                    f.write("Number of short trades:   {}\n".format(len(short_trades)))
                    f.write("Short win rate:           {}%\n".format(round(pc_win_short, 1)))
                    f.write("Short loss rate:           {}%\n".format(round(pc_loss_short, 1)))
                    f.write("Max win:                 ${}\n".format(round(max_short_win, 2)))
                    f.write("Average win:             ${}\n".format(round(avg_short_win, 2)))
                    f.write("Max loss:                -${}\n".format(round(abs(max_short_loss), 2)))
                    f.write("Average loss:            -${}\n".format(round(abs(avg_short_loss), 2)))
                    f.write("Longest win streak:      {} trades\n".format(longest_short_win_streak))
                else:
                    f.write("There were no short trades.\n")

            self._export_trades_to_csv()
        else:
            with open(data_path / f'Strategy_Results/{self.strategy.symbol}_{self.strategy.tf}_{self.strategy.short_name}_{self.strategy.risk_reward}RR_{self.strategy.atr_multiplier}ATR.txt', 'a') as f:
                f.write('No trades taken.\n')
                f.write(f'\n')

    def _export_trades_to_csv(self):
        csv_columns = self.trades[0].keys()

        try:
            with open(data_path / f'Trade_Data/{self.strategy.symbol}_{self.strategy.tf}_{self.strategy.short_name}_{self.strategy.risk_reward}RR_{self.strategy.atr_multiplier}ATR.csv', 'w') as d:
                writer = csv.DictWriter(d, fieldnames=csv_columns)
                writer.writeheader()
                for trade in self.trades:
                    writer.writerow(trade)
        except IOError:
            print("I/O error")

    def _create_dataframe_from_list(self, trade_list):
        time_array = [trade['Open Time'] for trade in trade_list]
        balance_array = [trade['Balance'] for trade in trade_list]
        returns_array = [trade['Return'] for trade in trade_list]
        returns_perc_array = [trade['Return Perc'] for trade in trade_list]
        close_time_array = [trade['Close Time'] for trade in trade_list]
        outcome_array = [trade['Outcome'] for trade in trade_list]

        df = pd.DataFrame.from_dict({'Time': time_array, 'Equity': balance_array, 'Returns': returns_array, 'Return Perc': returns_perc_array, 'Close Time': close_time_array, 'Outcome': outcome_array})

        df['Time'] = pd.to_datetime(df['Time'], format='%Y-%m-%d')
        df['Equity'] = df['Equity'].astype(float)
        df['Returns'] = df['Returns'].astype(float)
        df['Close Time'] = pd.to_datetime(df['Close Time'], format='%Y-%m-%d')
        df['Outcome'] = df['Outcome'].astype(str)

        return df

    def _get_trade_size(self, row):
        loss_perc = abs(row['Entry Price'] - row['SL Price']) / row['Entry Price']
        risk_amount = self.balance * (self.risk / 100)
        return risk_amount / loss_perc

    def _write_equity_dataframe_to_file(self, equity_df):
        fig = px.line(equity_df, x="Time", y="Equity", title=f"{self.strategy.symbol} on {self.strategy.tf} using {self.strategy.name}.")
        fig.write_image(data_path / f'Equity_Curves/{self.strategy.symbol}_{self.strategy.tf}_{self.strategy.short_name}_{self.strategy.risk_reward}RR_{self.strategy.atr_multiplier}ATR.pdf')
