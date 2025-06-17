from typing import Iterable, Iterator, Callable, TYPE_CHECKING, Any
from types import ModuleType
import sys
from pathlib import Path
from datetime import datetime, UTC
from dataclasses import field

from pynecore.types.ohlcv import OHLCV
from pynecore.core.syminfo import SymInfo
from pynecore.core.csv_file import CSVWriter

from pynecore.types import script_type

if TYPE_CHECKING:
    from zoneinfo import ZoneInfo
    from pynecore.core.script import script
    from pynecore.lib.strategy import Trade

__all__ = [
    'import_script',
    'ScriptRunner',
]


from zoneinfo import ZoneInfo


# modified from ScriptRunner.run_iter to match desired parameters and return values
# tz and last_bar_index are hardcoded to match desired parameters and return values
def fork_runner(script_module: ModuleType,
                ohlcv_iter: Iterable[OHLCV],
                script_inputs: dict[str, Any] = {},
                on_progress: Callable[[datetime], None] | None = None) \
            -> Iterator[tuple[OHLCV, dict[str, Any]] | tuple[OHLCV, dict[str, Any], list['Trade']]]:
        """
        Run the script on the data

        :param script_path: The path to the script to run
        :param ohlcv_iter: Iterator of OHLCV data
        :param script_inputs: Inputs to pass to pyne script: {"src": "close", "length": 20,}
        :param on_progress: Callback to call on every iteration
        :return: Return a dictionary with all data the sctipt plotted
        :raises AssertionError: If the 'main' function does not return a dictionary
        """

        last_bar_index = 0
        tz: ZoneInfo = ZoneInfo("UTC")

        script_obj: script = script_module.main.script
        
        # from .. import lib
        from pynecore import lib
        # from ..lib import _parse_timezone, barstate, string
        from pynecore.lib import _parse_timezone, barstate, string
        from pynecore.core import function_isolation

        is_strat = script_obj.script_type == script_type.strategy

        # Reset bar_index
        bar_index = 0
        # Reset function isolation
        function_isolation.reset()

        # Set script data
        lib._script = script_obj  # Store script object in lib

        # # Update syminfo lib properties if needed
        # if not self.update_syminfo_every_run:
        #     _set_lib_syminfo_properties(self.syminfo, lib)
        #     self.tz = _parse_timezone(lib.syminfo.timezone)

        # Clear plot data
        lib._plot_data.clear()

        # Position shortcut
        position = script_obj.position

        try:
            for candle in ohlcv_iter:
                # # Update syminfo lib properties if needed, other ScriptRunner instances may have changed them
                # if self.update_syminfo_every_run:
                #     _set_lib_syminfo_properties(self.syminfo, lib)
                #     self.tz = _parse_timezone(lib.syminfo.timezone)

                if bar_index == last_bar_index:
                    barstate.islast = True

                # Update lib properties
                _set_lib_properties(candle, bar_index, tz, lib)

                # Reset function isolation
                function_isolation.reset_step()

                # Process limit orders
                if is_strat and position:
                    position.process_orders()

                # Run the script
                res = script_module.main(**script_inputs)

                # Update plot data with the results
                if res is not None:
                    assert isinstance(res, dict), "The 'main' function must return a dictionary!"
                    lib._plot_data.update(res)
                
                # Yield plot data to be able to process in a subclass
                if not is_strat:
                    yield candle, lib._plot_data
                elif position:
                    yield candle, lib._plot_data, position.new_closed_trades
                
                # Clear plot data
                lib._plot_data.clear()

                # Call the progress callback
                if on_progress:
                    assert lib._datetime is not None
                    on_progress(lib._datetime.replace(tzinfo=None))

                # Update bar index
                bar_index += 1
                # It is no longer the first bar
                barstate.isfirst = False

            if on_progress:
                on_progress(datetime.max)

        except GeneratorExit:
            pass


def import_script(script_path: Path) -> ModuleType:
    """
    Import the script
    """
    from importlib import import_module
    # Import hook only before importing the script, to make import hook being used only for Pyne scripts
    # (this makes 1st run faster, than if it would be a top-level import)

    # from . import import_hook  # noqa
    from pynecore.core import import_hook

    # Add script's directory to Python path temporarily
    sys.path.insert(0, str(script_path.parent))
    try:
        # This will use the import system, including our hook
        module = import_module(script_path.stem)
    finally:
        # Remove the directory from path
        sys.path.pop(0)

    if not hasattr(module, 'main'):
        raise ImportError(f"Script '{script_path}' must have a 'main' function to run!")
    
    if not hasattr(module.main, 'script'):
        raise ImportError(f"The 'main' function must be decorated with "
                            f"@script.[indicator|strategy|library] to run!")

    return module


