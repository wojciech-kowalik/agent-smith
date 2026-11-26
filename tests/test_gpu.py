import subprocess

import gpu

MAC_PROFILER = '{"SPDisplaysDataType": [{"_name": "kHW_AppleM2ProItem", "sppci_model": "Apple M2 Pro", "sppci_cores": "19"}]}'
MAC_VM_STAT = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                               100000.
Pages active:                             500000.
Pages inactive:                           200000.
Pages speculative:                         50000.
"""


def fake_run(outputs):
    """A `subprocess.run` stand-in: answers by the command (first word or nvidia-smi query)."""
    class Result:
        def __init__(self, stdout):
            self.stdout = stdout

    def run(cmd, **kwargs):
        key = cmd[1].split("=")[0] if cmd[0] == "nvidia-smi" else cmd[0]
        if outputs is None or key not in outputs:
            raise FileNotFoundError(cmd[0])
        return Result(outputs[key])
    return run


MAC = {
    "system_profiler": MAC_PROFILER,
    "sysctl": str(32 * 2**30),  # 32 GiB
    "vm_stat": MAC_VM_STAT,
    "ps": "  9830400\n",  # KB
}


# ---- NVIDIA (Linux) --------------------------------------------------------------------------

def test_nvidia_report_shows_card_vram_and_the_process_share():
    run = fake_run({
        "--query-gpu": "NVIDIA GeForce RTX 3060, 12288, 9800, 2488\n",
        "--query-compute-apps": "111, 120\n4242, 9700\n",
    })
    assert gpu.gpu_report(4242, run, "linux") == [
        "GPU 0: NVIDIA GeForce RTX 3060 | VRAM total 12288 MiB, used 9800 MiB, free 2488 MiB",
        "Smith (pid 4242) holds 9700 MiB of VRAM",
    ]


def test_nvidia_report_notes_when_the_model_is_on_the_cpu():
    run = fake_run({"--query-gpu": "GPU A, 8192, 100, 8092\nGPU B, 8192, 0, 8192\n", "--query-compute-apps": ""})
    lines = gpu.gpu_report(7, run, "linux")
    assert lines[0].startswith("GPU 0: GPU A") and lines[1].startswith("GPU 1: GPU B")
    assert "holds no VRAM" in lines[-1]


def test_report_without_nvidia_smi():
    assert gpu.gpu_report(1, fake_run(None), "linux") == [gpu.NO_INFO]


def test_nvidia_process_memory():
    run = fake_run({"--query-compute-apps": "111, 120\n4242, 9700\n"})
    assert gpu.process_memory_mib(4242, run, "linux") == 9700
    assert gpu.process_memory_mib(1, run, "linux") is None


# ---- macOS -----------------------------------------------------------------------------------

def test_mac_report_shows_chip_unified_memory_and_the_process_share():
    lines = gpu.gpu_report(4242, fake_run(MAC), "darwin")
    # 350000 reclaimable pages * 16 KiB = 5468 MiB free of 32768 MiB
    assert lines == [
        "GPU 0: Apple M2 Pro (19 GPU cores) | unified memory (shared with the system) total 32768 MiB, "
        "used 27300 MiB, free 5468 MiB",
        "Smith (pid 4242) holds 9600 MiB of unified memory",
    ]


def test_mac_chip_falls_back_to_the_cpu_brand():
    outputs = {**MAC, "sysctl": "Apple M1\n"}
    del outputs["system_profiler"]
    assert gpu._mac_chip(fake_run(outputs)) == "Apple M1"
    assert gpu._mac_chip(fake_run({"system_profiler": "not json"})) == "Apple GPU"


def test_mac_report_when_memory_info_fails():
    assert "no memory information" in gpu.gpu_report(1, fake_run(None), "darwin")[0]


def test_mac_process_memory_unknown():
    outputs = {**MAC, "ps": ""}
    lines = gpu.gpu_report(5, fake_run(outputs), "darwin")
    assert lines[-1] == "Smith (pid 5) memory usage is not available"


def test_vm_stat_parsing_needs_the_page_size():
    assert gpu._parse_vm_stat(MAC_VM_STAT) == 350000 * 16384
    assert gpu._parse_vm_stat("garbage") is None


def test_memory_label_per_platform():
    assert gpu.memory_label("darwin") == "unified memory"
    assert gpu.memory_label("linux") == "VRAM"


def test_failing_command_counts_as_no_output():
    def run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)
    assert gpu._output(["x"], run) is None
