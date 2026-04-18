# WebCoEvo

WebCoEvo 是一个自包含的 Linkding XVR 评测 runner，用来在 hardv3 drift 网站上测试 cross-version reflection rules。

它从更大的 `webAgentBenchmark` 研究仓库中剥离出来，目标是让 Linkding Focus20 和 TaskBank36 实验可以在一个小而可审计的仓库里运行，不再依赖历史 `webevolve/` 框架和多代 harness。

英文文档见 [README.md](README.md)。

## 课程项目

WebCoEvo 是 **UMich EECS545 Winter 2026** 的课程项目，由 Chenming Ge、Chengyang Shi、Yifei Xu、Yuxiang Yang 和 Binglin Zhong 完成，项目在 Honglak Lee 教授指导下开展，并得到 Violet Fu 的 mentoring。

## 仓库包含什么

- `linkding_xvr_minimal/`: Python runner、BrowserGym task wrapper、UI-TARS AgentLab adapter、prompt 注入、rule 选择、reset/login 处理、legacy eval/trace 导出。
- `configs/`: Focus20 smoke/full 和 TaskBank36 full 的 hardv3 task JSON。
- `rulebooks/`: V2.4/V2.5/V2.6 cross-version reflection rulebooks，以及 `expel_official_v2.json`。
- `scripts/singularity/`: Linkding drift runtime helper 和 hardv3 variant 模板文件。
- `websites/`: Linkding 三代网页资产：原版 control 快照、第一次修改网页、hardv3 release-grounded 网页。
- `scripts/verify_trace_rules.py`: trace 审计脚本，用来确认 XVR 和 ExpeL rules 真的进入 trace。
- `slurm/`: smoke、full、hardv3 matrix submitter。
- `skills/`: 给 Codex/agent 使用的本仓库运行、监控、分析技能。
- `tests/`: metadata、rule selection、prompt injection、export、reset、submitter 等单测。

运行时不需要旧的 `webAgentBenchmark` checkout。

## 架构

整体分四层：

1. Task 层：`tasks.py` 读取 raw JSON，并统一生成 `task_id`、`source_task_id`、`focus20_source_task_id`、`drift_type`、`variant`、`family`、`version`、`start_url`。
2. Rule 层：`rulebook.py` 和 `expel_rules.py` 负责读取、规范化、选择、渲染 XVR reflection rules 和 ExpeL-style task experience rules。
3. Browser/agent 层：`browser_task.py`、`benchmark.py`、`agentlab_agent.py`、`prompting.py` 注册 BrowserGym task，reset/login Linkding，注入 rules 到 prompt，解析 UI-TARS action，并运行 AgentLab。
4. Export/audit 层：`export.py` 输出 legacy eval/trace JSONL，把 preflight rule IDs 回填到 reset-error rows；`verify_trace_rules.py` 检查 trace 里是否有 rule 注入字段。

Singularity 脚本会启动本地 Linkding drift variant，把 task 的 start URL 改成本 job 的 localhost 端口，reset 数据，创建 baseline 用户，运行 Python runner，并做 trace audit。

## 网页资产

仓库里保留了三代 Linkding 网页：

- `websites/original/`: 干净 Linkding `1.45.0` control 的 HTML/PNG 快照。运行时 `control` variant 不挂载任何模板。
- `websites/first_modified/`: 第一版 vibe-coded drift 网页，从旧 commit `9879707` 恢复模板，并带上 4 月 3 日 before/after 截图。
- `websites/hardv3/`: 当前使用的 release-grounded hardv3 网页，包含模板覆盖、验证 HTML、截图和设计说明。

hardv3 运行时真正读取的路径仍然是 `scripts/singularity/linkding_drift/variants/`；`websites/hardv3/variant_templates/` 是一份便于 review 和迁移的归档副本。

## 环境准备

创建 Python 环境：

```bash
cd /path/to/WebCoEvo
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[benchmark,dev]'
```

在 UMich cluster 上，Slurm 脚本会加载 `python/3.11.5` 和 `singularity/4.x`。如果 Python 不在 `.venv/bin/python`，设置：

```bash
export PYTHON_BIN=/path/to/python
```

设置模型 endpoint：

```bash
export OPENAI_BASE_URL=http://your-openai-compatible-endpoint/v1
export OPENAI_API_KEY=...
export UITARS_MODEL=Qwen/Qwen3-VL-30B-A3B-Instruct
```

也可以放一个本地 `.env.umich`，Slurm 脚本会自动 source。不要提交密钥。

## HPC / Slurm 路线