# noinspection PyShadowingNames
def _set_lib_properties(ohlcv: OHLCV, bar_index: int, tz: 'ZoneInfo', lib: ModuleType):
    """
    Set lib properties from OHLCV
    """
    if TYPE_CHECKING:  # This is needed for the type checker to work
        # from .. import lib
        from pynecore.lib import lib

    lib.bar_index = bar_index

    lib.open = ohlcv.open
    lib.high = ohlcv.high
    lib.low = ohlcv.low
    lib.close = ohlcv.close
    lib.volume = ohlcv.volume

    lib.hl2 = (ohlcv.high + ohlcv.low) / 2.0
    lib.hlc3 = (ohlcv.high + ohlcv.low + ohlcv.close) / 3.0
    lib.ohlc4 = (ohlcv.open + ohlcv.high + ohlcv.low + ohlcv.close) / 4.0
    lib.hlcc4 = (ohlcv.high + ohlcv.low + 2 * ohlcv.close) / 4.0

    dt = lib._datetime = datetime.fromtimestamp(ohlcv.timestamp, UTC).astimezone(tz)
    lib._time = int(dt.timestamp() * 1000)  # PineScript representation of time


def _set_lib_syminfo_properties(syminfo: SymInfo, lib: ModuleType):
    """
    Set syminfo library properties from this object
    """
    if TYPE_CHECKING:  # This is needed for the type checker to work
        # from .. import lib
        from pynecore.lib import lib

    for key, value in syminfo.__dict__.items():
        if value is not None:
            try:
                setattr(lib.syminfo, key, value)
            except AttributeError:
                pass

    lib.syminfo.root = syminfo.ticker
    lib.syminfo.ticker = syminfo.prefix + ':' + syminfo.ticker

    lib.syminfo._opening_hours = syminfo.opening_hours
    lib.syminfo._session_starts = syminfo.session_starts
    lib.syminfo._session_ends = syminfo.session_ends


