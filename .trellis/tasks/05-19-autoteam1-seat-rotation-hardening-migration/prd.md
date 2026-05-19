# autoteam-1 seat rotation hardening migration

## Goal

将 `D:\Desktop\autoteam-1\AutoTeam` 中围绕 Team 席位轮换、注册链路、运行态校验、CPA 同步防护和资源治理的一系列优化，经过差异审计后迁移到当前项目 `D:\Desktop\AutoTeam`。目标不是机械照搬，而是吸收目标仓库已验证有效的设计，并按当前项目现有状态机、注册栈、多母号调度和运行约束做适配性改善。

## What I Already Know

* 用户明确要求走 `$trellis-brainstorm`，本轮先规划和收敛 PRD，不直接改业务代码。
* 当前项目已有大量相关 in-progress Trellis 任务；本任务必须避免把无关 WIP 混入实现。
* 当前仓库已吸收不少目标仓能力：3-seat clamp、runtime validation、`runtime_resources`、IPv6 pool/proxy、CLIProxy health、Docker/runtime hardening、multi-master scaffold。
* 目标仓最新值得迁移的剩余能力集中在：`ROTATE_SKIP_REUSE` 默认跳过旧号复用、replaceable pool blocker 判定、满员时 remove-before-create、每个新 child 的 operational validation、更细的 auto-check action 分流、rotate heartbeat / duration fuse、以及 direct signup race 的真实接入。
* 当前项目和目标项目已经明显分叉。`api.py`、`manager.py`、`cpa_sync.py` 和 `test_api_status.py` 仍有大差异，不能整文件覆盖。

## Requirements

* 以当前项目为主线迁移，不覆盖现有 `RegisterPathRotator`、多 provider mail fallback、SignupProfile 复用、Playwright cleanup、multi-master scaffold、CPA delete guard 和前端状态面板。
* 保持单 Team 硬约束：`1 owner + 2 managed children = 3 seats`，不得通过 create-before-remove 或临时超席位绕过。
* 将目标仓的“不可用但占席 child”概念适配到当前 `STATUS_AUTH_INVALID` / account-state 语义，识别 missing-auth、auth-error、auth-retry paused、exhausted、auth-invalid 等 blocker。
* 当 Team 已满但存在可替换 blocker 或确认不可用 child 时，必须先远端移除旧 child，确认 capacity 后再创建 replacement。
* 新建 child 不能只以“创建成功”算成功；需验证远端 member 存在、本地 auth 文件存在、Codex quota/auth 可用，再计入可用 pool。
* 自动巡检需要区分至少四类动作：低额度轮换、真实 seat shortage 补位、auth repair、超员 cleanup；cooldown 只限制低额度抖动，不能阻止真实缺席补位或确认无额度占席替换。
* 长任务需要可观测进度：rotate/fill 关键阶段应有 heartbeat 或等价 progress 标记；单次 rotate 需要 duration fuse，避免和 watchdog/recovery 周期互相撞车。
* CPA/CLIProxyAPI 同步必须继续采用 delete guard。degraded pool、active list 不完整、远端列表读取失败时不得删除远端 auth。
* 若纳入 direct signup race，必须受当前 multi-master browser budget 约束，并保留当前注册路径轮换与 provider fallback。

## Acceptance Criteria

* [x] 研究记录明确标注当前已吸收、仍缺失、需适配、不能覆盖的目标仓能力。
* [x] 实现前选定 MVP slice，并把不进入本轮的迁移项列入 Out of Scope。
* [x] 若进入实现，新增/更新测试覆盖：3-seat cap、remove-before-create、protected local credential guard、replaceable blocker reason、auto-check shortage/auth-repair/cleanup/cooldown 分流、runtime validation degraded/failed 语义。
* [x] 若实现 child validation，测试必须证明新 child 未通过远端/auth/quota 验收时不会被计入完成，并会释放或标记为待处理。
* [x] 若实现 direct signup race，测试必须证明 `DIRECT_REGISTER_PARALLEL` 被实际传入注册路径，且高内存/低 budget 时自动降级。
* [x] 运行 `ruff`、相关 `pytest`，并在需要时用本地 API/status/task 证据确认运行态字段。
* [x] 不修改、提交或回滚与本任务无关的既有未提交 WIP。

## Research References

* [`research/current-vs-autoteam1-seat-rotation.md`](research/current-vs-autoteam1-seat-rotation.md) — re-verified current vs target migration notes and recommended slices.

## Technical Approach

### Approach A: Safe rotation core (Recommended)

先迁移目标仓的轮换安全核心：blocker 分类、remove-before-create、managed child validation、auto-check action 分流、cooldown 语义、heartbeat 和 duration fuse。保留现有注册栈和 multi-master scaffold，不在同一 slice 接入 direct signup race。

Pros:

* 最贴近用户说的“轮换席位等一系列优化”。
* 风险集中在后端轮换/巡检，可用单元测试和局部 API 验证闭环。
* 避免同时引入 direct registration 并发导致 Playwright 资源风险放大。

Cons:

* 注册成功率/速度提升主要来自更准确的轮换和验证，不会立即获得目标仓 direct signup race 的吞吐收益。

### Approach B: Rotation core + direct signup race

在 Approach A 基础上同时迁移目标仓 `_race_chatgpt_signup` / `DIRECT_REGISTER_PARALLEL`，并接入当前 `RegisterPathRotator`、`cmd_fill` 和 multi-master browser budget。

