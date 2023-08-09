# konbini

おまえはもうショットいる。なに？！

Opinionated wrapper for Autodesk Shotgun I mean [ShotGrid Python API](https://github.com/shotgunsoftware/python-api)
because the API usage requirements is 便利じゃないでしょう？

> コンビニね～ As there is an existing PyPI project using **_konbini_** name, this repo project name
> on PyPI will be **konbinine**.

## How to Use

> For Python 3.8 and newer! While Autodesk made **shotgun_api3** to be compatible with Python 2 and 3, **konbinine**
> uses `dataclass` that is only available in Python 3.7 onwards. Starting with v0.1.6, Python 3.8 will be the minimum
> version due to the usage of TypedDict.

**konbinine** is designed to be used with web framework (such as Django, Flask, etc.) that interacts with ShotGrid. This
library has not been tested inside Digital Content Creation (DCC) software such as Maya, 3ds Max or Houdini.

Technically it should just work but that is outside the scope of this library.

### New Project

#### First time setup

1. Add `konbinine` to your project's `requirements.txt`.
2. ???
3. Profit (in improving code readability and debugging)

#### Using konbinine

I recommend configuring the environment variables before running the following code.

Set it using your `.env` file or through the shell session etc.

```shell
# if your studio subscribed to Shotgun prior to the ShotGrid rename, the URL should
# looks like https://yourstudioname.shotgunstudio.com or something 
KONBINI_BASE_URL=https://yourstudioname.shotgrid.autodesk.com
KONBINI_SCRIPT_NAME=YOURSHOTGRIDAPISCRIPTNAMEHERE
KONBINI_API_KEY=YOURSHOTGRIDAPIKEYHERE
```

```python
from konbinine import Konbini
from konbinine.enums import SgEntity

kon = Konbini()
booking_schemas = kon.get_sg_entity_schema_fields(SgEntity.BOOKING)
# whatever booking schemas results here
```

### Existing Project that Uses shotgun_api3

You will need to... rewrite/refactor your code to use **konbinine**! Pretty much the main reason why **konbinine** was
created is to improve the Developer Experience (DX) when interacting with ShotGrid.

## Quickstart for Developers

```commandline
pip install -r requirements.txt
```

## Extending konbinine

Coming soon!

## TODO

1. Implement `Sequence` dataclass
2. Handle Image/Movie upload gracefully (currently for Project entity only)