class ScriptRunner:
    """
    Script runner
    """

    __slots__ = ('script_module', 'script', 'ohlcv_iter', 'syminfo', 'update_syminfo_every_run',
                 'bar_index', 'tz', 'plot_writer', 'strat_writer', 'equity_writer', 'last_bar_index')

    def __init__(self, script_path: Path, ohlcv_iter: Iterable[OHLCV], syminfo: SymInfo, *,
                 plot_path: Path | None = None, strat_path: Path | None = None,
                 equity_path: Path | None = None,
                 update_syminfo_every_run: bool = False, last_bar_index=0):
        """
        Initialize the script runner

        :param script_path: The path to the script to run
        :param ohlcv_iter: Iterator of OHLCV data
        :param syminfo: Symbol information
        :param plot_path: Path to save the plot data
        :param strat_path: Path to save the strategy results
        :param equity_path: Path to save the equity data of the strategy
        :param update_syminfo_every_run: If it is needed to update the syminfo lib in every run,
                                         needed for parallel script executions
        :param last_bar_index: Last bar index, the index of the last bar of the historical data
        :raises ImportError: If the script does not have a 'main' function
        :raises ImportError: If the 'main' function is not decorated with @script.[indicator|strategy|library]
        :raises OSError: If the plot file could not be opened
        """
        self.script_module = import_script(script_path)

        if not hasattr(self.script_module.main, 'script'):
            raise ImportError(f"The 'main' function must be decorated with "
                              f"@script.[indicator|strategy|library] to run!")

        self.script: script = self.script_module.main.script

        # noinspection PyProtectedMember
        from ..lib import _parse_timezone

        self.ohlcv_iter = ohlcv_iter
        self.syminfo = syminfo
        self.update_syminfo_every_run = update_syminfo_every_run
        self.last_bar_index = last_bar_index
        self.bar_index = 0

        self.tz = _parse_timezone(syminfo.timezone)

        self.plot_writer = CSVWriter(
            plot_path, float_fmt=f".{self.script.precision or 8}g"
        ) if plot_path else None
        self.strat_writer = CSVWriter(strat_path) if strat_path else None
        self.equity_writer = CSVWriter(equity_path, headers=(
            "Trade #", "Bar Index", "Type", "Signal", "Date/Time", f"Price {syminfo.currency}",
            "Contracts", f"Profit {syminfo.currency}", "Profit %", f"Cumulative profit {syminfo.currency}",
            "Cumulative profit %", f"Run-up {syminfo.currency}", "Run-up %", f"Drawdown {syminfo.currency}",
            "Drawdown %",
        )) if equity_path else None

    # noinspection PyProtectedMember
    def run_iter(self, on_progress: Callable[[datetime], None] | None = None) \
            -> Iterator[tuple[OHLCV, dict[str, Any]] | tuple[OHLCV, dict[str, Any], list['Trade']]]:
        """
        Run the script on the data

        :param on_progress: Callback to call on every iteration
        :return: Return a dictionary with all data the sctipt plotted
        :raises AssertionError: If the 'main' function does not return a dictionary
        """
        # from .. import lib
        from pynecore.lib import lib
        from ..lib import _parse_timezone, barstate, string
        from pynecore.core import function_isolation
        # from . import script
        from pynecore.core import script

        is_strat = self.script.script_type == script_type.strategy

        # Reset bar_index
        self.bar_index = 0
        # Reset function isolation
        function_isolation.reset()

        # Set script data
        lib._script = self.script  # Store script object in lib

        # Update syminfo lib properties if needed
        if not self.update_syminfo_every_run:
            _set_lib_syminfo_properties(self.syminfo, lib)
            self.tz = _parse_timezone(lib.syminfo.timezone)

        # Open plot writer if we have one
        if self.plot_writer:
            self.plot_writer.open()

        # If the script is a strategy, we open strategy output files too
        if is_strat:
            # Open equity writer if we have one
            if self.equity_writer:
                self.equity_writer.open()

        # Clear plot data
        lib._plot_data.clear()

        # Trade counter
        trade_num = 0

        # Position shortcut
        position = self.script.position

        try:
            for candle in self.ohlcv_iter:
                # Update syminfo lib properties if needed, other ScriptRunner instances may have changed them
                if self.update_syminfo_every_run:
                    _set_lib_syminfo_properties(self.syminfo, lib)
                    self.tz = _parse_timezone(lib.syminfo.timezone)

                if self.bar_index == self.last_bar_index:
                    barstate.islast = True

                # Update lib properties
                _set_lib_properties(candle, self.bar_index, self.tz, lib)

                # Reset function isolation
                function_isolation.reset_step()

                # Process limit orders
                if is_strat and position:
                    position.process_orders()

                # Execute registered library main functions before main script
                lib._lib_semaphore = True
                for library_title, main_func in script._registered_libraries:
                    main_func()
                lib._lib_semaphore = False

                # Run the script
                res = self.script_module.main()

                # Update plot data with the results
                if res is not None:
                    assert isinstance(res, dict), "The 'main' function must return a dictionary!"
                    lib._plot_data.update(res)

                # Write plot data to CSV if we have a writer
                if self.plot_writer and lib._plot_data:
                    # Create a new dictionary combining extra_fields (if any) with plot data
                    extra_fields = {} if candle.extra_fields is None else dict(candle.extra_fields)
                    extra_fields.update(lib._plot_data)
                    # Create a new OHLCV instance with updated extra_fields
                    updated_candle = candle._replace(extra_fields=extra_fields)
                    self.plot_writer.write_ohlcv(updated_candle)

                # Yield plot data to be able to process in a subclass
                if not is_strat:
                    yield candle, lib._plot_data
                elif position:
                    yield candle, lib._plot_data, position.new_closed_trades

                # Save equity data if we have a writer
                if is_strat and self.equity_writer and position:
                    for trade in position.new_closed_trades:
                        trade_num += 1  # Start from 1
                        self.equity_writer.write(
                            trade_num,
                            trade.entry_bar_index,
                            "Entry long" if trade.size > 0 else "Entry short",
                            trade.entry_id,
                            string.format_time(trade.entry_time),  # type: ignore
                            trade.entry_price,
                            abs(trade.size),
                            trade.profit,
                            f"{trade.profit_percent:.2f}",
                            trade.cum_profit,
                            f"{trade.cum_profit_percent:.2f}",
                            trade.max_runup,
                            f"{trade.max_runup_percent:.2f}",
                            trade.max_drawdown,
                            f"{trade.max_drawdown_percent:.2f}",
                        )
                        self.equity_writer.write(
                            trade_num,
                            trade.exit_bar_index,
                            "Exit long" if trade.size > 0 else "Exit short",
                            trade.exit_id,
                            string.format_time(trade.exit_time),  # type: ignore
                            trade.exit_price,
                            abs(trade.size),
                            trade.profit,
                            f"{trade.profit_percent:.2f}",
                            trade.cum_profit,
                            f"{trade.cum_profit_percent:.2f}",
                            trade.max_runup,
                            f"{trade.max_runup_percent:.2f}",
                            trade.max_drawdown,
                            f"{trade.max_drawdown_percent:.2f}",
                        )

                # Clear plot data
                lib._plot_data.clear()

                # Call the progress callback
                if on_progress:
                    assert lib._datetime is not None
                    on_progress(lib._datetime.replace(tzinfo=None))

                # Update bar index
                self.bar_index += 1
                # It is no longer the first bar
                barstate.isfirst = False

            if on_progress:
                on_progress(datetime.max)

        except GeneratorExit:
            pass
        finally:  # Python reference counter will close this even if the iterator is not exhausted
            # Close the plot writer
            if self.plot_writer:
                self.plot_writer.close()
            # Close the equity writer
            if self.equity_writer:
                self.equity_writer.close()

    def run(self, on_progress: Callable[[datetime], None] | None = None):
        """
        Run the script on the data

        :param on_progress: Callback to call on every iteration
        :raises AssertionError: If the 'main' function does not return a dictionary
        """
        for _ in self.run_iter(on_progress=on_progress):
            pass