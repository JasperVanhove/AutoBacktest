import csv

from models.Backtest import Backtest
from models.Strategies import WavetrendEMA

pairs = []
tfs = []
rrs = []
atrs = []

with open('./Util_Data/timeframes.csv', 'r') as fd:
    reader = csv.reader(fd, delimiter=',')
    for row in reader:
        tfs.append(row[0])

with open('./Util_Data/pairs.csv', 'r') as fd:
    reader = csv.reader(fd, delimiter=',')
    for row in reader:
        pairs.append(row[0])

with open('./Util_Data/risk_reward.csv', 'r') as fd:
    reader = csv.reader(fd, delimiter=',')
    for row in reader:
        rrs.append(row[0])

with open('./Util_Data/atrs.csv', 'r') as fd:
    reader = csv.reader(fd, delimiter=',')
    for row in reader:
        atrs.append(row[0])

if __name__ == '__main__':
    for tf in tfs:
        for pair in pairs:
            for rr in rrs:
                for atr in atrs:
                    try:
                        strategy = WavetrendEMA.WavetrendEMA(pair, tf, rr=rr, atr_multiplier=atr)  # rr and atr_multiplier
                        backtest = Backtest(strategy, 1000, 2, commission=0.06)
                        backtest.run()
                    except:
                        print('Error Backtesting {} on Timeframe {} with Risk/Reward {} and Atr Multiplier of {}!'.format(pair, tf, rr, atr))
