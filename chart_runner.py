from typing import Iterable, Iterator, Callable, TYPE_CHECKING, Any
from types import ModuleType
import sys
from pathlib import Path
from datetime import datetime, UTC

from pynecore.types.ohlcv import OHLCV

from pynecore.types import script_type

if TYPE_CHECKING:
    from zoneinfo import ZoneInfo
    from pynecore.core.script import script
    from pynecore.lib.strategy import Trade

__all__ = [
    'import_script',
    'ChartRunner',
]


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
        from .. import lib

    lib.bar_index = lib.last_bar_index = bar_index

    lib.open = ohlcv.open
    lib.high = ohlcv.high
    lib.low = ohlcv.low
    lib.close = ohlcv.close

    lib.volume = ohlcv.volume

    lib.hl2 = (lib.high + lib.low) / 2.0
    lib.hlc3 = (lib.high + lib.low + lib.close) / 3.0
    lib.ohlc4 = (lib.open + lib.high + lib.low + lib.close) / 4.0
    lib.hlcc4 = (lib.high + lib.low + 2 * lib.close) / 4.0

    dt = lib._datetime = datetime.fromtimestamp(ohlcv.timestamp, UTC).astimezone(tz)
    lib._time = lib.last_bar_time = int(dt.timestamp() * 1000)  # PineScript representation of time


def _reset_lib_vars(lib: ModuleType):
    """
    Reset lib variables to be able to run other scripts
    :param lib:
    :return:
    """
    if TYPE_CHECKING:  # This is needed for the type checker to work
        from .. import lib
    from pynecore.types.source import Source

    lib.open = Source("open")
    lib.high = Source("high")
    lib.low = Source("low")
    lib.close = Source("close")
    lib.volume = Source("volume")
    lib.hl2 = Source("hl2")
    lib.hlc3 = Source("hlc3")
    lib.ohlc4 = Source("ohlc4")
    lib.hlcc4 = Source("hlcc4")

    lib._time = 0
    lib._datetime = datetime.fromtimestamp(0, UTC)

    lib._lib_semaphore = False

    lib.barstate.isfirst = True
    lib.barstate.islast = False



class ScriptModule:
    def __init__(self, script_path: Path, script_inputs: dict[str, Any]):
        """
        Initialize the script module
        :param script_path: The path to the script to run
        :param script_inputs: Inputs to pass to pyne script: {"src": "close", "length": 20,}

        :raises ImportError: If the script does not have a 'main' function
        :raises ImportError: If the 'main' function is not decorated with @script.[indicator|strategy|library]
        """
        self.module = import_script(script_path)
        self.script = self.module.main.script
        self.inputs = script_inputs
    def execute_bar(self):
        return self.module.main(**self.inputs)


class ChartRunner:
    """
    Chart runner
    """

    __slots__ = ('script_module', 'script', 'ohlcv_iter', 'bar_index', 'tz')

    scripts_modules = {}

    def __init__(self, scripts: list[tuple[Path, dict[str, Any]]], ohlcv_iter: Iterable[OHLCV]):
        """
        Initialize the chart runner

        :param scripts: script to run: path to script, script_inputs
        :param ohlcv_iter: Iterator of OHLCV data
        """
        for script_path, script_inputs in scripts:
            script_name = script_path.name[:-3]
            self.scripts_modules[script_name] = ScriptModule(script_path, script_inputs)

        self.ohlcv_iter = ohlcv_iter
        self.bar_index = 0

        from zoneinfo import ZoneInfo
        self.tz: ZoneInfo = ZoneInfo("UTC")

    # noinspection PyProtectedMember
    def run_iter(self, on_progress: Callable[[datetime], None] | None = None) \
            -> Iterator[tuple[OHLCV, dict[str, Any]] | tuple[OHLCV, dict[str, Any], list['Trade']]]:
        """
        Run the script on the data

        :param on_progress: Callback to call on every iteration
        :return: Return a dictionary with all data the sctipt plotted
        :raises AssertionError: If the 'main' function does not return a dictionary
        """
        from pynecore import lib
        from pynecore.lib import _parse_timezone, barstate, string
        from pynecore.core import function_isolation
        from pynecore.core import script

        # Reset bar_index
        self.bar_index = 0
        # Reset function isolation
        function_isolation.reset()

        # Clear plot data
        lib._plot_data.clear()

        def execute_script_bar(script_id: str) -> dict[str, dict[str, Any]]:
            self.script_module = self.scripts_modules[script_id].module
            self.script = self.scripts_modules[script_id].script
            lib._script = self.script

            # Reset function isolation
            function_isolation.reset_step()

            # Execute registered library main functions before main script
            lib._lib_semaphore = True
            for library_title, main_func in script._registered_libraries:
                main_func()
            lib._lib_semaphore = False

            # Run the script
            indic_values = self.scripts_modules[script_id].execute_bar()

            return indic_values

        try:
            for candle in self.ohlcv_iter:
                # Update lib properties
                _set_lib_properties(candle, self.bar_index, self.tz, lib)

                res: dict[str, dict[str, Any]] = {}
                for script_id in self.scripts_modules:
                    res[script_id] = execute_script_bar(script_id)
                yield res
                
                _reset_lib_vars(lib)

                # Update bar index
                self.bar_index += 1
                # It is no longer the first bar
                barstate.isfirst = False
        except GeneratorExit:
            pass
        finally:  # Python reference counter will close this even if the iterator is not exhausted        
            # Reset library variables
            _reset_lib_vars(lib)
            # Reset function isolation
            function_isolation.reset()