这个仓库默认的正式评测路线仍然是 HPC：

- `slurm/` submitter
- `scripts/singularity/` runtime helper
- 共享 module 环境，例如 `python/3.11.5` 和 `singularity/4.x`

如果你要跑正式 full matrix、要让作业排队、或者要把 runtime 放到更合适的存储目录，这条路线最稳。

在当前 UMich 环境里，Slurm runner 会优先复用 `~/webAgentBenchmark/.venv/bin/python`。如果换机器或换环境，可以显式设置：

```bash
export PYTHON_BIN=/path/to/python
```

## 本地 Docker 路线

如果是在 Linux 或 macOS 本地机器上跑，就不要走 HPC 的 Singularity 路线，而是走 Docker：

- runner 镜像：`docker/Dockerfile.runner`
- compose 生成器：`scripts/docker/generate_local_compose.py`
- 单变体本地 smoke：`scripts/docker/local_smoke.sh`
- 顺序版本地 full matrix：`scripts/docker/local_matrix.sh`
- 详细说明：`docker/README.md`

警告：这个仓库里的 Docker 路线到现在为止从来没有被端到端实际测试过。它还没有作为一个验证过的本地 benchmark 路线跑通过，因此在把它用于正式实验或结果汇报之前，必须先做额外测试。

快速例子：

```bash
scripts/docker/local_smoke.sh preflight
```

```bash
OPENAI_API_KEY=... \
OPENAI_BASE_URL=http://host.docker.internal:8000/v1 \
VARIANT=access \
scripts/docker/local_smoke.sh smoke
```

```bash
OPENAI_API_KEY=... \
OPENAI_BASE_URL=http://host.docker.internal:8000/v1 \
TASK_FILE=configs/focus20_hardv3_full.raw.json \
RUN_PREFIX=local_focus20_full \
scripts/docker/local_matrix.sh
```

本地时间预算可以先按下面估：

- preflight：通常不到 1 分钟
- smoke：通常 2 到 15 分钟
- Focus20 full x 3 个 rulebook x 7 个 variant：通常半天到过夜
- TaskBank36 full x 3 个 rulebook x 7 个 variant：通常过夜到多天

这里只给 planning range，让本地用户自己决定要不要真的跑 full matrix。

## 本地检查

跑单测：

```bash
python3 -m pytest -q
```

只编译 tasks，不启动浏览器：

```bash
python3 -m linkding_xvr_minimal.runner \
  --task-file configs/focus20_hardv3_smoke.raw.json \
  --rulebook rulebooks/v2_6.json \
  --run-label focus20_smoke_compile \
  --compile-only
```

在 agent run 前检查 rule 注入：

```bash
python3 -m linkding_xvr_minimal.runner \
  --task-file configs/focus20_hardv3_smoke.raw.json \
  --rulebook rulebooks/v2_6.json \
  --run-label focus20_smoke_preflight_v26 \
  --preflight-rules-only \
  --fail-on-empty-xvr-rules \
  --expel-rule-file rulebooks/expel_official_v2.json \
  --expel-fidelity official_eval
```

期望：每个 task 都有非空 `preflight[].selected_rule_ids`，ExpeL 也有非空 `expel_preflight[].selected_rule_ids`。

## Smoke Run

提交一个 access task smoke：

```bash
RUN_LABEL=focus20_hardv3_smoke_access_xvr26_webcoevo_v1 \
EXPEL_RULE_FILE="$PWD/rulebooks/expel_official_v2.json" \
EXPEL_FIDELITY=official_eval \
sbatch slurm/run_smoke_access_singularity.slurm.sh
```

输出会写到：

```text
results/<RUN_LABEL>/
```

脚本最后会运行 trace audit：

```bash
python3 scripts/verify_trace_rules.py \
  --trace 'results/<RUN_LABEL>/result_access/*trace*.jsonl' \
  --require-cross-version-rules \
  --require-rulebook-path \
  --require-expel-rules
```

## Full Matrix

提交 Focus20 和 TaskBank36 hardv3 的 V2.4/V2.5/V2.6 全矩阵：

```bash
RUN_STAMP="$(date +%Y%m%d_%H%M%S)_webcoevo_full_v1" \
EXPEL_RULE_FILE="$PWD/rulebooks/expel_official_v2.json" \
EXPEL_FIDELITY=official_eval \
SBATCH_TIME=04:00:00 \
bash slurm/submit_hardv3_matrix.sh
```

矩阵包含：

