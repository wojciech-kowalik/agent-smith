"""Simple benchmark of the local model: 8 short tasks run through `make ask` (uses the server when
running), with wall-clock time and an automatic correctness check. Run: make benchmark"""
import re
import subprocess
import sys
import time
from pathlib import Path
SMITH = str(Path(__file__).resolve().parent.parent)  # repo root (holds the Makefile)
TASKS = [
 ("arytmetyka", "What is 17 * 23? Answer with just the number.", lambda a: "391" in a),
 ("wiedza", "What is the capital of Australia? One word.", lambda a: "canberra" in a.lower()),
 ("logika", "If all bloops are razzies and all razzies are lazzies, are all bloops lazzies? Answer yes or no.", lambda a: "yes" in a.lower()),
 ("kod-fizzbuzz", "Write a Python function fizzbuzz(n) returning a list of strings for 1..n. Only code.", None),
 ("kod-bug", "Find the bug: def avg(xs): return sum(xs)/len(xs)+1. One sentence.", lambda a: bool(re.search(r"\+ ?1|adds? 1|plus 1|add(s|ing)? one", a, re.I))),
 ("regex", "Give a Python regex matching a 5-digit ZIP code like 12345 as a full string. Only the regex.", lambda a: "5" in a and "\\d" in a or "[0-9]" in a),
 ("pl-tlumaczenie", "Translate to Polish: 'The server is running.' Only the translation.", lambda a: "serwer" in a.lower()),
 ("dlugi-tekst", "Explain in about 150 words how a hash map works.", lambda a: len(a.split()) > 40 and "hash" in a.lower()),
]
def run_py(code_text):
    m = re.search(r"```(?:python)?\n(.*?)```", code_text, re.S)
    code = m.group(1) if m else code_text
    code += "\nassert fizzbuzz(15)[-1]=='FizzBuzz' and fizzbuzz(3)[2]=='Fizz' and fizzbuzz(5)[4]=='Buzz' and fizzbuzz(1)==['1']\n"
    return subprocess.run([sys.executable,"-I","-c",code],capture_output=True,timeout=10).returncode==0
ok=0; tot=0
print(f"{'zadanie':16}{'czas[s]':>8}{'słowa':>7}  wynik")
for name,q,chk in TASKS:
    t=time.time()
    r=subprocess.run(["make","--no-print-directory","-C",SMITH,"ask",f"Q={q}"],capture_output=True,text=True,timeout=300)
    dt=time.time()-t; a=r.stdout.strip()
    try: good = run_py(a) if name=="kod-fizzbuzz" else chk(a)
    except Exception: good=False
    ok+=good; tot+=1
    print(f"{name:16}{dt:8.2f}{len(a.split()):7}  {'OK' if good else 'FAIL'}  | {a[:60]!r}")
print(f"\nPoprawne: {ok}/{tot}")
