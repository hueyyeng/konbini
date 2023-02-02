# konbini
おまえはもうショットいる。なに？！

Opinionated wrapper for Autodesk Shotgun I mean [ShotGrid Python API](https://github.com/shotgunsoftware/python-api) because the API usage requirements is 便利じゃないでしょう？

## How to Use

> For Python 3.7 and newer! While Autodesk made **shotgun_api3** to be compatible with Python 2 and 3, **konbini** uses `dataclass` that is only available in Python 3.7 onwards.

**konbini** is designed to be use with web framework (such as Django, Flask, etc) that interacts with ShotGrid. This library has not been tested inside Digital Content Creation (DCC) software such as Maya, 3ds Max or Houdini.

Technically it should just work but that is outside the scope of this library.

### New Project

1. Add `konbini` to your project's `requirements.txt`.
2. ???
3. Profit (in improving code readability and debugging)

### Existing Project that Uses shotgun_api3

You will need to... rewrite/refactor your code to use **konbini**! Pretty much the main reason why **konbini** was created is to improve the Developer Experience (DX) when interacting with ShotGrid.

## Quickstart for Developers

```commandline
pip install -r requirements.txt
```

## Extending konbini

Coming soon!
