#!/usr/bin/env python3
"""
tests/check_contract_scale.py  v1.2
v1.2  2026-10-04  OTV4TEST r236 — AN INTERPRETER THAT CANNOT IMPORT THE REPO IS "NOT RUN", NEVER "FAIL". Under the system
      python3 (no numpy) every case printed FAIL carrying a ModuleNotFoundError - an exit code dressed as a verdict
      (SPX-TEST's agent, 2026-10-04; WA 40.1 / 38.9 criterion 3). Now the first case's import failure prints
      "NOT RUN - <error>" with exit 2 and no case lines. Still non-zero: a NOT RUN is never a pass.
v1.1  2026-10-04  OTV4TEST r235 — S7: the Service mode line also says ORCS=on/OFF, read from config.ORCS_ENABLED.
v1.0  2026-10-04  OTV4TEST r234 (SCALE.1) — ORCS'S WING AND CREDIT FLOOR SCALE WITH THE BOX'S CONTRACT PRICE.

  The operator, 2026-10-04: "SPX cap, ramp & wing search CANNOT be the same as QQQ. The math doesn't work. It
  needs to scale with the contract price differences." Measured: SPX contracts cost ~7.5x QQQ's (platform
  expected move median 7.57, /var/tmp/spx_scale_1004). His answer to the proposal: "Perfect."

  S1  QQQ: CONTRACT_SCALE 1.0 ("default"); ORCS wing 3.0, credit floor 0.10 - UNCHANGED from r207
  S2  SPX: CONTRACT_SCALE 7.5 ("SPX default"); ORCS wing 22.5, credit floor 0.75
  S3  OT_CONTRACT_SCALE overrides (SPX at 6.0 -> wing 18.0); a non-positive / non-numeric value is IGNORED and SAID
  S4  the REAL locate() on a 5-dollar SPX chain: both sides 20 wide (22.5 ties 20/25; the tie goes NARROWER on
      BOTH sides - before r234 the put took 25 and the call 20)
  S5  the REAL locate() on a 1-dollar QQQ chain: both sides 3 wide, exactly as r207
  S6  the Service mode line ends with contract_scale and its source; config is read from main's import
Fresh interpreter per case (config is read at import). Run: python3 tests/check_contract_scale.py
"""
import json, os, subprocess, sys, tempfile
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


_P = r'''
import json, sys
from types import SimpleNamespace as N
sys.path.insert(0, sys.argv[1])
import config as C
import strategy.orcs_plan as P
out = {"scale": C.CONTRACT_SCALE, "src": C.CONTRACT_SCALE_SOURCE,
       "wing": P.ORCS_WING_USD, "floor": P.ORCS_MIN_CREDIT}
spot, step, im = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
def leg(k, side):
    d = abs(k - spot)
    delta = max(0.01, 0.5 - d * (0.30 / (1.5 * im)))     # 0.20 at 1.5 implied moves out
    prem = max(0.05, 0.4 * im * (delta / 0.2) ** 2)
    return N(strike=k, delta=(-delta if side == "put" else delta), bid=round(prem * 0.95, 2), ask=round(prem * 1.05, 2))
n = int(4 * im / step) + 2
puts = [leg(spot - step * i, "put") for i in range(1, n)]
calls = [leg(spot + step * i, "call") for i in range(1, n)]
chain = N(puts=puts, calls=calls)
for side in ("put", "call"):
    loc = P.locate(side, chain, spot, im)
    out[side] = [float(loc.short.strike) if loc.short else None, loc.width, loc.why]
print("@@" + json.dumps(out))
'''


def run(inst, spot, step, im, scale=None):
    env = {k: v for k, v in os.environ.items() if k not in ("OT_CONTRACT_SCALE",)}
    env["OT_INSTRUMENT"] = inst
    env["OT_LOG_FILE"] = os.path.join(tempfile.mkdtemp(prefix="check_contract_scale_"), "bot.log")
    if scale is not None:
        env["OT_CONTRACT_SCALE"] = scale
    p = subprocess.run([sys.executable, "-c", _P, _root, str(spot), str(step), str(im)],
                       capture_output=True, text=True, env=env, timeout=120)
    tag = [l for l in p.stdout.splitlines() if l.startswith("@@")]
    if tag:
        return json.loads(tag[-1][2:])
    err = (p.stderr or p.stdout).strip().splitlines()
    last = err[-1] if err else "no output"
    if "ModuleNotFoundError" in last or "ImportError" in last:
        return {"notrun": last}
    return {"err": (p.stderr or p.stdout)[-300:]}


class NotRun(Exception):
    pass


def main():
    try:
        q = run("QQQ", 750.0, 1.0, 3.0)
        if "notrun" in q:
            raise NotRun(q["notrun"])
        check("S1 QQQ: scale 1.0 (default), wing 3.0, floor 0.10 - r207 unchanged",
              q.get("scale") == 1.0 and q.get("src") == "default" and q.get("wing") == 3.0
              and abs(q.get("floor", 0) - 0.10) < 1e-9, q)
        s = run("SPX", 7700.0, 5.0, 22.5)
        check("S2 SPX: scale 7.5 (SPX default), wing 22.5, floor 0.75",
              s.get("scale") == 7.5 and s.get("src") == "SPX default" and s.get("wing") == 22.5
              and abs(s.get("floor", 0) - 0.75) < 1e-9, s)
        o = run("SPX", 7700.0, 5.0, 22.5, scale="6")
        bad = [run("SPX", 7700.0, 5.0, 22.5, scale=v) for v in ("abc", "0", "-2")]
        check("S3 OT_CONTRACT_SCALE overrides; a bad value is ignored (SPX default kept) and SAID",
              o.get("scale") == 6.0 and o.get("wing") == 18.0 and o.get("src") == "OT_CONTRACT_SCALE"
              and all(b.get("scale") == 7.5 and "IGNORED" in b.get("src", "") for b in bad), (o, bad))
        check("S4 real locate() on a 5-dollar SPX chain: BOTH sides 20 wide (a 20/25 tie goes narrower)",
              s.get("put", [None, None])[1] == 20.0 and s.get("call", [None, None])[1] == 20.0, s)
        check("S5 real locate() on a 1-dollar QQQ chain: both sides 3 wide, as r207",
              q.get("put", [None, None])[1] == 3.0 and q.get("call", [None, None])[1] == 3.0, q)
        src = open(os.path.join(_root, "main.py")).read()
        check("S6 the Service mode line ends with contract_scale and its source (main imports both from config)",
              'contract_scale={CONTRACT_SCALE:g} ({CONTRACT_SCALE_SOURCE})' in src
              and "CONTRACT_SCALE, CONTRACT_SCALE_SOURCE," in src)
        check("S7 the Service mode line says ORCS=on/OFF from config.ORCS_ENABLED (main imports it)",
              "f\" · ORCS={'on' if ORCS_ENABLED else 'OFF'}\"" in src and "    ORCS_ENABLED," in src)
    except NotRun as nr:
        print(f"  NOT RUN — this interpreter ({sys.executable}) cannot import the repo: {nr}")
        print("\nNOT RUN — not a verdict; run it under the venv (the sweep and the lander do)"); return 2
    except Exception as exc:  # noqa: BLE001
        check("S0 (did not run)", False, f"{type(exc).__name__}: {exc}")
    if FAILED:
        print(f"\nRED — {sorted(set(FAILED))}"); return 1
    print("\nGREEN — ORCS's wing and credit floor ride the box's contract scale; QQQ unchanged"); return 0


if __name__ == "__main__":
    sys.exit(main())
