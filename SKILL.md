---
name: ccnu-seat-reservation
description: 预约华中师范大学（CCNU）图书馆座位：查空位、预约、取消、首次配置。用户提到 CCNU/华师/南湖或主馆图书馆，或要看空闲座位、订座、退座时使用。
---

# CCNU 图书馆座位预约

用本 skill 目录下的 `bin/ccnu` 完成查空位、预约和取消。命令一律加 `--json`，按 JSON 字段决策。

## 命令

| 命令 | 用途 |
| --- | --- |
| `bin/ccnu status --json` | 凭据是否已配置 |
| `bin/ccnu rules --json` | Step / Max Duration / 可约天数 |
| `bin/ccnu catalog --json` | 馆舍、楼层、可选日期 |
| `bin/ccnu spaces --date D --start HH:MM --end HH:MM [--building 名称] [--floor 名称] --json` | 楼层内各 Space 的空位数 |
| `bin/ccnu seats --space <code\|id\|名称> --date D --start HH:MM --end HH:MM --json` | 整个时段的空位 |
| `bin/ccnu reserve --seat <id> --date D --start HH:MM --end HH:MM [--yes] --json` | 预约；默认演练 |
| `bin/ccnu cancel <reservation-id> [--yes] --json` | 取消；默认演练 |
| `bin/ccnu last --json` | 最近预约 |

`catalog` 里的任何馆舍和楼层都可约：`--building` / `--floor` 指定（名称支持模糊匹配），Space 用 `seats --space <名称|id>`。`n1` / `n1m` / `n2` 只是南湖一楼开敞、一楼中庭、二楼开敞的快捷码；运行时以 `spaces` 的结果为准。

## 工作流

1. **准备。** 运行 `status --json`。`configured` 为 false 时，请用户运行 `<本 skill 目录>/bin/ccnu login`（默认打开本机浏览器登录页；无浏览器时用 `--tty`），密码在网页里输入，不经过对话；等他回「好了」。完成标准：`configured: true`。若登录返回 `verification: unavailable`，说明系统当前关闭，凭据已保存，稍后再约。
2. **定时段。** 把用户的话解析为 Asia/Shanghai 的 `--date YYYY-MM-DD --start HH:MM --end HH:MM`。完成标准：`spaces --json` 成功返回，即窗口已通过 Step 与 Max Duration 校验。
3. **选 Space。** 用户没说馆舍/楼层时先问清（主馆还是南湖），不要默认南湖。读 `spaces --json` 的 `seat_free` / `seat_total`，落到一个 Space；多个候选时列出名称和 id 让用户选。完成标准：确定一个 Space。
4. **列空位。** 运行 `seats --json`，把 `label` 列表（可带 id）给用户；用户明确说「随便/第一个」才取第一个。完成标准：确定一个 seat id，或用户授权随便选。
5. **确认点（预约）。** 复述 Space、seat label、日期和起止时间，然后停。完成标准：用户对这次具体预约明确回复同意（原始消息已明确说「约」并授权选座的，视为同意）。
6. **下单。** 运行 `reserve ... --yes --json`。完成标准：返回 `reservation_id`；失败走下一节。

取消：`last --json` 找到记录 → 复述座位与时间 → 用户同意 → `cancel <id> --yes`。这是**确认点（取消）**。用户要求「约了立刻退」时，下单后可直接执行取消。

## 两个确认点

真实变更只发生在两次：预约前和取消前。每次先复述对象（座位、日期、时间），再等用户明确的「是」。其余情况只输出演练结果。

## 失败处理

`ok:false` 时读 `error.kind`：

- `not_configured` → 回到第 1 步。
- `invalid_credentials` → 请用户重新运行 `bin/ccnu login`。
- `session_expired` → CLI 已自动重登并重试一次；仍失败就原样重跑。
- `invalid_window` → 用 `rules --json` 核对步长和最长时长，再调整时间。
- `upstream_blocked` → 告诉用户系统当前不可用（学校可能在夜间关闭），约定稍后再试。
- `api_error` / `no_reservation_id` → 把 `message` 告诉用户，由用户决定下一步。
- `network_error` → 说明网络问题，等用户决定。

更多排查见 `references/troubleshooting.md`。
