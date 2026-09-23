#!/usr/bin/env python3
"""bankscan.py - BANK HEALTH SCANNER (Dev ke notebook rules):
- data/banks.json me ratios quarterly seed hote hain (manual, official press releases se)
- Ye script sirf price/day-change merge karta hai data/circuits.json (bhavcopy) se
- Ratios preserve hote hain - jab tak seed edit na ho"""
import json, os

def main():
    if not os.path.exists("data/banks.json"):
        print("no banks.json - skip")
        return
    with open("data/banks.json") as f:
        banks = json.load(f)
    changed = False
    if os.path.exists("data/circuits.json"):
        with open("data/circuits.json") as f:
            circ = json.load(f)
        allst = circ.get("all") or {}
        for b in banks.get("banks", []):
            a = allst.get(b["s"])
            if a and len(a) > 10 and a[10] is not None:
                b["p"] = a[10]
                # last day % (aaj ka)
                last = None
                for i in range(6, -1, -1):
                    if a[i] is not None:
                        last = a[i]
                        break
                if last is not None:
                    b["chg"] = last
                changed = True
    if changed:
        with open("data/banks.json", "w") as f:
            json.dump(banks, f, ensure_ascii=False, separators=(",", ":"))
        print("OK banks.json prices merged:", [(b["s"], b.get("p")) for b in banks["banks"]])
    else:
        print("no price data - banks.json unchanged")

if __name__ == "__main__":
    main()