- Focus20 full hardv3: 68 tasks。
- TaskBank36 hardv3 full: 本仓库 bundled 的所有 TaskBank36 rows。
- Rulebooks: `v2_4.json`、`v2_5.json`、`v2_6.json`。
- Shards: `access`、`surface`、`content`、`runtime:process`、`structural:functional`。

runtime 目录默认是：

```text
/home/gecm/linkding-drift-runtimes/<run-label>-<shard>-<run-stamp>
```

如果 cluster quota 需要，可以用 `LINKDING_DRIFT_BASE_DIR` 覆盖。

## Rule-Ablation / Transfer Matrix

为了 EECS545 project 的 ablation 和 transfer 实验，仓库里新增了两个 profile-aware submitter：

- `slurm/submit_control_rules_matrix.sh`: clean Linkding `1.45.0` baseline，对比 `no_rules` 和 `expel_only`，分别跑 Focus20 与 TaskBank36。
- `slurm/submit_first_modified_rules_matrix.sh`: 历史 `websites/first_modified` drift profile，对比 `expel_only` 和 `ExpeL + v2_4`，分别跑 Focus20 与 TaskBank36。

Smoke 例子：

```bash
RUN_STAMP="$(date +%Y%m%d_%H%M%S)_control_rules_smoke_qwen3vl_v1" \
TASK_LIMIT=2 \
SBATCH_TIME=00:30:00 \
MAX_STEPS=12 \
bash slurm/submit_control_rules_matrix.sh
```

```bash
RUN_STAMP="$(date +%Y%m%d_%H%M%S)_first_modified_rules_smoke_qwen3vl_v1" \
TASK_LIMIT=2 \
SBATCH_TIME=00:30:00 \
MAX_STEPS=12 \
SHARD_NAMES_CSV=access \
SHARD_VARIANTS_CSV=access \
bash slurm/submit_first_modified_rules_matrix.sh
```

Full 例子：

```bash
RUN_STAMP="$(date +%Y%m%d_%H%M%S)_control_rules_full_qwen3vl_v1" \
TASK_LIMIT=0 \
SBATCH_TIME=02:00:00 \
bash slurm/submit_control_rules_matrix.sh
```

```bash
RUN_STAMP="$(date +%Y%m%d_%H%M%S)_first_modified_rules_full_qwen3vl_v1" \
TASK_LIMIT=0 \
SBATCH_TIME=04:00:00 \
bash slurm/submit_first_modified_rules_matrix.sh
```

通用 runner 现在支持 `LINKDING_DRIFT_PROFILE=hardv3|first_modified|control`、`REQUIRE_XVR_RULES`、`REQUIRE_EXPEL_RULES`、`TASK_HOST_PROFILE`、`RUNTIME_VARIANTS` 和 `TASK_LIMIT`。

## 输出

每个 run 会写：

- `study/`: AgentLab study artifacts。
- `*eval*.jsonl`: legacy eval rows。
- `*trace*.jsonl`: legacy trace rows，包含 rule audit fields。
- `tasks.offset.json`: 已改写到本地 drift ports 的 task file。

rule audit 字段刻意分开：

- `injected_rule_ids`: ExpeL/task-experience rules。
- `cross_version_reflection_rule_ids`: XVR reflection rules。
- `cross_version_reflection_rules_path`: rulebook path。

reset-time failure 会和 agent failure 分开记录，并且也会回填 preflight rule audit fields。

## Repo-Local Skills

`skills/` 目录有三个轻量 Codex skills：

- `webcoevo-run`: 运行 unit/preflight/smoke/full matrix。
- `webcoevo-monitor`: 监控 Slurm jobs、logs、trace audit 和 rerun 决策。
- `webcoevo-analyze`: 聚合 eval JSONL，输出 success-rate tables。

可以这样让 agent 使用：

```text
Use the skill at skills/webcoevo-run/SKILL.md to launch a smoke run.
```

## 迁移说明

WebCoEvo 避免 silent rule injection failure 的方式：

- AgentLab 启动前先做 preflight rule selection。
- 设置 `--fail-on-empty-xvr-rules` 后，XVR rules 为空会 fail-fast。
- ExpeL 和 XVR rule IDs 使用不同字段导出。
- reset-error eval/trace rows 也会回填 preflight rule IDs。
- Slurm run 结束后自动 audit trace。

有意不带入的历史功能：

- knowledge-graph mining 和 broad ExpeL discovery。
- TaskBank 生成/分析 scaffold。
- paper/report/figure pipelines。
- retrieved trajectory exemplar injection。
- previous failure 的 retry guidance text。
