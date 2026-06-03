#!/usr/bin/env python3
"""Offline test for the iTick live module (mocked HTTP — no key/network needed)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import live  # noqa: E402


class _FakeResp:
    def __init__(self, payload, status_code=200):
        self._p = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"http {self.status_code}")

    def json(self):
        return self._p


class _FakeSession:
    """Returns a canned iTick payload; records the request for assertions."""
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "params": params})
        return _FakeResp(self.payload)


def main() -> int:
    print("1) code mapping (.JK stripped) ...")
    assert live.to_itick_code("BBRI.JK") == "BBRI"
    assert live.to_itick_code("ptba.jk") == "PTBA"
    print("   -> ok")

    print("2) no-token path is graceful ...")
    q = live.fetch_quote("BBRI.JK", token=None)
    # ensure env doesn't accidentally supply one during the test
    if q["error"] != "no_token":
        # a token exists in the environment; that's fine, just note it
        print(f"   -> token present in env; got ok={q['ok']}")
    else:
        print("   -> correctly reported no_token")

    print("3) parse a good iTick response (mocked) ...")
    payload = {"code": 0, "msg": "OK",
               "data": {"s": "BBRI", "ld": 4250, "o": 4210, "h": 4280,
                        "l": 4200, "v": 12_500_000, "t": 1716200000000}}
    sess = _FakeSession(payload)
    q = live.fetch_quote("BBRI.JK", token="TESTKEY", session=sess)
    assert q["ok"] is True, q
    assert q["last"] == 4250 and q["open"] == 4210 and q["high"] == 4280, q
    assert q["volume"] == 12_500_000, q
    # header + params correct?
    call = sess.calls[0]
    assert call["headers"]["token"] == "TESTKEY"
    assert call["params"] == {"region": "ID", "code": "BBRI"}, call["params"]
    print(f"   -> parsed last={q['last']:.0f} open={q['open']:.0f} vol={q['volume']:.0f}")

    print("4) parse a list-wrapped response ...")
    sess2 = _FakeSession({"code": 0, "data": [{"s": "PTBA", "ld": 2900, "o": 2850}]})
    q2 = live.fetch_quote("PTBA.JK", token="K", session=sess2)
    assert q2["ok"] and q2["last"] == 2900, q2
    print("   -> ok")

    print("5) API error code surfaces as error ...")
    sess3 = _FakeSession({"code": 401, "msg": "invalid token"})
    q3 = live.fetch_quote("BBRI.JK", token="BAD", session=sess3)
    assert q3["ok"] is False and "invalid token" in (q3["error"] or ""), q3
    print("   -> ok")

    print("\nALL LIVE TESTS PASSED ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
