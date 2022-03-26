import warnings

import numpy as np
import pandas as pd
import plotly.graph_objects as go
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
        print("\nBeginning new backtest for {} on {} timeframe using {}.".format(self.strategy.symbol, self.strategy.tf, self.strategy.name))

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
            chart_data = go.Scatter(x=equity_df['Time'], y=equity_df['Equity'])
            fig = go.Figure(data=chart_data)

            print("\n---------------------------------------------------")
            print("                 Backtest Results")
            print("---------------------------------------------------")
            print("Start date:              {}".format(self.start_date))
            print("End date:                {}".format(self.end_date))
            print("Starting balance:        ${}".format(round(self.starting_balance, 2)))
            print("Ending balance:          ${}".format(round(self.balance, 2)))
            print("Total return:            ${} ({}%)".format(round(abs_return, 2),
                                                              round(pc_return, 1)))

            print("Instrument traded: ", self.strategy.symbol)
            if self.commission:
                print("Total fees:              ${}".format(round(self.fees, 3)))
            print("Total no. trades:        ", amount_of_trades)
            print("Backtest win rate:       {}%".format(round(pc_win, 1)))
            print("Backtest loss rate:       {}%".format(round(pc_loss, 1)))
            if pc_breakeven:
                print("\nInstrument breakeven rate (%):")
                print(pc_breakeven)

            print("")

            s = (equity_df.Returns + 1).cumprod()
            max_drawdown = np.ptp(s) / s.max()

            print("Maximum drawdown:        {}%".format(round(max_drawdown, 2)))
            # print("Max win:                 ${}".format(round(max_win, 2)))
            # print("Average win:             ${}".format(round(avg_win, 2)))
            # print("Max loss:                -${}".format(round(max_loss, 2)))
            # print("Average loss:            -${}".format(round(avg_loss, 2)))
            # print("Longest win streak:      {} trades".format(longest_win_streak))
            # print("Longest losing streak:   {} trades".format(longest_lose_streak))
            # print("Average trade duration:  {}".format(backtest_results['all_trades']['avg_trade_duration']))
            if len(long_trades) > 0:
                losing_long_trades = [trade for trade in long_trades if trade['Outcome'] == '-']
                winning_long_trades = [trade for trade in long_trades if trade['Outcome'] == '+']

                pc_loss_long = 100 * len(losing_long_trades) / len(long_trades)
                pc_win_long = 100 * len(winning_long_trades) / len(long_trades)

                print("\n            Summary of long trades")
                print("----------------------------------------------")
                print("Number of long trades:   {}".format(len(long_trades)))
                print("Long win rate:           {}%".format(round(pc_win_long, 1)))
                print("Long loss rate:           {}%".format(round(pc_loss_long, 1)))
                # print("Max win:                 ${}".format(round(max_long_win, 2)))
                # print("Average win:             ${}".format(round(avg_long_win, 2)))
                # print("Max loss:                -${}".format(round(max_long_loss, 2)))
                # print("Average loss:            -${}".format(round(avg_long_loss, 2)))
            else:
                print("There were no long trades.")

            if len(short_trades) > 0:
                winning_short_trades = [trade for trade in short_trades if trade['Outcome'] == '+']
                losing_short_trades = [trade for trade in short_trades if trade['Outcome'] == '-']

                pc_win_short = 100 * len(winning_short_trades) / len(short_trades)
                pc_loss_short = 100 * len(losing_short_trades) / len(short_trades)

                print("\n            Summary of short trades")
                print("----------------------------------------------")
                print("Number of short trades:   {}".format(len(short_trades)))
                print("Short win rate:           {}%".format(round(pc_win_short, 1)))
                print("Short loss rate:           {}%".format(round(pc_loss_short, 1)))
                # print("Max win:                 ${}".format(round(max_long_win, 2)))
                # print("Average win:             ${}".format(round(avg_long_win, 2)))
                # print("Max loss:                -${}".format(round(max_long_loss, 2)))
                # print("Average loss:            -${}".format(round(avg_long_loss, 2)))
            else:
                print("There were no short trades.")

            # print("\n                List of trades")
            # print("----------------------------------------------\n")
            # for trade in self.trades:
            #     print(f"{trade['Open Time']}: {trade['Side']} at {trade['Price']}, Closed at {trade['Close Price']} ({trade['Close Time']})")

            # fig.show()

        else:
            print("")
            print("No trades taken.")

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
