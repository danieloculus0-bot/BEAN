# Dedicated cloud Core deployment | November 24, 2026

BEAN's owner has established a dedicated Linux VPS as its primary cognitive host. The existing Python Core (source revision `54b0a4d2c17face7ffbf3d016ef348c5a055164a`) was installed and started by an authenticated private deployment runner. This is the actual Python runtime, not the lightweight hosted JavaScript notes adapter.

| Observation | Result |
| --- | --- |
| Host | Ubuntu 24.04.5 LTS, six virtual CPU cores, 12 GB nominal RAM |
| Storage at installation | 96 GiB filesystem, approximately 94 GiB free |
| Boot readiness | 10/10 checks passed (temporary database; mock reasoning probe) |
| Production service | Active and enabled for startup; persistent SQLite database present |
| Follow-up service status | Active, enabled, zero reported restarts; approximately 29 MB service memory at sample |
| Extended verification | Incomplete: Git ownership check stopped the follow-up before database growth and integrated cognition tests |

Deployment logs were inspected by the project maintainer through a private repository. They are not public evidence artifacts or independent uptime monitoring. Host identifiers, credentials, and private infrastructure details are intentionally omitted. The next steps are to repeat runtime verification as the repository owner, check live database progress and isolated multi-skill execution, and connect authenticated model providers and client interfaces. The Jetson remains a distinct physical runtime. Existing hosted adapters are not yet unified with the VPS; no live cloud model inference, autonomous research or learning gain is claimed from this milestone.

See [boot readiness implementation](../bean/runtime/boot_readiness.py), [persistent goal plans](PERSISTENT_GOAL_PLANS.md), and [status](status.html).
