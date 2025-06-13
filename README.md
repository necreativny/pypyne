# pypyne
it's a dirty patch for [pynecore](https://github.com/PyneSys/pynecore) to run it from python instead of running it with pyne cli

to use it, put `custom_script_runner.py` in your project and import/use like in examples(pynecore should be installed properly, it's a patch on top of pynecore)

# examples
Examples naming: <input_option>_<output_option>.py
* ohlcv_stdout.py -- simplest example, shows when you want to read data from ohlcv file but control the output
* csv_stdout.py -- example that shows how to use it with custom input and custom output. Shows how to create iterator to pass custom input data

# notes:
* `custom_script_runner.py` is a copy of pynecores src/pynecore/core/script_runner with added `fork_runner` func