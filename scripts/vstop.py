"""
@pyne

Volatility Stop (built-in)
https://www.tradingview.com/support/solutions/43000594676/
"""

from pynecore import Series, Persistent
from pynecore.lib import script, input, close, ta, plot, color, na, nz, math, barstate, time
from pynecore.types.na import NA

@script.indicator("Volatility Stop", "VStop", overlay=True, timeframe="", timeframe_gaps=True)
def main(
        length: int = input.int(20, "Length", minval = 2),
        src: Series[float] = input.source(close, "Source"),
        factor: float = input.float(2.0, "Multiplier", minval = 0.25, step = 0.25),
    ):
    def volStop(src: Series[float], atrlen: int, atrfactor: float):
        if not na(src):
            max: Persistent[float] = src
            min: Persistent[float] = src
            uptrend: Persistent[bool] = True
            stop: Persistent[float] = NA(float)
            atrM: Series[float] = nz(ta.atr(atrlen) * atrfactor, ta.tr)
            max: Series[float] = math.max(max, src)
            min: Series[float] = math.min(max, src)
            stop = nz(math.max(stop, max - atrM) if uptrend else math.min(stop, min + atrM), src)
            uptrend: Series[bool] = src - stop >= 0.0

            if uptrend != uptrend[1] and not barstate.isfirst:
                max = src
                min = src
                stop = max - atrM if uptrend else min + atrM
            return stop, uptrend
        raise RuntimeError
    
    vStop, uptrend = volStop(src, length, factor)
    
    return {
        "Volatility Stop": vStop,
        "uptrend": uptrend,
    }