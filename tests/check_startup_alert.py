#!/usr/bin/env python3
"""tests/check_startup_alert.py — v1.0
v1.0  2026-09-13 — OTV4TEST r22. THE BOOT ALERT CARRIES THE BOX'S PUBLIC IP.

The operator reaches a misbehaving box by its public IP, which changes on every
stop/start; without it on the alert he is in the AWS console fighting two-factor
at exactly the moment he needs to be on the box. So the IP rides the boot alert.

Drives the REAL `AlertManager.send_startup_alert` and the REAL `public_ip()`
urllib path against a LOCAL HTTP server that plays checkip.amazonaws.com.

  A0  the existing fields survive: mode, instrument, restart type (CONTROL)
  A1  a good reply lands in the alert as `IP <address>`
  A2  a reply that is not an IP (a captive portal page) is REFUSED and NAMED,
      and the alert still sends
  A3  an unreachable endpoint is NAMED, and the alert still sends
  A4  a hung endpoint is abandoned within the bound — it cannot hold the boot
  A5  `public_ip()` never raises, on any of the above

🔴 NOTHING HERE CAN REACH TELEGRAM. The manager is built with `__new__`, so its
constructor — which creates a real TelegramSender — never runs; `_send` is a
capture. A check that pages the operator is a false alarm (WORKING_AGREEMENT §17).
Born red at r21 on A1, A2, A3 and A5; A0 and A4 are controls.
"""
import http.server
import os
import socket
import sys
import threading
import time

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


class _Checkip(http.server.BaseHTTPRequestHandler):
    def do_GET(self):                                           # noqa: N802
        if self.path == "/slow":
            time.sleep(5)
        body = {"/ok": b"203.0.113.7\n",                        # TEST-NET-3, never a real host
                "/html": b"<html><body>Please log in to the Wi-Fi</body></html>",
                "/slow": b"203.0.113.9\n"}.get(self.path, b"")
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:                                       # noqa: BLE001
            pass

    def log_message(self, *a):                                  # silence
        pass


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def main():
    import notifications.alert_manager as am

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Checkip)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    # a manager with NO path to Telegram: constructor skipped, _send captured
    mgr = am.AlertManager.__new__(am.AlertManager)
    mgr._tg, mgr._enabled = None, False
    sent = []
    mgr._send = lambda msg: (sent.append(msg), True)[1]

    am.PUBLIC_IP_TIMEOUT_S = 1.0                  # the bound under test

    def boot(path):
        am.PUBLIC_IP_URL = base + path
        sent.clear()
        t0 = time.time()
        mgr.send_startup_alert(paper=True, instrument="QQQ", risk_usd=100.0,
                               restart_type="fresh boot")
        return (sent[-1] if sent else ""), time.time() - t0

    msg, _ = boot("/ok")
    check("A0 the existing fields survive — mode, instrument, restart type (control)",
          "[PAPER] STARTED" in msg and "QQQ" in msg and "fresh boot" in msg, msg)
    check("A1 a good reply lands in the alert as `IP <address>`",
          "IP 203.0.113.7" in msg, msg)

    msg, _ = boot("/html")
    check("A2 a reply that is NOT an IP is refused and NAMED, and the alert still sends",
          bool(msg) and "IP unavailable (reply was not an IP address)" in msg
          and "Wi-Fi" not in msg, msg)

    closed = f"http://127.0.0.1:{_free_port()}/ok"
    am.PUBLIC_IP_URL = closed
    sent.clear()
    mgr.send_startup_alert(paper=True, instrument="QQQ", risk_usd=100.0, restart_type="fresh boot")
    msg = sent[-1] if sent else ""
    check("A3 an unreachable endpoint is NAMED, and the alert still sends",
          bool(msg) and "IP unavailable (" in msg, msg)

    msg, took = boot("/slow")
    check("A4 a hung endpoint is abandoned within the bound — it cannot hold the boot (control)",
          bool(msg) and took < 3.0, f"took {took:.2f}s against a 5 s hang, bound 1 s")

    fn = getattr(am, "public_ip", None)
    raised = None
    if fn is None:
        raised = "public_ip() does not exist"
    else:
        for u in (base + "/ok", base + "/html", closed, "not a url at all"):
            try:
                fn(timeout=1.0, url=u)
            except Exception as e:                              # noqa: BLE001
                raised = f"{u}: {type(e).__name__}"
                break
    check("A5 public_ip() never raises, on any of those inputs", raised is None, raised or "")

    srv.shutdown()
    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
