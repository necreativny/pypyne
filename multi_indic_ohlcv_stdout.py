from typing import Union, Any, Iterable
from pathlib import Path

from pynecore.types.ohlcv import OHLCV
from pynecore.core.ohlcv_file import OHLCVReader

from chart_runner import ChartRunner

IndicNameType = str
IndicInputsType = dict[str, Union[str, int, float]]
IndicValueType = dict[str, Any]
indics_folder = Path("./scripts")
data_path = "./data/ccxt_BYBIT_BTC_USDT_60.ohlcv"


def run_chart(indics: list[tuple[IndicNameType, IndicInputsType]], ohlcv_iter: Iterable[OHLCV]):
    scripts: list[tuple[Path, dict[str, Any]]] = []
    for indic_name, indic_inputs in indics:
        scripts.append((indics_folder/f"{indic_name}.py", indic_inputs))
    
    chart = ChartRunner(scripts, ohlcv_iter)
    for plot_data in chart.run_iter():
        print(plot_data)
        print()


def main():
    with OHLCVReader(data_path) as reader:
        time_from = reader.start_datetime
        time_to = reader.end_datetime
        time_from = time_from.replace(tzinfo=None)
        time_to = time_to.replace(tzinfo=None)
        ohlcv_iter = reader.read_from(int(time_from.timestamp()), int(time_to.timestamp()))
        
        chart_indics: list[tuple[IndicNameType, IndicInputsType]] = [
            ("demo_pyne", {"src": "close", "fast_length": 16, "slow_length": 30}),
            ("vstop", {"length": 30, "src": "close", "factor": 2.0})
        ]
        run_chart(chart_indics, ohlcv_iter)

main()