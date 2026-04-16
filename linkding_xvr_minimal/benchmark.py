from functools import partial

from linkding_xvr_minimal.browser_task import WebEvolveBrowserTask


_REGISTERED_ENV_IDS = set()


def env_id(spec):
    if spec.task_name.startswith("browsergym/"):
        return spec.task_name.split("/", 1)[1]
    return spec.task_name


def register_task_for_spec(spec):
    try:
        import gymnasium as gym
        from browsergym.core.registration import register_task
    except Exception as exc:
        raise RuntimeError("BrowserGym registration dependencies are unavailable: {}".format(exc))

    task_env_id = env_id(spec)
    if task_env_id in _REGISTERED_ENV_IDS or "browsergym/{}".format(task_env_id) in gym.registry:
        _REGISTERED_ENV_IDS.add(task_env_id)
        return task_env_id
    register_task(id=task_env_id, task_class=partial(WebEvolveBrowserTask, spec=spec))
    _REGISTERED_ENV_IDS.add(task_env_id)
    return task_env_id


def build_env_args_list(specs, max_steps=30, headless=True):
    try:
        from agentlab.experiments.loop import EnvArgs
    except Exception as exc:
        raise RuntimeError("AgentLab EnvArgs dependency is unavailable: {}".format(exc))

    env_args_list = []
    for spec in specs:
        register_task_for_spec(spec)
        env_args_list.append(
            EnvArgs(
                task_name=env_id(spec),
                task_seed=0,
                max_steps=max_steps,
                headless=headless,
                storage_state=spec.storage_state,
            )
        )
    return env_args_list


def build_task_metadata(specs):
    rows = []
    for spec in specs:
        metadata = (spec.metadata or {}).get("normalized_task") or {}
        rows.append(
            {
                "task_name": env_id(spec),
                "task_name_full": spec.task_name,
                "task_id": spec.task_id,
                "site": spec.site,
                "version": spec.version,
                "family": metadata.get("family", spec.family),
                "source_task_id": metadata.get("source_task_id", 0),
                "focus20_source_task_id": metadata.get("focus20_source_task_id", 0),
                "source_family": metadata.get("source_family", ""),
                "variant": metadata.get("variant", ""),
                "drift_type": metadata.get("drift_type", ""),
                "start_url": spec.start_url,
            }
        )
    return rows


def build_benchmark(specs, benchmark_name="linkding_xvr_minimal", max_steps=30, headless=True):
    try:
        import pandas as pd
        from browsergym.experiments.benchmark.base import Benchmark, HighLevelActionSetArgs
    except Exception as exc:
        raise RuntimeError("BrowserGym benchmark dependencies are unavailable: {}".format(exc))

    return Benchmark(
        name=benchmark_name,
        high_level_action_set_args=HighLevelActionSetArgs(
            subsets=("chat", "infeas", "bid", "nav"),
            multiaction=False,
        ),
        is_multi_tab=False,
        supports_parallel_seeds=True,
        env_args_list=build_env_args_list(specs, max_steps=max_steps, headless=headless),
        backends=[],
        task_metadata=pd.DataFrame(build_task_metadata(specs)),
    )
