from pathlib import Path
from typing import Iterator
import csv

from pynecore.types.ohlcv import OHLCV

from custom_script_runner import fork_runner


script_path = Path("./scripts/demo_pyne.py")
data_path = "./data/ccxt_BYBIT_BTC_USDT_60.csv"


def read_candles_csv(file_path: Path) -> Iterator[OHLCV]:
    with open(file_path, mode='r') as csvfile:
        csv_reader = csv.DictReader(csvfile)
        for row in csv_reader:
            yield OHLCV(
                timestamp=int(row['timestamp']),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=float(row['volume']),
                extra_fields=None,
            )

def main():
    inputs = {
        "src": "close",
        "fast_length": 20,
        "slow_length": 32,
    }
    ohlcv_iter = read_candles_csv(data_path)
    for plot_data in fork_runner(script_path, ohlcv_iter, inputs):
        print(plot_data)

main()