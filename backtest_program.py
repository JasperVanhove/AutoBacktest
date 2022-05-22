import csv
from pathlib import Path
import sys
import os
import shutil

from program.models.Backtest import Backtest
from program.models.Strategies.Double_EMA_MACD_Cross import DoubleEmaMacdCross
from program.models.Strategies.Double_EMA_MACD_Hist import DoubleEmaMacdHist
from program.models.Strategies.Wavetrend_EMA import WavetrendEMA
from program.models.Strategies.Supertrend_Ema_Trailing import SupertrendEmaTrailing

pairs = []
tfs = []
rrs = []
atrs = []

util_path = Path(__file__).parent / f'Data/Util_Data/'
result_path = Path(__file__).parent / f'Data/Strategy_Results'
filtered_path = Path(__file__).parent / f'Data/Filtered_Strategy_Results'

with open(util_path / 'timeframes.csv', 'r') as fd:
    reader = csv.reader(fd, delimiter=',')
    for row in reader:
        tfs.append(row[0])

with open(util_path / 'pairs.csv', 'r') as fd:
    reader = csv.reader(fd, delimiter=',')
    for row in reader:
        pairs.append(row[0])

with open(util_path / 'risk_reward.csv', 'r') as fd:
    reader = csv.reader(fd, delimiter=',')
    for row in reader:
        rrs.append(row[0])

with open(util_path / 'atrs.csv', 'r') as fd:
    reader = csv.reader(fd, delimiter=',')
    for row in reader:
        atrs.append(row[0])

def sort_results_in_directories():
    # iterate over files in
    # that directory
    for filename in os.listdir(result_path):
        nums = []
        origin_file_path = os.path.join(result_path, filename)
        # checking if it is a file
        if os.path.isfile(origin_file_path):
            with open(origin_file_path, 'r') as data:
                for d in data.readlines():
                    try:
                        nums.append(d.strip('\n'))
                    except IOError:
                        print("got IOError")
                        sys.exit()
                    except ValueError:
                        print("got ValueError")
                        sys.exit()

            if len(nums) < 25 or not nums[24]:
                continue

            line = nums[24]
            avg_montly_perc = line.split(' ')[-1]
            avg_montly_perc = float(avg_montly_perc[:-1])

            if 0 < avg_montly_perc < 5:
                condition_folder = '0-5_Montly_Percent'
                copy_path = os.path.join(filtered_path, condition_folder, filename)
                shutil.copyfile(origin_file_path, copy_path)

            elif 5 < avg_montly_perc < 7:
                condition_folder = '5-7_Montly_Percent'
                copy_path = os.path.join(filtered_path, condition_folder, filename)
                shutil.copyfile(origin_file_path, copy_path)

            elif 7 < avg_montly_perc < 10:
                condition_folder = '7-10_Montly_Percent'
                copy_path = os.path.join(filtered_path, condition_folder, filename)
                shutil.copyfile(origin_file_path, copy_path)

            elif 10 < avg_montly_perc < 12:
                condition_folder = '10-12_Montly_Percent'
                copy_path = os.path.join(filtered_path, condition_folder, filename)
                shutil.copyfile(origin_file_path, copy_path)

            elif 12 < avg_montly_perc:
                condition_folder = '+12_Montly_Percent'
                copy_path = os.path.join(filtered_path, condition_folder, filename)
                shutil.copyfile(origin_file_path, copy_path)

if __name__ == '__main__':
    for tf in tfs:
        for pair in pairs:
            for rr in rrs:
                for atr in atrs:
                    try:
                        strategy = WavetrendEMA(pair, tf, rr=float(rr), atr_multiplier=float(atr))  # rr and atr_multiplier
                        backtest = Backtest(strategy, 1000, 2, commission=0.06)
                        backtest.run()
                    except Exception as e:
                        print('Error Backtesting {} on Timeframe {} with Risk/Reward {} and Atr Multiplier of {}!\n{}'.format(pair, tf, rr, atr, e))

    # strategy = SupertrendEmaTrailing('BTCUSDT', '1h', rr=float(3.5), atr_multiplier=float(2.9))  # rr and atr_multiplier
    # backtest = Backtest(strategy, 1000, 2, commission=0.06)
    # backtest.run(test=True)

    # sort_results_in_directories()
