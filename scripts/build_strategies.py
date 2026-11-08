#!/usr/bin/env python3
"""Options strategies, described accurately and without a recommendation.

WHAT THIS IS
A reference. For each common structure it states what you actually do, the most you can
make, the most you can lose, and the view it expresses. No entry levels, no "buy this", no
ranking of which is best - because which structure suits a person depends on their capital,
their risk tolerance and what they think will happen, and none of that is knowable from here.

WHY IT IS WRITTEN THIS WAY
An options strategy is a shape, not a tip. "Sell a covered call" is not advice; it is a
description of a payoff. The moment a page ranks strategies or suggests one for today, it
stops being reference and starts being a recommendation, which is a different thing with
different rules and a different burden of accuracy.

THE HONEST FRAME, STATED ON THE PAGE
SEBI's own studies have found most individual F&O traders lose money over time. A reference
that lists strategies without saying so would be quietly misleading - the structures below
are all symmetrical arithmetic, and none of them changes those odds.

Each row carries:
  legs        what you buy and sell
  max_profit  bounded or unlimited, and why
  max_loss    the same
  view        the market opinion it expresses
  note        the thing that usually surprises people
"""
import json, os, sys
from datetime import datetime, timezone

OUT = "docs/strategies.json"

S = [
    {
        "name": "Long call",
        "legs": "Buy 1 call",
        "max_profit": "Unlimited (the stock can keep rising)",
        "max_loss": "The premium paid",
        "view": "The price will rise, and rise enough to cover the premium before expiry.",
        "note": "Needs a move, not just the right direction. A stock that drifts up slowly can "
                "still lose money because time decay eats the premium.",
    },
    {
        "name": "Long put",
        "legs": "Buy 1 put",
        "max_profit": "Large but bounded (the stock cannot fall below zero)",
        "max_loss": "The premium paid",
        "view": "The price will fall, and fall enough to cover the premium before expiry.",
        "note": "Falling volatility hurts even when the direction is right - the put loses "
                "value if the market calms down.",
    },
    {
        "name": "Covered call",
        "legs": "Own the stock, sell 1 call",
        "max_profit": "Premium plus the gain up to the strike",
        "max_loss": "The stock can fall to zero, less the premium received",
        "view": "Mildly bullish or flat - happy to sell the upside for income.",
        "note": "Caps the upside. If the stock doubles, you keep only up to the strike. The "
                "premium is small compared with the downside you still carry.",
    },
    {
        "name": "Protective put",
        "legs": "Own the stock, buy 1 put",
        "max_profit": "Unlimited (the stock can keep rising)",
        "max_loss": "The fall to the strike, plus the premium",
        "view": "Bullish but wanting a floor under the position.",
        "note": "Insurance costs money every time. Held for long, the premiums can add up to "
                "more than the protection ever pays.",
    },
    {
        "name": "Bull call spread",
        "legs": "Buy a lower-strike call, sell a higher-strike call",
        "max_profit": "The gap between strikes, less the net premium",
        "max_loss": "The net premium paid",
        "view": "Moderately bullish - up, but not beyond the upper strike.",
        "note": "Selling the second leg cuts the cost and caps the gain. Cheaper than a long "
                "call and also worth less if the move is large.",
    },
    {
        "name": "Bear put spread",
        "legs": "Buy a higher-strike put, sell a lower-strike put",
        "max_profit": "The gap between strikes, less the net premium",
        "max_loss": "The net premium paid",
        "view": "Moderately bearish - down, but not below the lower strike.",
        "note": "The mirror of the bull call spread. A crash pays no more than a modest fall.",
    },
    {
        "name": "Long straddle",
        "legs": "Buy 1 call and 1 put at the same strike",
        "max_profit": "Unlimited in theory, in either direction",
        "max_loss": "Both premiums",
        "view": "A big move is coming, but not which way.",
        "note": "You pay for two options and need a large move just to break even. If the "
                "market stays quiet, both legs decay at once.",
    },
    {
        "name": "Long strangle",
        "legs": "Buy an out-of-the-money call and an out-of-the-money put",
        "max_profit": "Unlimited in theory, in either direction",
        "max_loss": "Both premiums",
        "view": "A big move is coming, and cheaply expressed.",
        "note": "Cheaper than a straddle and needs an even larger move to pay. This is the "
                "structure behind most very cheap options.",
    },
    {
        "name": "Iron condor",
        "legs": "Sell a call spread and sell a put spread, both out of the money",
        "max_profit": "The net premium received",
        "max_loss": "The wider spread, less the premium",
        "view": "The price will stay inside a range.",
        "note": "Wins often and small, loses rarely and large. The shape that makes people "
                "believe they have found an edge, right up until one bad week.",
    },
    {
        "name": "Short straddle",
        "legs": "Sell 1 call and 1 put at the same strike",
        "max_profit": "Both premiums",
        "max_loss": "Unlimited on the call side",
        "view": "The price will stay near the strike.",
        "note": "The exact opposite of a long straddle, and the risk profile is not "
                "symmetrical - the loss has no ceiling. Most exchanges require large margin "
                "for this reason.",
    },
]


def main():
    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(S),
        "columns": ["strategy", "legs", "max profit", "max loss", "view", "what surprises people"],
        "rows": [[s["name"], s["legs"], s["max_profit"], s["max_loss"], s["view"], s["note"]]
                 for s in S],
        "note": ("Each row is a payoff shape, not a recommendation. Which structure suits "
                 "anyone depends on capital, risk tolerance and what they expect - none of "
                 "which this page can know."),
        "cautions": {
            "sebi": ("SEBI's own studies have found most individual F&O traders lose money "
                     "over time. Every structure above is arithmetic; none of it changes "
                     "those odds."),
            "premium_is_not_cost": ("Premium x lot size is what leaves your account, plus "
                                    "brokerage, STT, exchange charges and GST."),
            "time_decay": ("Every bought option loses value as expiry approaches, whether or "
                           "not the price moves. That is why being right on direction is not "
                           "enough."),
            "not_advice": ("This is educational reference only. It is not investment advice, "
                           "not a recommendation, and not a signal."),
        },
    }
    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %d strategies" % (OUT, len(S)))
    for s in S:
        print("   %-18s %s" % (s["name"], s["view"][:60]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
