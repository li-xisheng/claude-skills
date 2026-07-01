<!--
Hooks 示例集。Hook 真正的价值不是「防止 Claude 做错事」，而是让整套 harness「自我进化」。
按需把对应片段并进 .claude/settings.json 的 "hooks" 字段。先挂一两个，别一次堆满。
路径 / 命令请按你的项目改。
-->

# Hooks 示例

Claude Code 的 hook 在特定事件点跑脚本：`PostToolUse`（工具调用后）、`SessionStart`（会话开始）、
`Stop`（会话结束）、`PreToolUse`（工具调用前）等。下面三个是 ROI 最高的。

## 1. PostToolUse — 写完代码自动格式化（防错型，但收益稳定）

抹平 Claude 偶尔遗漏的格式问题，避免 CI 因格式挂掉。

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "npx prettier --write \"$CLAUDE_FILE_PATHS\" 2>/dev/null || true" }
        ]
      }
    ]
  }
}
```

## 2. SessionStart — 按当前子目录注入模块 context（自进化型）

在 `payments/` 下就拉支付相关说明，在 `auth/` 下就换认证相关。让 context 自动聚焦，而不是每次全量加载。

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/load-module-context.sh" }
        ]
      }
    ]
  }
}
```

配套脚本 `.claude/hooks/load-module-context.sh`（示意）：

```bash
#!/usr/bin/env bash
# 根据启动目录输出该模块的额外 context（会被注入到会话）
case "$(basename "$PWD")" in
  payments) cat services/payments/CONTEXT.md 2>/dev/null ;;
  auth)     cat services/auth/CONTEXT.md 2>/dev/null ;;
esac
```

## 3. Stop — 会话结束自动反思并回写 CLAUDE.md（最能自进化）

每次会话结束让模型反思「这次有没有反复犯的错？要不要沉淀进 CLAUDE.md？」——让 CLAUDE.md 被 Claude 自己持续打磨，
而不再需要你手动盯着维护。

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/reflect.sh" }
        ]
      }
    ]
  }
}
```

> 提醒：自动回写 CLAUDE.md 的 hook 很强，但也要纳入「200 行 / 删除测试」的纪律，否则会越长越肿。
> 把回写产物当作「待审草稿」，等定期纠偏（模式 C）时再合并/精简。
