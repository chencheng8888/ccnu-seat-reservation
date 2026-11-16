# 排查

## 凭据

- `not_configured`：让用户运行 `bin/ccnu login`（默认浏览器登录页；无浏览器时加 `--tty`）。
- `invalid_credentials`：CAS 拒绝学号或密码；确认后让用户重试。
- 凭据文件：`~/.config/ccnu-seat-reservation/config.json`（0600）。
- 环境变量 `CCNU_STUID` / `CCNU_PASSWORD` 优先于文件，适合 CI。

## Session

- `session_expired`（上游 code 20002/20003）：客户端会清缓存、重新登录并重试一次。
- 重试后仍失败时，用 `bin/ccnu me --json` 确认登录是否可用。
- HMAC 请求头由客户端自动生成；排查时不要手工构造请求。

## 窗口

- `invalid_window` 的 message 会说明是步长还是时长问题。
- `bin/ccnu rules --json` 给出 `step_minute`、`max_minute`、`future_make_day`。
- 日期必须在 `bin/ccnu catalog --json` 的 `dates` 里。

## 风控与 capToken

- 当前 `capToken` 固定为字面量 `"capToken"`。
- 如果上游要求行为验证，`freeBook` 会返回 `api_error`；此时请用户在官方页面完成预约。

## 上游不可用（夜间关闭）

- 403/503 映射为 `upstream_blocked`：学校可能在夜间关闭预约系统。
- CAS 域名可能仍然可达，这不代表预约系统可用。
- 把情况告诉用户，约定白天再试；不要连续重试。
- `login` 在这种情况仍会保存凭据，`verification` 为 `unavailable`，白天自动验证。

## 网络

- 失败一次就停，向用户说明；不要高频轮询或并行重试。
