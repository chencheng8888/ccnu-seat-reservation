# CCNU 图书馆座位预约

CCNU 图书馆座位预约的 Python 客户端，同时是一个可安装的 agent skill：登录认证、馆舍/楼层/空间发现、空闲座位查询、预约和取消。

- 客户端：`ccnu_reservation/`，纯标准库，无需 `pip install`
- Skill：根目录 `SKILL.md`，让支持 Agent Skills 的 agent 用自然语言完成预约
- 协议：对接新版预约系统（`https://kjyy.ccnu.edu.cn/rem` + `/jsq`），实现细节见代码与测试

## 范围

面向**个人 agent**：单用户、凭据在本机、需要可交互终端。多用户校园 agent 的服务端接入不在本仓库范围内；届时复用 `ccnu_reservation/` 加服务层，见 `docs/adr/0002-personal-agent-scope.md`。

## 安装

仓库根目录就是 skill 目录，任选一种：

```bash
# 支持 Agent Skills 的宿主（Claude Code、Codex、Cursor 等）
npx skills add chencheng8888/ccnu-seat-reservation

# Skills Manager
skills-manager-cli skills install https://github.com/chencheng8888/ccnu-seat-reservation.git
skills-manager-cli skills deploy ccnu-seat-reservation --agent claude_code

# 手动
git clone https://github.com/chencheng8888/ccnu-seat-reservation.git ~/.claude/skills/ccnu-seat-reservation
```

想要一个全局 `ccnu` 命令：

```bash
./scripts/install.sh
export PATH="$HOME/.local/bin:$PATH"
```

不需要 Python 第三方依赖；要求 Python 3.9+。

## 首次使用

默认打开本机浏览器登录页；密码只在网页里输入，不经过终端输出或对话：

```bash
bin/ccnu login
```

没有浏览器，或想留在终端时，用 `--tty` 隐藏输入：

```bash
bin/ccnu login --tty
```

从密码管理器注入：

```bash
bin/ccnu login --stu-id 20210001 --password-stdin
```

登录页只监听 `127.0.0.1`，一次性使用。如果 agent 跑在远端机器上，浏览器访问不到那台机器的 loopback，请改用 `--tty` 或 `--password-stdin`。

再次登录时学号会预填（脱敏显示），只需要敲密码。也可以只用环境变量：`CCNU_STUID` / `CCNU_PASSWORD`。

Session Token 在本机缓存 5 分钟（`~/.cache/ccnu-seat-reservation/session.json`，0600），同一个预约流程只登录一次；上游返回 Session 过期时自动重登并重试。

## 常用命令

```bash
bin/ccnu status --json
bin/ccnu spaces --date 2026-11-18 --start 12:30 --end 13:30 --json
bin/ccnu seats --space n1m --date 2026-11-18 --start 12:30 --end 13:30 --json
bin/ccnu reserve --seat <seat-id> --date 2026-11-18 --start 12:30 --end 13:30 --json   # 演练
bin/ccnu reserve --seat <seat-id> --date 2026-11-18 --start 12:30 --end 13:30 --yes --json
bin/ccnu cancel <reservation-id> --yes --json
```

`reserve` 和 `cancel` 默认只演练；加 `--yes` 才真实调用上游。

## 测试

```bash
python3 -m unittest discover -s tests
```

只读集成测试（不创建预约）：

```bash
CCNU_INTEGRATION=1 python3 -m unittest tests.test_integration -v
```

## 安全说明

1. 学号、密码、Session Token、HMAC key 不打印、不写日志。
2. 凭据文件权限 0600；密码优先在终端交互输入。
3. 真实预约与取消都要求用户明确确认。
4. 避免高频请求，遵守图书馆的预约规则。
5. 所有时间按 `Asia/Shanghai` 处理。

## 已知限制

- 学校可能在夜间关闭预约系统；此时命令返回 `upstream_blocked`，白天再试。`login` 仍会保存凭据（`verification: unavailable`）。

## 免责声明

本项目仅供学习和研究使用。开发者不对因使用本项目产生的任何问题负责。
