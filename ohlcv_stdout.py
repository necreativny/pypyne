from pathlib import Path
from dataclasses import field

from pynecore.core.ohlcv_file import OHLCVReader

from custom_script_runner import fork_runner


script_path = Path("./scripts/demo_pyne.py")
data_path = "./data/ccxt_BYBIT_BTC_USDT_60.ohlcv"

def main():
    with OHLCVReader(data_path) as reader:
        time_from = reader.start_datetime
        time_to = reader.end_datetime
        time_from = time_from.replace(tzinfo=None)
        time_to = time_to.replace(tzinfo=None)
        ohlcv_iter = reader.read_from(int(time_from.timestamp()), int(time_to.timestamp()))
        
        inputs = {
            "src": "close",
            "fast_length": 20,
            "slow_length": 32,
        }
        for plot_data in fork_runner(script_path, ohlcv_iter, inputs):
            print(plot_data)

main()