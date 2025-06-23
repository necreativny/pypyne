"""
@pyne
Simple Pyne Script Demo

A basic demo showing a 12 and 26 period EMA crossover system.
"""
from pynecore import Series
from pynecore.lib import script, input, plot, color, ta


@script.indicator(
    title="Simple EMA Crossover Demo",
    shorttitle="EMA Demo",
    overlay=True
)
def main(
    src: Series[float] = input.source("close", title="Price Source"),
    fast_length: int = input.int(12, title="Fast EMA Length"),
    slow_length: int = input.int(26, title="Slow EMA Length")
):
    """
    A simple EMA crossover demo
    """
    # Calculate EMAs
    fast_ema = ta.ema(src, fast_length)
    slow_ema = ta.ema(src, slow_length)

    return{
        "Fast EMA": fast_ema,
        "Slow EMA": slow_ema
    }