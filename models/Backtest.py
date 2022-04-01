import csv
import warnings

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from models.Strategies import Strategy

warnings.filterwarnings('ignore')


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
        self.commission = commission

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
        print("\nBeginning new backtest for {} on {} timeframe using {} ({}:1 Risk/Reward).".format(self.strategy.symbol, self.strategy.tf, self.strategy.name, self.strategy.risk_reward))

    def print_header_to_file(self):
        with open(f'/home/jasper/Documents/Private/Projects/AutoBacktest/Strategy_Results/{self.strategy.symbol}_{self.strategy.tf}_{self.strategy.short_name}.txt', 'w') as f:
            f.write('\n')
            f.write('    _         _        ____             _    _            _   \n')
            f.write('   / \  _   _| |_ ___ | __ )  __ _  ___| | _| |_ ___  ___| |_ \n')
            f.write('  / _ \| | | | __/ _ \|  _ \ / _` |/ __| |/ / __/ _ \/ __| __|\n')
            f.write(' / ___ \ |_| | || (_) | |_) | (_| | (__|   <| ||  __/\__ \ |_\n')
            f.write('/_/   \_\__,_|\__\___/|____/ \__,_|\___|_|\_\\__\___||___/\__|\n')
            f.write('\n')
            f.write("\nBeginning new backtest for {} on {} timeframe using {} ({}:1 Risk/Reward).\n".format(self.strategy.symbol, self.strategy.tf, self.strategy.name, self.strategy.risk_reward))

    def open_position(self, row):
        self.has_open_position = True
        quantity = self._get_trade_size(row)
        trading_fee = (quantity / row['Entry Price'] * self.commission) * 3  # 3X The fee amount: Entry, SL and TP order
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
        risk_amount = self.balance * (self.risk / 100)
        trading_fee = (latest_position['Size'] / latest_position['Price'] * self.commission) * 3  # 3X The fee amount: Entry, SL and TP order
        self.fees += trading_fee
        self.balance -= trading_fee

        if latest_position['Side'] == 'Long':
            if close_price > latest_position['Price']:
                return_amount = risk_amount * self.strategy.risk_reward
                self.balance += return_amount
                latest_position['Return'] = return_amount
                latest_position['Outcome'] = '+'
            elif close_price < latest_position['Price']:
                self.balance -= risk_amount
                latest_position['Return'] = -risk_amount
                latest_position['Outcome'] = '-'
            else:
                latest_position['Outcome'] = '0'
                latest_position['Return'] = 0
        elif latest_position['Side'] == 'Short':
            if close_price > latest_position['Price']:
                self.balance -= risk_amount
                latest_position['Return'] = -risk_amount
                latest_position['Outcome'] = '-'
            elif close_price < latest_position['Price']:
                return_amount = risk_amount * self.strategy.risk_reward
                self.balance += return_amount
                latest_position['Return'] = return_amount
                latest_position['Outcome'] = '+'
            else:
                latest_position['Outcome'] = '0'
                latest_position['Return'] = 0
        else:
            raise Exception('No position side was defined')

        latest_position['Close Price'] = close_price
        latest_position['Close Time'] = row['Close Time']
        latest_position['Balance'] = self.balance
        self.trades[-1] = latest_position

    def print_results(self):
        # Todo: Add extra result like win/loss streak, fees, drawdown, avg trade duration
        # Todo: Put all the results in dictionary and use this to print/export
        self.print_header_to_file()

        abs_return = self.balance - self.starting_balance
        pc_return = 100 * abs_return / self.starting_balance
        amount_of_trades = len(self.trades)

        if amount_of_trades > 0:
            winning_trades = [trade for trade in self.trades if trade['Outcome'] == '+']
            losing_trades = [trade for trade in self.trades if trade['Outcome'] == '-']
            break_even_trades = [trade for trade in self.trades if trade['Outcome'] == '0']

            long_trades = [trade for trade in self.trades if trade['Side'] == 'Long']
            short_trades = [trade for trade in self.trades if trade['Side'] == 'Short']

            pc_win = 100 * len(winning_trades) / amount_of_trades
            pc_loss = 100 * len(losing_trades) / amount_of_trades
            pc_breakeven = 100 * len(break_even_trades) / amount_of_trades

            equity_df = self._create_equity_dataframe()
            self._write_equity_dataframe_to_file(equity_df)

            with open(f'/home/jasper/Documents/Private/Projects/AutoBacktest/Strategy_Results/{self.strategy.symbol}_{self.strategy.tf}_{self.strategy.short_name}.txt', 'a') as f:

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

                s = (equity_df.Returns + self.starting_balance).cumprod()
                max_drawdown = np.ptp(s) / s.max()

                f.write("Maximum drawdown:        {}%\n".format(round(max_drawdown, 2)))
                # f.write("Max win:                 ${}\n".format(round(max_win, 2)))
                # f.write("Average win:             ${}\n".format(round(avg_win, 2)))
                # f.write("Max loss:                -${}\n".format(round(max_loss, 2)))
                # f.write("Average loss:            -${}\n".format(round(avg_loss, 2)))
                # f.write("Longest win streak:      {} trades\n".format(longest_win_streak))
                # f.write("Longest losing streak:   {} trades\n".format(longest_lose_streak))
                # f.write("Average trade duration:  {}\n".format(backtest_results['all_trades']['avg_trade_duration']))
                if len(long_trades) > 0:
                    losing_long_trades = [trade for trade in long_trades if trade['Outcome'] == '-']
                    winning_long_trades = [trade for trade in long_trades if trade['Outcome'] == '+']

                    pc_loss_long = 100 * len(losing_long_trades) / len(long_trades)
                    pc_win_long = 100 * len(winning_long_trades) / len(long_trades)

                    f.write("\n            Summary of long trades\n")
                    f.write("----------------------------------------------\n")
                    f.write("Number of long trades:   {}\n".format(len(long_trades)))
                    f.write("Long win rate:           {}%\n".format(round(pc_win_long, 1)))
                    f.write("Long loss rate:           {}%\n".format(round(pc_loss_long, 1)))
                    # f.write("Max win:                 ${}\n".format(round(max_long_win, 2)))
                    # f.write("Average win:             ${}\n".format(round(avg_long_win, 2)))
                    # f.write("Max loss:                -${}\n".format(round(max_long_loss, 2)))
                    # f.write("Average loss:            -${}\n".format(round(avg_long_loss, 2)))
                else:
                    f.write("There were no long trades.\n")

                if len(short_trades) > 0:
                    winning_short_trades = [trade for trade in short_trades if trade['Outcome'] == '+']
                    losing_short_trades = [trade for trade in short_trades if trade['Outcome'] == '-']

                    pc_win_short = 100 * len(winning_short_trades) / len(short_trades)
                    pc_loss_short = 100 * len(losing_short_trades) / len(short_trades)

                    f.write("\n            Summary of short trades\n")
                    f.write("----------------------------------------------\n")
                    f.write("Number of short trades:   {}\n".format(len(short_trades)))
                    f.write("Short win rate:           {}%\n".format(round(pc_win_short, 1)))
                    f.write("Short loss rate:           {}%\n".format(round(pc_loss_short, 1)))
                    # f.write("Max win:                 ${}\n".format(round(max_long_win, 2)))
                    # f.write("Average win:             ${}\n".format(round(avg_long_win, 2)))
                    # f.write("Max loss:                -${}\n".format(round(max_long_loss, 2)))
                    # f.write("Average loss:            -${}\n".format(round(avg_long_loss, 2)))
                else:
                    f.write("There were no short trades.\n")

            self._export_trades_to_csv()
        else:
            with open(f'/home/jasper/Documents/Private/Projects/AutoBacktest/Strategy_Results/{self.strategy.symbol}_{self.strategy.tf}_{self.strategy.short_name}.txt', 'a') as f:
                f.write('No trades taken.\n')
                f.write(f'\n')

    def _export_trades_to_csv(self):
        csv_columns = self.trades[0].keys()

        try:
            with open(f'/home/jasper/Documents/Private/Projects/AutoBacktest/Trade_Data/{self.strategy.symbol}_{self.strategy.tf}_{self.strategy.short_name}.csv', 'w') as d:
                writer = csv.DictWriter(d, fieldnames=csv_columns)
                writer.writeheader()
                for trade in self.trades:
                    writer.writerow(trade)
        except IOError:
            print("I/O error")

    def _create_equity_dataframe(self):
        time_array = [trade['Close Time'] for trade in self.trades]
        balance_array = [trade['Balance'] for trade in self.trades]
        returns_array = [trade['Return'] for trade in self.trades]

        df = pd.DataFrame.from_dict({'Time': time_array, 'Equity': balance_array, 'Returns': returns_array})

        df['Time'] = pd.to_datetime(df['Time'], format='%Y-%m-%d')
        df['Equity'] = df['Equity'].astype(float)
        df['Returns'] = df['Returns'].astype(float)

        return df

    def _get_trade_size(self, row):
        loss_perc = abs(row['Entry Price'] - row['SL Price']) / row['Entry Price']
        risk_amount = self.balance * (self.risk / 100)
        return risk_amount / loss_perc

    def _write_equity_dataframe_to_file(self, equity_df):
        fig = px.line(equity_df, x="Time", y="Equity", title=f"{self.strategy.symbol} on {self.strategy.tf} using {self.strategy.name}.")
        fig.write_image(f"/home/jasper/Documents/Private/Projects/AutoBacktest/Equity_Curves/{self.strategy.symbol}_{self.strategy.tf}_{self.strategy.short_name}.pdf")
