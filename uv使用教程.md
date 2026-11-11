# uv 使用教程

> uv 是 Rust 写的极速 Python 包管理 / 虚拟环境工具，号称 `pip + virtualenv + pipx` 的合体。
> 它最重要的两个特点：**快**（并行下载、全局缓存）和**一个命令搞定环境 + 依赖**。
> 本文按 Windows + PowerShell 环境写，覆盖你之前踩过的所有坑。

---

## 1. uv 是什么？和 pip / conda 的关系

| 工具 | 干什么的 | 快吗 | 管不管 Python 版本 |
|------|---------|------|-------------------|
| `pip` | 装包 | 一般 | ❌ |
| `conda` | 装包 + 管环境 + 管 Python 版本 | 慢 | ✅ |
| `uv` | 装包 + 管环境 + 管 Python 版本 | 极快 | ✅ |

一句话：**uv 能做 pip 能做的所有事，还能顺便帮你管 Python 版本和虚拟环境，且快一个数量级。**

它有两种用法，务必分清（你之前用的是第一种）：

- **`uv pip ...`** —— 传统模式，等价于 pip，配合 `requirements.txt` 用。和你现在的习惯无缝衔接。
- **`uv add / sync / run ...`** —— 项目模式，配合 `pyproject.toml` 用，类似 poetry。更现代、更省心。

---

## 2. 安装 uv

**方式一（推荐，官方脚本）**，PowerShell 里运行：

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**方式二：用 pip 装**（你之前就是这么装的）：

```powershell
pip install uv
```

> ⚠️ 用 pip 装时，如果提示 `Defaulting to user installation`，说明装到了**用户级目录**，
> 需要把那个目录加进 PATH（就是当初 `uv` 命令找不到的原因）。目录长这样：
>
> ```
> C:\Users\你的用户名\AppData\Roaming\Python\PythonXXX\Scripts
> ```

装完验证：

```powershell
uv --version
# uv 0.x.x
```

---

## 3. 核心命令速查

### 3.1 管理 Python 版本

```powershell
uv python list          # 看本机已装的 Python
uv python install 3.11  # 自动下载安装某个版本的 Python（不用自己去官网下）
uv python install 3.12
```

### 3.2 创建虚拟环境

```powershell
uv venv                 # 创建 .venv（用当前默认 Python）
uv venv myenv           # 指定环境目录名
uv venv --python 3.11   # 指定 Python 版本（没有会自动装）
uv venv --seed          # 顺便把 pip 也装进环境（默认不装 pip！）
```

> ⭐ **关键点**：`uv venv` 默认**不装 pip**，所以环境里没有 `pip.exe`。
> 这是你之前 `where pip` 找不到、以及 `pip` 命令撞到 Anaconda 的根因。
> 但**你根本不需要 pip**——用 `uv pip` 代替即可（见下）。

### 3.3 装包 / 卸载 / 查看

```powershell
uv pip install requests                       # 装到当前"已激活"的 venv
uv pip install --python .venv requests        # 显式装到指定 venv（无需先激活）
uv pip install requests==2.31.0               # 指定版本
uv pip install -r requirements.txt            # 按清单批量装
uv pip uninstall requests                     # 卸载
uv pip list                                   # 列出当前环境的包
```

> ⭐ **无需激活也能装**：`--python .venv` 直接指定目标环境，彻底避免"装错环境"。
> 你之前 `uv pip install --python .venv langchain-openai` 就是这个用法。

### 3.4 激活 / 退出环境

```powershell
.venv\Scripts\activate     # 激活（PowerShell）
deactivate                 # 退出
```

激活后命令行前缀会出现 `(.venv)`，这就是环境名（之前 `myagent` 前缀的来源，见 `pyvenv.cfg` 的 `prompt` 字段）。

### 3.5 项目模式（更推荐的现代用法）

```powershell
uv init myproject          # 初始化一个项目，生成 pyproject.toml
cd myproject
uv add requests            # 加依赖：写进 pyproject.toml + 立刻装好
uv add "langchain-openai>=0.1"
uv remove requests         # 移除依赖
uv sync                    # 按 pyproject.toml 同步环境（别人 clone 后一键还原）
uv run python main.py      # 在项目环境里运行脚本（不用手动激活）
uv run --with httpx python -c "import httpx"   # 临时带某个包运行
```

---

## 4. 两种推荐工作流

### 工作流 A：最小改动（延续你现在的习惯）

适合：临时跑脚本、学习、已有 `requirements.txt`。

```powershell
uv venv                                  # 建环境
uv pip install --python .venv python-dotenv langchain-openai langchain-community
uv pip list                              # 确认装对
.venv\Scripts\python test.py             # 用环境里的 python 跑（或先 activate）
```

### 工作流 B：正式项目（推荐）

适合：长期维护的项目，需要和同事共享、可复现。

```powershell
uv init myagent                          # 建项目
cd myagent
uv add langchain-openai python-dotenv    # 依赖自动记录
uv run python test.py                    # 直接跑，环境自动就绪
```

> 两者本质一样，B 只是把"环境 + 依赖清单"自动化管理了。学习阶段用 A 够用，进项目用 B。

---

## 5. 你之前踩过的坑（一次性讲清）

| 现象 | 原因 | 解决 |
|------|------|------|
| `uv` 命令找不到 | 装到了用户目录，没加 PATH | 把 Scripts 目录加进用户 PATH，**重启终端/VSCode** |
| VSCode 里不认 uv，cmd 里认 | VSCode 的进程环境是旧的 | 完全关闭并重开 VSCode |
| `pip` 装包撞到 Anaconda | `uv venv` 没装 pip，`pip` 解析到 conda 的 | 用 `uv pip install --python .venv` 代替 |
| venv 里是"空壳"没包 | 之前用 pip 装到别处了，没装进这个 venv | 装包时显式指定 `--python .venv` |
| 环境名前缀 `myagent` | `pyvenv.cfg` 里 `prompt = myagent` | 正常现象，是环境名 |

### 一个必懂的心智模型

**"装包" 永远是装进"某个具体环境"，不是装进"这台电脑"。**

所以判断"包装对没有"，永远是看**当前激活的是哪个环境**，再用 `uv pip list` 确认。
之前"撞到 conda"的本质：命令叫了 `pip`，系统把 conda 的 pip 当成目标，包就装进 conda 了。

---

## 6. 常用技巧

```powershell
uv cache clean             # 清缓存（删掉重下的临时文件）
uv cache dir               # 看缓存目录在哪
uv tree                    # 看依赖树
uv --help                  # 顶层帮助
uv pip install --help      # 子命令帮助
```

### uv 和 conda 怎么配合？

不用纠结二选一。常见做法：

- **只用 uv**：`uv venv` + `uv pip`，完全替代 conda 的环境功能（更轻更快）。
- **conda 装 Python 本体，uv 管环境和包**：conda 只负责提供多个 Python 版本，环境交给 uv。
- **别混着来**：不要在一个环境里既用 `conda install` 又用 `uv pip install` 装包，会乱。

---

## 7. 一句话总结

- 建环境：`uv venv --python 3.11`
- 装包：`uv pip install --python .venv 包名`
- 跑代码：`.venv\Scripts\python xx.py`（或先 `activate`）
- 忘了 pip：所有 `pip xxx` 都能换成 `uv pip xxx`
- 进项目：`uv init` → `uv add 包` → `uv run python xx.py`
