from models.Backtest import Backtest
from models.Strategies import Strategy, VumanchuEmasMfi, EmaStochRsiDivergence, WavetrendEMA, MtfEmaMacdDiv

if __name__ == '__main__':
    # strategy = WavetrendEMA.WavetrendEMA('BTCUSDT', '4h', rr=3)  # rr and atr_multiplier
    # backtest = Backtest(strategy, 1000, 2, commission=0.06)
    # backtest.run()
    # print('\n')
    # print('\n')
    # strategy = WavetrendEMA.WavetrendEMA('BTCUSDT', '2h', rr=3)
    # backtest = Backtest(strategy, 1000, 2, commission=0.06)
    # backtest.run()
    # print('\n')
    # print('\n')
    # strategy = WavetrendEMA.WavetrendEMA('BTCUSDT', '1h', rr=3)
    # backtest = Backtest(strategy, 1000, 2, commission=0.06)
    # backtest.run()
    # print('\n')
    # print('\n')
    # strategy = WavetrendEMA.WavetrendEMA('BTCUSDT', '30m', rr=3)
    # backtest = Backtest(strategy, 1000, 2, commission=0.06)
    # backtest.run()
    # print('\n')
    # print('\n')
    strategy = WavetrendEMA.WavetrendEMA('BTCUSDT', '30mtest', rr=1.5)
    backtest = Backtest(strategy, 1000, 2, commission=0.06)
    backtest.run()
    print('\n')
    print('\n')
    # strategy = WavetrendEMA.WavetrendEMA('BTCUSDT', '15m', rr=2.5)
    # backtest = Backtest(strategy, 1000, 2, commission=0.06)
    # backtest.run()
    # print('\n')
    # print('\n')
    # strategy = WavetrendEMA.WavetrendEMA('BTCUSDT', '5m', rr=1.5)
    # backtest = Backtest(strategy, 1000, 2, commission=0.06)
    # backtest.run()
    # print('\n')
    # print('\n')