Pros:

* 一次性覆盖轮换准确性和单账号注册吞吐。
* 与多母号并行调度的最终方向更接近。

Cons:

* 风险显著更高：Playwright 并发、邮箱 provider 限速、注册失败分类、全局任务锁都要一起验证。
* 更容易和现有 `05-18-multi-master-parallel-registration` 任务边界重叠。

### Approach C: Audit-only decomposition

本任务只产出迁移审计和拆分子任务，不进入实现。随后把 rotation core、direct signup race、multi-master parity 分别建子任务执行。

Pros:

* 最稳，不碰当前脏工作区。
* 适合用户希望先梳理多个 in-progress 任务关系时使用。

Cons:

* 不能立即改善当前运行态轮换效率和准确性。

## Decision (ADR-lite)

Context: 当前项目已经吸收了目标仓的一批低耦合能力，但仍缺目标仓最新的“占席 blocker → 先移后补 → 子号验收 → 细分巡检动作”闭环。整文件复制会破坏当前 Round 11/12 注册栈和多母号架构。

Decision: 选择 Approach B：Rotation core + direct signup race。

Consequences: 本轮同时解决席位轮换准确性和单账号注册吞吐。实现必须把 direct signup race 接入当前 `RegisterPathRotator` / `cmd_fill` / multi-master browser budget，而不能只暴露配置或结果字段。风险集中在 Playwright 并发、邮箱 provider 限速、注册失败归因和测试矩阵扩大，需要更宽的单元测试和至少一次资源预算降级验证。

## Out of Scope

* 本 brainstorm 阶段不直接修改业务代码。
* 不提高单 Team seat cap，不做 create-before-remove。
* 不整文件覆盖目标仓 `api.py`、`manager.py`、`cpa_sync.py`。
* 不使用会上传或删除远端 auth 文件的 `/api/sync` 作为 smoke test。
* 不重启或扰动当前 live container，除非后续实现阶段明确需要并经过验证窗口。
* 不自动创建新的 Team owner 母号；多母号并行仅复用当前已有/imported owner scaffold。

## Expansion Sweep

Future evolution:

* 本轮 rotation core 后，可以把 direct signup race 作为独立 slice 接到 multi-master browser budget。
* 后续多母号并行可复用同一 blocker/validation contract，但按 owner 分组运行。

Related scenarios:

* API `/api/status`、任务 `validation`、前端 PoolPage/TeamPage 需要继续展示同一套健康语义。
* CPA/CLIProxyAPI sync 和 account cleanup 必须共享 protected credential / delete guard 规则。

Failure and edge cases:

* Team count probe unknown、remote remove delayed、new child auth missing、quota API network_error、auth repair throttled、protected local credential、disabled account、external remote member。
* Windows 本地环境与 Docker runtime 对 Playwright/browser 资源限制不同，实现需保留降级和可观测日志。

## Technical Notes

* Task dir: `.trellis/tasks/05-19-autoteam1-seat-rotation-hardening-migration`
* Current repo: `D:\Desktop\AutoTeam`
* Target repo: `D:\Desktop\autoteam-1\AutoTeam`
* GitNexus 当前未索引 AutoTeam；Serena MCP 在本会话返回参数错误，本轮已记录回退到本地只读搜索。
* External search was used only to validate general SaaS lifecycle direction: remove/deprovision before replacement, preflight quota, idempotent retry, background reconciliation, audit logging.

## Implementation Notes

Date: 2026-05-19

Implemented Approach B in the current repo without whole-file copying from the target repo:

* Added `ROTATE_SKIP_REUSE` and `ROTATE_MAX_DURATION` config/env examples.
* Added replaceable pool blocker classification for `missing_auth`, `auth_error`, `auth_retry_*`, `auth_invalid`, `quota_exhausted`, and `orphan`, while preserving disabled/protected local credential seats.
* Wired remove-before-create semantics into `cmd_rotate`: replaceable blockers are removed first, remote capacity is polled, then replacements are created.
* Added managed child operational validation after fill/rotate creation. A new child must have local auth, remote Team membership, and Codex quota above threshold before it counts as filled; failed validation releases/marks the child standby.
* Wired direct signup race through `create_account_direct(..., parallel=...)`, `create_new_account(..., parallel=...)`, `cmd_fill(..., direct_parallel=...)`, and multi-master owner workers. Race workers run signup-only attempts; only the winner is persisted/OAuth'd.
* Added runtime downgrade for direct race based on memory ratio and live browser process count.
* Updated auto-check so cooldown/full-Team observations do not block rotation when replaceable local blockers exist.
* Updated backend specs for the direct signup race, child validation, and multi-master budget propagation contracts.

Verification:

* `python -m py_compile src/autoteam/manager.py src/autoteam/multi_master.py src/autoteam/config.py`
* `python -m ruff check src/autoteam/api.py src/autoteam/manager.py src/autoteam/multi_master.py src/autoteam/config.py tests/unit/test_api_status.py tests/unit/test_manager_rotate.py tests/unit/test_manager_fill.py tests/unit/test_free_registration_hardening.py tests/unit/test_multi_master.py tests/unit/test_reconcile_anomalies.py`
* `pytest -q tests/unit` -> `826 passed, 1 warning`

Runtime note: no live Docker container was restarted and `/api/sync` was not used as a smoke test.
