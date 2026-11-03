import json, os
from ansible.plugins.callback import CallbackBase

KEEP = ("msg", "stdout", "greeting", "included_on", "rescued", "ping", "changed", "failed", "skipped")


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "aggregate"
    CALLBACK_NAME = "record"
    CALLBACK_NEEDS_ENABLED = True

    def _rec(self, status, result):
        r = result._result
        row = {"play": self._play, "task": result._task.get_name(), "host": result._host.get_name(), "status": status}
        for k in KEEP:
            if k in r:
                row[k] = r[k] if k != "ansible_facts" else sorted(r[k])
        if "ansible_facts" in r:
            row["facts"] = {k: v for k, v in sorted(r["ansible_facts"].items()) if not k.startswith("discovered")}
        with open(os.environ["RECORD_FILE"], "a") as f:
            f.write(json.dumps(row, sort_keys=True, default=str) + "\n")

    def v2_playbook_on_play_start(self, play):
        self._play = play.get_name()

    def v2_runner_on_ok(self, result): self._rec("ok", result)
    def v2_runner_on_failed(self, result, ignore_errors=False): self._rec("failed", result)
    def v2_runner_on_skipped(self, result): self._rec("skipped", result)
    def v2_runner_on_unreachable(self, result): self._rec("unreachable", result)
    def v2_runner_item_on_ok(self, result): self._rec("item_ok", result)
    def v2_playbook_on_stats(self, stats):
        with open(os.environ["RECORD_FILE"], "a") as f:
            f.write(json.dumps({"stats": {h: stats.summarize(h) for h in sorted(stats.processed)}}, sort_keys=True) + "\n")
