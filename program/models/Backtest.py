import csv
import warnings
from pathlib import Path

import numpy as np
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
        self.results = {}

    def run(self, test=False):
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
            self.strategy.add_equity(index, row, self.balance)
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

        if self.balance <= self.starting_balance:
            print('\n')
            print('\n')
            print('No positive Balance!')
            print('\n')
            print('\n')
            return

        if len(self.trades) < 50:
            print('\n')
            print('\n')
            print('Need more than 50 trades!')
            print('\n')
            print('\n')
            return

        self._calculate_results()
        self.print_results() if test else self.print_results_to_file()

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

    def print_results_to_file(self):
        self.print_header_to_file()
        if self.results['gmean_monthly_return'] >= 3.0:
            with open(data_path / f'Strategy_Results/{self.strategy.symbol}_{self.strategy.tf}_{self.strategy.short_name}_{self.strategy.risk_reward}RR_{self.strategy.atr_multiplier}ATR.txt', 'a') as f:

                f.write("\n---------------------------------------------------\n")
                f.write("                 Backtest Results\n")
                f.write("---------------------------------------------------\n")
                f.write("Start date:              {}\n".format(self.start_date))
                f.write("End date:                {}\n".format(self.end_date))
                f.write("Starting balance:        ${}\n".format(round(self.starting_balance, 2)))
                f.write("Ending balance:          ${}\n".format(round(self.balance, 2)))
                f.write("Equity Peak:             ${}\n".format(round(self.results['equity_peak'], 2)))
                f.write("Total return:            ${} ({}%)\n".format(round(self.results['abs_return'], 2),
                                                                      round(self.results['pc_return'], 1)))

                f.write("Instrument traded: {}\n".format(self.strategy.symbol))
                if self.commission:
                    f.write("Total fees:              ${}\n".format(round(self.fees, 3)))
                f.write("Total no. trades:        {}\n".format(self.results['amount_of_trades']))
                f.write("Backtest win rate:       {}%\n".format(round(self.results['pc_win'] * 100, 1)))
                f.write("Backtest loss rate:       {}%\n".format(round(self.results['pc_loss'] * 100, 1)))
                if self.results['pc_breakeven']:
                    f.write("\nInstrument breakeven rate (%):      {}\n".format(round(self.results['pc_breakeven'], 1)))

                f.write("")

                f.write("Maximum drawdown:        {}%\n".format(round(self.results['max_drawdown_perc'], 2)))
                f.write("Profit Factor:            {}\n".format(round(self.results['profit_factor'], 2)))
                f.write("Return (Ann.) [%]:        {}\n".format(round(self.results['annualized_return'] * 100, 2)))
                f.write("Volatility (Ann.) [%]:    {}\n".format(round(self.results['annual_volatility'], 2)))
                f.write("Avg. Monthly Return [%]:  {}%\n".format(round(self.results['gmean_monthly_return'], 2)))
                f.write("Avg. Trade Return [%]:  {}%\n".format(round(self.results['avg_trade_perc'], 2)))
                f.write("Avg. Trade Duration:  {}\n".format(self.results['avg_trade_duration']))
                f.write("Max. Trade Duration:  {}\n".format(self.results['max_trade_duration']))
                f.write("")
                f.write("Max win Amount:            ${}\n".format(round(self.results['max_win'], 2)))
                f.write("Average win Amount:        ${}\n".format(round(self.results['avg_win'], 2)))
                f.write("Max loss Amount:          -${}\n".format(round(abs(self.results['max_loss']), 2)))
                f.write("Average loss Amount:      -${}\n".format(round(abs(self.results['avg_loss']), 2)))
                f.write("Longest win streak:      {} trades\n".format(self.results['longest_win_streak']))
                # print("Longest losing streak:   {} trades\n".format(longest_lose_streak))
                # print("Average trade duration:  {}\n".format(backtest_results['all_trades']['avg_trade_duration']))
                f.write("")
                f.write("Sharpe Ratio:            {}\n".format(round(self.results['sharpe_ratio'], 2)))
                f.write("Sortino Ratio:            {}\n".format(round(self.results['sortino_ratio'], 2)))
                f.write("Calmar Ratio:            {}\n".format(round(self.results['calmar_ratio'], 2)))
                f.write("Expectancy [%]:            {}%\n".format(round(self.results['expectancy_perc'], 2)))

            if self.results.get('long_trades', False):
                f.write("\n            Summary of long trades\n")
                f.write("----------------------------------------------\n")
                f.write("Number of long trades:   {}\n".format(len(self.results['long_trades'])))
                f.write("Long win rate:           {}%\n".format(round(self.results['pc_win_long'] * 100, 1)))
                f.write("Long loss rate:           {}%\n".format(round(self.results['pc_loss_long'] * 100, 1)))
                f.write("Max win:                 ${}\n".format(round(self.results['max_long_win'], 2)))
                f.write("Average win:             ${}\n".format(round(self.results['avg_long_win'], 2)))
                f.write("Max loss:                -${}\n".format(round(abs(self.results['max_long_loss']), 2)))
                f.write("Average loss:            -${}\n".format(round(abs(self.results['avg_long_loss']), 2)))
                f.write("Longest win streak:      {} trades\n".format(self.results['longest_long_win_streak']))
            else:
                f.write("There were no long trades.\n")

            if self.results.get('short_trades', False):

                f.write("\n            Summary of short trades\n")
                f.write("----------------------------------------------\n")
                f.write("Number of short trades:   {}\n".format(len(self.results['short_trades'])))
                f.write("Short win rate:           {}%\n".format(round(self.results['pc_win_short'] * 100, 1)))
                f.write("Short loss rate:           {}%\n".format(round(self.results['pc_loss_short'] * 100, 1)))
                f.write("Max win:                 ${}\n".format(round(self.results['max_short_win'], 2)))
                f.write("Average win:             ${}\n".format(round(self.results['avg_short_win'], 2)))
                f.write("Max loss:                -${}\n".format(round(abs(self.results['max_short_loss']), 2)))
                f.write("Average loss:            -${}\n".format(round(abs(self.results['avg_short_loss']), 2)))
                f.write("Longest win streak:      {} trades\n".format(self.results['longest_short_win_streak']))
            else:
                f.write("There were no short trades.\n")

            self._export_trades_to_csv()
        else:
            with open(data_path / f'Strategy_Results/{self.strategy.symbol}_{self.strategy.tf}_{self.strategy.short_name}_{self.strategy.risk_reward}RR_{self.strategy.atr_multiplier}ATR.txt', 'a') as f:
                f.write('No trades taken.\n')
                f.write(f'\n')

    def print_results(self):
        if self.results['gmean_monthly_return'] >= 3.0:

            print("\n---------------------------------------------------\n")
            print("                 Backtest Results\n")
            print("---------------------------------------------------\n")
            print("Start date:              {}\n".format(self.start_date))
            print("End date:                {}\n".format(self.end_date))
            print("Starting balance:        ${}\n".format(round(self.starting_balance, 2)))
            print("Ending balance:          ${}\n".format(round(self.balance, 2)))
            print("Equity Peak:             ${}\n".format(round(self.results['equity_peak'], 2)))
            print("Total return:            ${} ({}%)\n".format(round(self.results['abs_return'], 2),
                                                                round(self.results['pc_return'], 1)))

            print("Instrument traded: {}\n".format(self.strategy.symbol))
            if self.commission:
                print("Total fees:              ${}\n".format(round(self.fees, 3)))
            print("Total no. trades:        {}\n".format(self.results['amount_of_trades']))
            print("Backtest win rate:       {}%\n".format(round(self.results['pc_win'] * 100, 1)))
            print("Backtest loss rate:       {}%\n".format(round(self.results['pc_loss'] * 100, 1)))
            if self.results['pc_breakeven']:
                print("\nInstrument breakeven rate (%):      {}\n".format(round(self.results['pc_breakeven'], 1)))

            print("")

            print("Maximum drawdown:        {}%\n".format(round(self.results['max_drawdown_perc'], 2)))
            print("Profit Factor:            {}\n".format(round(self.results['profit_factor'], 2)))
            print("Return (Ann.) [%]:        {}\n".format(round(self.results['annualized_return'] * 100, 2)))
            print("Volatility (Ann.) [%]:    {}\n".format(round(self.results['annual_volatility'], 2)))
            print("Avg. Monthly Return [%]:  {}%\n".format(round(self.results['gmean_monthly_return'], 2)))
            print("Avg. Trade Return [%]:  {}%\n".format(round(self.results['avg_trade_perc'], 2)))
            print("Avg. Trade Duration:  {}\n".format(self.results['avg_trade_duration']))
            print("Max. Trade Duration:  {}\n".format(self.results['max_trade_duration']))
            print("")
            print("Max win Amount:            ${}\n".format(round(self.results['max_win'], 2)))
            print("Average win Amount:        ${}\n".format(round(self.results['avg_win'], 2)))
            print("Max loss Amount:          -${}\n".format(round(abs(self.results['max_loss']), 2)))
            print("Average loss Amount:      -${}\n".format(round(abs(self.results['avg_loss']), 2)))
            print("Longest win streak:      {} trades\n".format(self.results['longest_win_streak']))
            # print("Longest losing streak:   {} trades\n".format(longest_lose_streak))
            # print("Average trade duration:  {}\n".format(backtest_results['all_trades']['avg_trade_duration']))
            print("")
            print("Sharpe Ratio:            {}\n".format(round(self.results['sharpe_ratio'], 2)))
            print("Sortino Ratio:            {}\n".format(round(self.results['sortino_ratio'], 2)))
            print("Calmar Ratio:            {}\n".format(round(self.results['calmar_ratio'], 2)))
            print("Expectancy [%]:            {}%\n".format(round(self.results['expectancy_perc'], 2)))

            if self.results.get('long_trades', False):
                print("\n            Summary of long trades\n")
                print("----------------------------------------------\n")
                print("Number of long trades:   {}\n".format(len(self.results['long_trades'])))
                print("Long win rate:           {}%\n".format(round(self.results['pc_win_long'] * 100, 1)))
                print("Long loss rate:           {}%\n".format(round(self.results['pc_loss_long'] * 100, 1)))
                print("Max win Amount:            ${}\n".format(round(self.results['max_long_win'], 2)))
                print("Average win Amount:        ${}\n".format(round(self.results['avg_long_win'], 2)))
                print("Max loss Amount:          -${}\n".format(round(abs(self.results['max_long_loss']), 2)))
                print("Average loss Amount:      -${}\n".format(round(abs(self.results['avg_long_loss']), 2)))
                print("Longest win streak:      {} trades\n".format(self.results['longest_long_win_streak']))
            else:
                print("There were no long trades.\n")

            if self.results.get('short_trades', False):

                print("\n            Summary of short trades\n")
                print("----------------------------------------------\n")
                print("Number of short trades:   {}\n".format(len(self.results['short_trades'])))
                print("Short win rate:           {}%\n".format(round(self.results['pc_win_short'] * 100, 1)))
                print("Short loss rate:           {}%\n".format(round(self.results['pc_loss_short'] * 100, 1)))
                print("Max win Amount:                 ${}\n".format(round(self.results['max_short_win'], 2)))
                print("Average win Amount:             ${}\n".format(round(self.results['avg_short_win'], 2)))
                print("Max loss Amount:                -${}\n".format(round(abs(self.results['max_short_loss']), 2)))
                print("Average loss Amount:            -${}\n".format(round(abs(self.results['avg_short_loss']), 2)))
                print("Longest win streak:      {} trades\n".format(self.results['longest_short_win_streak']))
            else:
                print("There were no short trades.\n")
        else:
            print('No trades taken.\n')
            print(f'\n')

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

        df['Duration'] = df['Close Time'] - df['Time']

        df['Time'] = pd.to_datetime(df['Time'], format='%Y-%m-%d')
        df['Equity'] = df['Equity'].astype(float)
        df['Returns'] = df['Returns'].astype(float)
        df['Return Perc'] = df['Return Perc'].astype(float)
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

    def _calculate_results(self):
        self.results['abs_return'] = self.balance - self.starting_balance
        self.results['pc_return'] = 100 * self.results['abs_return'] / self.starting_balance
        self.results['amount_of_trades'] = len(self.trades)

        date_diff = relativedelta.relativedelta(self.end_date, self.start_date)
        months_diff = (date_diff.years * 12) + date_diff.months

        indexed_df = self.strategy.df.set_index('Open Time')

        self.results['equity_peak'] = indexed_df['Equity'].max()

        dd, dd_duration, dd_peaks = self._get_dd_metrics(indexed_df['Equity'])
        max_dd = -np.nan_to_num(dd.max())

        day_returns = indexed_df['Equity'].resample('D').last().dropna().pct_change()
        gmean_day_return = self.geometric_mean(day_returns)

        annualized_return = (1 + gmean_day_return) ** 365 - 1
        annual_volatility = self._get_annual_volatility(day_returns, gmean_day_return)

        sharpe_ratio = self._get_sharpe_ratio(annualized_return, annual_volatility)
        sortino_ratio = self._get_sortino_ratio(day_returns, annualized_return)
        calmar_ratio = self._get_calmar_ratio(annualized_return, max_dd)

        self.results['annualized_return'] = annualized_return
        self.results['gmean_monthly_return'] = (annualized_return / 12) * 100
        self.results['annual_volatility'] = annual_volatility

        self.results['sharpe_ratio'] = sharpe_ratio
        self.results['sortino_ratio'] = sortino_ratio
        self.results['calmar_ratio'] = calmar_ratio

        self.results['max_drawdown_perc'] = max_dd * 100
        self.results['avg_drawdown_perc'] = -dd_peaks.mean() * 100
        self.results['max_drawdown_duration'] = dd_duration.max()
        self.results['avg_drawdown_duration'] = dd_duration.mean()

        ### Todo: Add extra metrics
        # - Equity Peak
        # - SQN??
        ###

        if self.results['gmean_monthly_return'] >= 3.0:
            self.results['winning_trades'] = [trade for trade in self.trades if trade['Outcome'] == '+']
            self.results['losing_trades'] = [trade for trade in self.trades if trade['Outcome'] == '-']
            self.results['break_even_trades'] = [trade for trade in self.trades if trade['Outcome'] == '0']

            self.results['long_trades'] = [trade for trade in self.trades if trade['Side'] == 'Long']
            self.results['short_trades'] = [trade for trade in self.trades if trade['Side'] == 'Short']

            self.results['pc_win'] = len(self.results['winning_trades']) / self.results['amount_of_trades']
            self.results['pc_loss'] = len(self.results['losing_trades']) / self.results['amount_of_trades']
            self.results['pc_breakeven'] = 100 * len(self.results['break_even_trades']) / self.results['amount_of_trades']

            trades_df = self._create_dataframe_from_list(self.trades)
            wins_df = self._create_dataframe_from_list(self.results['winning_trades'])
            loss_df = self._create_dataframe_from_list(self.results['losing_trades'])
            long_df = self._create_dataframe_from_list(self.results['long_trades'])
            short_df = self._create_dataframe_from_list(self.results['short_trades'])

            # self._write_equity_dataframe_to_file(trades_df)

            self.results['max_win'] = wins_df['Returns'].max()
            self.results['avg_win'] = wins_df['Returns'].mean()
            self.results['max_loss'] = loss_df['Returns'].min()
            self.results['avg_loss'] = loss_df['Returns'].mean()

            grouper = (trades_df.Outcome != trades_df.Outcome.shift()).cumsum()
            self.results['longest_win_streak'] = trades_df.groupby(grouper).cumcount().max()

            gmean_trade_return = self.geometric_mean(trades_df['Return Perc'])

            self.results['avg_trade_perc'] = gmean_trade_return * 100
            self.results['max_trade_duration'] = self._round_timedelta(trades_df['Duration'].max())
            self.results['avg_trade_duration'] = self._round_timedelta(trades_df['Duration'].mean())

            self.results['profit_factor'] = wins_df['Returns'].sum() / abs(loss_df['Returns'].sum())
            self.results['expectancy_perc'] = self._get_expectancy_ratio()
            # self.results['sqn'] = np.sqrt(self.results['amount_of_trades']) * pl.mean() / (pl.std() or np.nan)

            if len(self.results['long_trades']) > 0:
                losing_long_trades = [trade for trade in self.results['long_trades'] if trade['Outcome'] == '-']
                winning_long_trades = [trade for trade in self.results['long_trades'] if trade['Outcome'] == '+']

                long_win_df = self._create_dataframe_from_list(winning_long_trades)
                long_loss_df = self._create_dataframe_from_list(losing_long_trades)

                self.results['pc_loss_long'] = len(losing_long_trades) / len(self.results['long_trades'])
                self.results['pc_win_long'] = len(winning_long_trades) / len(self.results['long_trades'])

                self.results['max_long_win'] = long_win_df['Returns'].max()
                self.results['avg_long_win'] = long_win_df['Returns'].mean()
                self.results['max_long_loss'] = long_loss_df['Returns'].min()
                self.results['avg_long_loss'] = long_loss_df['Returns'].mean()

                grouper = (long_df.Outcome != long_df.Outcome.shift()).cumsum()
                self.results['longest_long_win_streak'] = long_df.groupby(grouper).cumcount().max()  # Todo: Calculate this with a method

            if len(self.results['short_trades']) > 0:
                winning_short_trades = [trade for trade in self.results['short_trades'] if trade['Outcome'] == '+']
                losing_short_trades = [trade for trade in self.results['short_trades'] if trade['Outcome'] == '-']

                short_win_df = self._create_dataframe_from_list(winning_short_trades)
                short_loss_df = self._create_dataframe_from_list(losing_short_trades)

                self.results['pc_win_short'] = len(winning_short_trades) / len(self.results['short_trades'])
                self.results['pc_loss_short'] = len(losing_short_trades) / len(self.results['short_trades'])

                self.results['max_short_win'] = short_win_df['Returns'].max()
                self.results['avg_short_win'] = short_win_df['Returns'].mean()
                self.results['max_short_loss'] = short_loss_df['Returns'].min()
                self.results['avg_short_loss'] = short_loss_df['Returns'].mean()

                grouper = (short_df.Outcome != short_df.Outcome.shift()).cumsum()
                self.results['longest_short_win_streak'] = short_df.groupby(grouper).cumcount().max()

    def geometric_mean(self, returns: pd.Series) -> float:
        returns = returns.fillna(0) + 1
        if np.any(returns <= 0):
            return 0
        return np.exp(np.log(returns).sum() / (len(returns) or np.nan)) - 1

    def _get_annual_volatility(self, daily_returns, gmean_day_return):
        return np.sqrt((daily_returns.var(ddof=int(bool(daily_returns.shape))) + (1 + gmean_day_return) ** 2) ** 365 - (1 + gmean_day_return) ** (2 * 365)) * 100

    def _get_sharpe_ratio(self, annualized_return, annual_volatility):
        return np.clip((annualized_return * 100 - 0) / (annual_volatility or np.nan), 0, np.inf)

    def _get_sortino_ratio(self, daily_returns, annualized_return):
        return np.clip((annualized_return - 0) / (np.sqrt(np.mean(daily_returns.clip(-np.inf, 0) ** 2)) * np.sqrt(365)), 0, np.inf)

    def _get_calmar_ratio(self, annualized_return, max_dd):
        return np.clip(annualized_return / (-max_dd or np.nan), 0, np.inf)

    def _get_dd_metrics(self, equity):
        dd = 1 - equity / np.maximum.accumulate(equity)

        iloc = np.unique(np.r_[(dd == 0).values.nonzero()[0], len(dd) - 1])
        iloc = pd.Series(iloc, index=dd.index[iloc])
        df = iloc.to_frame('iloc').assign(prev=iloc.shift())
        df = df[df['iloc'] > df['prev'] + 1].astype(int)

        # If no drawdown since no trade, avoid below for pandas sake and return nan series
        if not len(df):
            return (dd.replace(0, np.nan),) * 3

        df['duration'] = df['iloc'].map(dd.index.__getitem__) - df['prev'].map(dd.index.__getitem__)
        df['peak_dd'] = df.apply(lambda row: dd.iloc[row['prev']:row['iloc'] + 1].max(), axis=1)
        df = df.reindex(dd.index)

        return dd, df['duration'], df['peak_dd']

    def _round_timedelta(self, timedelta):
        days = timedelta.days
        seconds = timedelta.seconds
        hours = seconds // 3600
        minutes = (seconds // 60) % 60

        return f'{days} days, {hours} hours and {minutes} minutes'

    def _get_expectancy_ratio(self):
        win_ratio = self.results['pc_win']
        loss_ratio = self.results['pc_loss']
        reward_to_risk_ratio = self.results['avg_win'] / abs(self.results['avg_loss'])

        return (reward_to_risk_ratio * win_ratio) - loss_ratio
