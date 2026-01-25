# deep_reloader

[English Version](../README.md) | [日本語版](README.ja.md)

> [!WARNING]
> 本软件目前处于预发布阶段。API 可能会发生变化。

一个用于分析模块依赖关系并执行递归重载的 Python 库。专为 Maya 脚本开发设计，可即时反映模块变更。

## 功能特性

- **深度重载**：可重载任意深度层级的模块
- **AST 分析**：通过静态分析准确检测 from-import 语句
- **通配符支持**：支持 `from module import *`
- **相对导入支持**：正确处理包内的相对导入
- **循环引用支持**：正确重载 Python 中可运行的循环导入

## 安装

可以将包放置在 Python 路径中的任何位置。
本 README 以 Maya 常用的 scripts 文件夹为例进行说明。

```
~/Documents/maya/scripts/  (示例)
└── deep_reloader/
    ├── __init__.py
    ├── _metadata.py
    ├── deep_reloader.py
    ├── from_clause.py
    ├── import_clause.py
    ├── module_node.py
    ├── symbol_extractor.py
    ├── LICENSE
    ├── README.md
    └── tests/
```

## 使用方法

### 基本用法

```python
# 最简单的使用示例
from deep_reloader import deep_reload
deep_reload(your_module)
```

### 日志配置

在开发或调试时，可以启用详细的日志输出：

```python
from deep_reloader import deep_reload, setup_logging
import logging

# 设置日志级别（影响所有 deep_reloader 日志）
logger = setup_logging(logging.DEBUG)   # 详细调试信息

# 也可以使用返回的 logger 直接输出日志
logger.info("deep_reloader 日志配置完成")

# 然后正常使用
deep_reload(your_module)
```

**日志级别说明：**
- `logging.DEBUG`：显示包括 pycache 清理在内的详细信息
- `logging.INFO`：显示模块重载状态（默认）
- `logging.WARNING`：仅显示错误和警告

## 运行测试

**注意：测试必须使用 pytest 运行。不支持在 Maya 内部运行。**

本项目的测试为 pytest 专用。请在开发环境中使用 pytest 运行测试。

```shell
# 导航到仓库根目录（示例）
cd ~/Documents/maya/scripts/deep_reloader

# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/integration/test_absolute_import.py -v

# 更详细的输出
pytest tests/ -vv

# 简洁输出
pytest tests/ -q
```

### 已验证环境

**测试开发环境（非 Maya）：**
- Python 3.11.9+（在当前开发环境中已验证）
- pytest 8.4.2+（运行测试所需）

**注意**：以上是用于库测试和开发的环境。与 Maya 执行环境不同。支持的 Maya 版本尚未最终确定。

## 限制事项与已知问题

### isinstance() 失败（Python 语言规范限制）

重载前创建的实例在重载后的类上进行 `isinstance()` 检查会失败。这是 Python 语言规范的限制，是所有重载系统的共同问题。

**原因**：重载后，类对象 ID 发生变化。

**示例**：
```python
# 重载前
my_class = MyClass()
isinstance(my_class, MyClass)  # True

deep_reload(MyClass)         # 重载

isinstance(my_class, MyClass)  # False（my_class 是旧 MyClass 的实例，MyClass 是新类）
```

**应对措施**：
- 重载后重新创建实例
- 使用类名进行字符串比较（`type(my_class).__name__ == 'MyClass'`）
- 重启 Maya

### 不支持 import 语句（按设计）

不支持 `import xxx` 样式的依赖关系。

**原因**：在重载时恢复自动添加到父模块的属性会增加复杂性。

**支持的形式**：仅支持 from-import
- `from xxx import yyy` 样式
- `from .xxx import yyy` 样式
- `from . import yyy` 样式

### 仅重载单个包（按设计）

`deep_reload()` 仅重载与传入模块属于同一包的模块。

**原因**：防止重载内置模块（`sys` 等）和第三方库（`maya.cmds`、`PySide2` 等），以保持系统稳定性。

**示例**：运行 `deep_reload(myutils)` 将仅重载 `myutils` 所属包中的模块。

**开发多个自定义包时**：
如果包之间存在依赖关系，重载可能无法正常工作。建议使用单个包。
如果确实需要，请考虑依赖顺序多次调用 `deep_reload()`。
```python
# 需要重载多个包时（不推荐）
deep_reload(myutils)
deep_reload(mytools)
```

### 需要包结构（按设计）

`deep_reload()` 仅支持打包的模块。

**原因**：独立模块无法区分标准库和用户代码，存在意外重载系统模块的风险。

**不支持**：独立的 `.py` 文件（例如：`~/maya/scripts/my_tool.py`）

**对于独立模块**：使用标准的 `importlib.reload()`。

**使用多个模块时**：将它们打包（建议使用包含 `__init__.py` 的目录结构）。

## 发布状态

- ✅ 核心功能完成（from-import 支持）
- ✅ 测试套件
- ✅ 文档
- ✅ Maya 环境验证
- ✅ 循环导入支持
- 🔄 API 稳定化进行中
- 📋 增强调试日志
- 📋 性能优化和缓存

## 许可证

MIT License - 详情请参阅 [LICENSE](LICENSE) 文件。
