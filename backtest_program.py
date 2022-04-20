import csv
from pathlib import Path

from program.models.Backtest import Backtest
from program.models.Strategies.Wavetrend_EMA import WavetrendEMA
from program.models.Strategies.Supertrend_Ema_Trailing import SupertrendEmaTrailing

pairs = []
tfs = []
rrs = []
atrs = []

util_path = Path(__file__).parent / f'Data/Util_Data/'

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

if __name__ == '__main__':
    for tf in tfs:
        for pair in pairs:
            for rr in rrs:
                for atr in atrs:
                    try:
                        strategy = SupertrendEmaTrailing(pair, tf, rr=float(rr), atr_multiplier=float(atr))  # rr and atr_multiplier
                        backtest = Backtest(strategy, 1000, 2, commission=0.06)
                        backtest.run()
                    except Exception as e:
                        print('Error Backtesting {} on Timeframe {} with Risk/Reward {} and Atr Multiplier of {}!\n{}'.format(pair, tf, rr, atr, e))

    # strategy = SupertrendEmaTrailing('ETHUSDT', '2h', rr=float(2.0), atr_multiplier=float(1.5))  # rr and atr_multiplier
    # backtest = Backtest(strategy, 1000, 2, commission=0.06)
    # backtest.run()