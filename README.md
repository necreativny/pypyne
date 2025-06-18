# pypyne
it's a dirty patch for [pynecore](https://github.com/PyneSys/pynecore) to run it from python instead of running it with pyne cli

to use it, put `custom_script_runner.py` in your project and import/use like in examples(pynecore should be installed properly, it's a patch on top of pynecore)

# custom_script_runner_preload_script.py
This is another version of `custom_script_runner` that you use if you want to pre-load pyne-indicator and then just run it.
You use it like this:
```python
from custom_script_runner_preload_script import fork_runner, import_script

script_module = import_script(indic_path)
fork_runner(script_module, ohlcv_iter, inputs)
```

# examples
Examples naming: <input_option>_<output_option>.py
* ohlcv_stdout.py -- simplest example, shows when you want to read data from ohlcv file but control the output
* csv_stdout.py -- example that shows how to use it with custom input and custom output. Shows how to create iterator to pass custom input data

# notes:
* last_bar_index most likely doesn't work properly (in fork_runner it's inited with 0 when it should be inited with input data size)
* `custom_script_runner.py` is a copy of pynecores src/pynecore/core/script_runner with added `fork_runner` func