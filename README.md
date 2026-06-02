# portfolio_alert

一个 Windows 下运行的轻量级长期 ETF 持仓监控器。当前版本是命令行后台运行程序，只做行情监控和重要提醒，不接入券商交易接口，也不会自动买卖。

## 功能

- 从本地私有的 `holdings.yaml` 读取持仓。
- 从 `config.yaml` 读取刷新间隔、交易时间、盈亏阈值、日志等配置。
- 使用 AKShare 获取 ETF 实时行情，不再请求 A股行情接口。
- 计算单只标的市值、浮动盈亏、收益率，以及组合汇总结果。
- 默认每 15 分钟刷新一次，启动时打印一次状态摘要，之后控制台静默运行。
- 当组合或单只标的亏损/盈利达到阈值时，通过 `win11toast` 弹出 Windows 通知。
- 交易日收盘后发送一次持仓日报。
- 每次成功刷新后保存 `data/latest_snapshot.json`，非交易时间或行情失败时可显示最近一次组合状态。
- 通知失败时自动退回到命令行输出。
- Traceback 不直接打印到终端，异常会写入日志并等待下一轮。

## 安装

建议使用 Python 3.10 或更高版本。你的 Conda base 环境可直接运行：

```powershell
cd portfolio_alert
conda activate base
python -m pip install -r requirements.txt
```

## 编辑持仓

项目提供 `holdings.example.yaml` 作为示例文件；真实持仓写在本地私有的 `holdings.yaml`，不要写进 Python 代码，也不要提交到 Git。

第一次使用时复制一份示例文件：

```powershell
Copy-Item holdings.example.yaml holdings.yaml
```

然后编辑 `holdings.yaml`。证券代码建议加引号，便于保留前导零。

```yaml
holdings:
  - code: "510300"
    name: "沪深300ETF"
    shares: 1200
    cost_price: 0
    enabled: true
    remark: "手动填写成本价"

  - code: "562500"
    name: "机器人ETF"
    shares: 5300
    cost_price: 0
    enabled: true
    remark: "手动填写成本价"

  - code: "159819"
    name: "人工智能ETF"
    shares: 2600
    cost_price: 0
    enabled: true
    remark: "手动填写成本价"
```

字段说明：

- `code`：证券代码，会按 6 位字符串处理并保留前导零。
- `name`：名称。
- `shares`：持有份额。
- `cost_price`：持仓成本价。若小于等于 0，程序会提示补充成本价，但不会崩溃。
- `enabled`：`true` 参与计算，`false` 忽略。
- `remark`：备注。

新增持仓时在 `holdings:` 下添加一项即可；临时忽略某只标的时把 `enabled` 改为 `false`。

如果启动时看到：

```text
未找到 holdings.yaml。
请复制 holdings.example.yaml 为 holdings.yaml，并填写真实持仓信息。
```

说明还没有创建本地真实持仓文件，按上面的复制命令处理即可。

## 编辑配置

配置写在 `config.yaml`。如果文件缺失，程序会自动生成默认配置。

```yaml
refresh_interval_sec: 900

trading_time:
  morning_start: "09:30"
  morning_end: "11:30"
  afternoon_start: "13:00"
  afternoon_end: "15:00"
  skip_weekends: true

alert:
  total_loss_threshold: -500
  single_loss_threshold: -300
  total_profit_threshold: 500
  single_profit_threshold: 300
  cooldown_sec: 300
  notify_on_recover: true

console:
  silent: true
  show_startup_summary: true
  show_non_trading_message: true
  show_portfolio_each_refresh: false
  startup_quote_timeout_sec: 8

daily_report:
  enabled: true
  report_time: "15:05"
```

亏损阈值使用负数，盈利阈值使用正数。比如组合总浮亏小于等于 `-500` 元时触发组合亏损提醒；组合浮盈大于等于 `500` 元时触发组合盈利提醒。

## 运行

```powershell
cd portfolio_alert
conda activate base
python run.py
```

启动后会立即打印一次当前监控状态，包括是否交易时间、启用持仓数量、刷新频率、当前组合状态和下一次刷新时间。之后默认静默运行，不会每轮刷屏。重要提醒会弹出 Windows 通知；运行明细写入 `logs/portfolio_alert.log`。

如果当前不是交易时间，程序会优先显示 `data/latest_snapshot.json` 中的最近一次组合状态，不主动等待实时行情接口。交易时间启动时会尝试获取一次实时行情，但最多等待 `console.startup_quote_timeout_sec` 秒；超时后会显示缓存并让后台循环稍后继续刷新。非交易时段运行期间不会每分钟重复刷屏。

### 命令行参数

只查看一次组合状态，不进入长期后台循环：

```powershell
python run.py --once
```

强制请求实时行情，不读取本地缓存：

```powershell
python run.py --once --no-cache
```

调试时显示更详细的控制台日志：

```powershell
python run.py --debug
```

默认模式仍保持少打扰：启动时打印一次摘要，之后不周期性刷屏。

## 缓存快照

程序每次成功获取行情并完成组合计算后，会把最近一次组合状态保存到：

```text
data/latest_snapshot.json
```

该文件只保存在本地，不提交到 Git。非交易时间启动、行情接口失败或启动行情请求超时时，程序会优先显示这份缓存；如果缓存超过 7 天，会提示“缓存较旧，仅供参考”。

## Windows 开机自启动

可以创建一个 PowerShell 脚本，例如 `start_portfolio_alert.ps1`：

```powershell
cd E:\CodeLocal\StakeTool\portfolio_alert
conda activate base
python run.py
```

然后按 `Win + R`，输入 `shell:startup`，把该脚本的快捷方式放入启动文件夹。

也可以使用“任务计划程序”创建登录时运行的任务，程序选择 `powershell.exe`，参数示例：

```powershell
-ExecutionPolicy Bypass -File "E:\CodeLocal\StakeTool\portfolio_alert\start_portfolio_alert.ps1"
```

## 常见问题

**行情获取失败怎么办？**

先确认网络可用，并升级 AKShare：

```powershell
pip install -U akshare
```

AKShare ETF 接口偶尔会字段变化或短暂不可用，程序会记录日志并在下一轮继续重试。

**为什么非交易时间显示的是最近一次状态？**

因为非交易时间程序不会频繁请求实时行情，会优先显示最近一次成功获取的组合快照。

**通知不弹出怎么办？**

确认 Windows 通知没有被系统关闭，并检查 `win11toast` 是否安装成功：

```powershell
pip install -U win11toast
```

如果通知库不可用，程序会在命令行打印重要提醒内容。

**如何新增持仓？**

在 `holdings.yaml` 的 `holdings:` 下新增一项，填写 `code`、`name`、`shares`、`cost_price`，并把 `enabled` 设为 `true`。

**如何修改亏损提醒阈值？**

修改 `config.yaml` 中的：

```yaml
alert:
  total_loss_threshold: -500
  single_loss_threshold: -300
  total_profit_threshold: 500
  single_profit_threshold: 300
```

保存后重启程序。

## 测试

```powershell
cd portfolio_alert
conda activate base
python -m pytest tests -q
```
