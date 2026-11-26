"""GPU / memory information for the Smith server (Linux with NVIDIA, and macOS).

- Linux (and others with an NVIDIA card): `nvidia-smi` gives the card, total/used/free VRAM and
  the VRAM held by one process.
- macOS: the GPU shares the system memory (unified memory), so there is no separate VRAM. The
  report shows the chip, the total/used/free system memory and the memory the process uses
  (its resident set; the Metal buffers of the model are part of it).

Every external command goes through the `run` argument, so the parsing can be tested without
the real tools.
"""
import json
import re
import subprocess
import sys

NO_INFO = "GPU: no GPU information available (nvidia-smi not found or failed)"


def is_macos(platform: str = sys.platform) -> bool:
    return platform == "darwin"


def memory_label(platform: str = sys.platform) -> str:
    """How to call the memory the model lives in."""
    return "unified memory" if is_macos(platform) else "VRAM"


def _output(cmd: list[str], run) -> str | None:
    try:
        return run(cmd, capture_output=True, text=True, timeout=15, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None


def _nvidia_smi(query: str, fields: str, run) -> list[list[str]] | None:
    """Rows of `nvidia-smi --query-<query>=<fields>` as lists of strings (None: no NVIDIA GPU info)."""
    out = _output(["nvidia-smi", f"--query-{query}={fields}", "--format=csv,noheader,nounits"], run)
    if out is None:
        return None
    return [[cell.strip() for cell in line.split(",")] for line in out.splitlines() if line.strip()]


# ---- macOS -----------------------------------------------------------------------------------

def _mac_chip(run) -> str:
    """'Apple M2 Pro (19 GPU cores)' from system_profiler, falling back to the CPU brand string."""
    out = _output(["system_profiler", "SPDisplaysDataType", "-json"], run)
    try:
        gpu = json.loads(out)["SPDisplaysDataType"][0]
        name = gpu.get("sppci_model") or gpu.get("_name") or "Apple GPU"
        cores = gpu.get("sppci_cores")
        return f"{name} ({cores} GPU cores)" if cores else name
    except (TypeError, ValueError, KeyError, IndexError):
        brand = _output(["sysctl", "-n", "machdep.cpu.brand_string"], run)
        return brand.strip() if brand and brand.strip() else "Apple GPU"


def _parse_vm_stat(text: str) -> int | None:
    """Bytes of memory that can be given to a new process (free + inactive + speculative pages)."""
    size = re.search(r"page size of (\d+) bytes", text)
    if not size:
        return None
    pages = 0
    for name in ("free", "inactive", "speculative"):
        match = re.search(rf"^Pages {name}:\s+(\d+)", text, re.MULTILINE)
        pages += int(match.group(1)) if match else 0
    return pages * int(size.group(1))


def _mac_memory_mib(run) -> tuple[int, int, int] | None:
    """(total, used, free) system memory in MiB, or None."""
    total = _output(["sysctl", "-n", "hw.memsize"], run)
    stat = _output(["vm_stat"], run)
    free_bytes = _parse_vm_stat(stat) if stat else None
    if not total or not total.strip().isdigit() or free_bytes is None:
        return None
    total_mib, free_mib = int(total) // 2**20, free_bytes // 2**20
    return total_mib, total_mib - free_mib, free_mib


def _mac_process_mib(pid: int, run) -> int | None:
    out = _output(["ps", "-o", "rss=", "-p", str(pid)], run)
    return int(out.strip()) // 1024 if out and out.strip().isdigit() else None


# ---- public API ------------------------------------------------------------------------------

def process_memory_mib(pid: int, run=subprocess.run, platform: str = sys.platform) -> int | None:
    """Memory (MiB) the process `pid` holds on the GPU (macOS: resident memory); None when none."""
    if is_macos(platform):
        return _mac_process_mib(pid, run)
    apps = _nvidia_smi("compute-apps", "pid,used_memory", run) or []
    held = next((mem for app_pid, mem in apps if app_pid == str(pid)), None)
    return int(held) if held and held.isdigit() else None


def gpu_report(pid: int | None = None, run=subprocess.run, platform: str = sys.platform) -> list[str]:
    """Human readable lines: the GPU, total/used/free memory and how much the process `pid` holds."""
    label = memory_label(platform)
    if is_macos(platform):
        memory = _mac_memory_mib(run)
        if memory is None:
            return ["GPU: no memory information available (sysctl / vm_stat failed)"]
        total, used, free = memory
        lines = [f"GPU 0: {_mac_chip(run)} | {label} (shared with the system) total {total} MiB, "
                 f"used {used} MiB, free {free} MiB"]
    else:
        gpus = _nvidia_smi("gpu", "name,memory.total,memory.used,memory.free", run)
        if not gpus:
            return [NO_INFO]
        lines = [f"GPU {i}: {name} | {label} total {total} MiB, used {used} MiB, free {free} MiB"
                 for i, (name, total, used, free) in enumerate(gpus)]
    if pid is not None:
        held = process_memory_mib(pid, run, platform)
        if held:
            lines.append(f"Smith (pid {pid}) holds {held} MiB of {label}")
        elif is_macos(platform):
            lines.append(f"Smith (pid {pid}) memory usage is not available")
        else:
            lines.append(f"Smith (pid {pid}) holds no VRAM (the model runs on the CPU)")
    return lines
