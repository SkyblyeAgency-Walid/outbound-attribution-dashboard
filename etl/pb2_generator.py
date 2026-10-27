"""
PB2 - Outbound Attribution Dashboard :: Synthetic Data Generator
Generates 7 CSVs (3 facts + 4 dims) with 4 pre-baked insights:
  1. Referral list : ~3% of sends -> ~31% of closed revenue
  2. Recycled 2024 : highest sends + highest cost -> lowest revenue per 1k sends
  3. List decay    : reply rate drops ~40% once list age > 60 days
  4. Bounce concentration: Recycled source ~= 70%+ of all bounces
Run:  python pb2_generator.py
Out:  ./pb2_data/*.csv
"""
import numpy as np
import pandas as pd
from pathlib import Path

SEED = 7
rng = np.random.default_rng(SEED)
OUT = Path(__file__).resolve().parent / "pb2_data"
OUT.mkdir(parents=True, exist_ok=True)

BDAYS = [d.date() for d in pd.bdate_range("2025-01-06", periods=60)]  # 60 business days
WINDOW_END = pd.Timestamp("2025-04-30")
BOOK_CUTOFF = pd.Timestamp("2025-04-21")
RECENT_CUTOFF = pd.Timestamp("2025-04-21")
TOTAL_SENDS = 14_400

SDRS = pd.DataFrame({
    "SDRID":    ["SDR-01", "SDR-02", "SDR-03"],
    "SDRName":  ["Ana Duarte", "Bruno Lima", "Carla Mendes"],
    "ReplyMult":[1.06, 1.00, 0.92],
})

SIZE_BANDS  = ["1-10", "11-50", "51-200", "201-1000", "1000+"]
TITLE_BANDS = ["C-Level", "VP", "Director", "Manager"]

INDUSTRY_MIX = {
    "LinkedIn_FinServ": [("FinServ", .80), ("SaaS", .10), ("Insurance", .10)],
    "Purchased_EcomEU": [("Ecom", .70), ("Retail", .15), ("Logistics", .15)],
    "Referral":         [("SaaS", .35), ("FinServ", .25), ("Healthcare", .20), ("Ecom", .20)],
    "JobChange":        [("SaaS", .40), ("FinServ", .20), ("Ecom", .20), ("Manufacturing", .20)],
    "Webinar":          [("SaaS", .30), ("Ecom", .25), ("Healthcare", .25), ("FinServ", .20)],
    "Recycled2024":     [("Ecom", .40), ("Retail", .25), ("Manufacturing", .20), ("Logistics", .15)],
}

SOURCES = {  # share, bounce, open, reply(of delivered), positive(of replies), unsub,
            # booked(of positive), show, close(of shown), won value range, est value range
    "LinkedIn_FinServ": dict(share=.18, bounce=.060, open=.45, reply=.050, positive=.30,
                             unsub=.004, booked=.58, show=.70, close=.34,
                             won=(2200, 4200), est=(1500, 4000)),
    "Purchased_EcomEU": dict(share=.18, bounce=.030, open=.55, reply=.042, positive=.22,
                             unsub=.010, booked=.52, show=.70, close=.34,
                             won=(1800, 4500), est=(1200, 3500)),
    "Referral":         dict(share=.03, bounce=.008, open=.70, reply=.180, positive=.55,
                             unsub=.002, booked=.60, show=.72, close=.30,
                             won=(3800, 6500), est=(3000, 8000)),
    "JobChange":        dict(share=.15, bounce=.020, open=.50, reply=.140, positive=.50,
                             unsub=.003, booked=.45, show=.72, close=.22,
                             won=(1800, 4200), est=(1200, 3500)),
    "Webinar":          dict(share=.12, bounce=.015, open=.62, reply=.060, positive=.35,
                             unsub=.006, booked=.52, show=.75, close=.34,
                             won=(2000, 4800), est=(1500, 4000)),
    "Recycled2024":     dict(share=.34, bounce=.200, open=.22, reply=.024, positive=.10,
                             unsub=.035, booked=.50, show=.70, close=.25,
                             won=(1500, 3500), est=(1000, 3000)),
}

BATCHES = [  # (name, source, purchase_date, cost)
    ("LinkedIn scrape - FinServ | Batch A (Jan)", "LinkedIn_FinServ", "2025-01-02", 1200),
    ("LinkedIn scrape - FinServ | Batch B (Feb)", "LinkedIn_FinServ", "2025-02-14", 1200),
    ("Purchased DB - Ecom EU | Batch A (Dec 24)", "Purchased_EcomEU", "2024-12-02", 1800),
    ("Purchased DB - Ecom EU | Batch B (Feb)",    "Purchased_EcomEU", "2025-02-21", 1800),
    ("Referral / network",                        "Referral",         "2025-01-02",  250),
    ("Job-change trigger | Batch A (Jan)",        "JobChange",        "2025-01-02",  900),
    ("Job-change trigger | Batch B (Mar)",        "JobChange",        "2025-03-03",  900),
    ("Inbound webinar | Batch A (Jan)",           "Webinar",          "2025-01-02",  600),
    ("Inbound webinar | Batch B (Feb)",           "Webinar",          "2025-02-28",  600),
    ("Recycled 2024 | Batch A (Jun 24)",          "Recycled2024",     "2024-06-10", 2500),
    ("Recycled 2024 | Batch B (Aug 24)",          "Recycled2024",     "2024-08-19", 2500),
]

CAMP = {
    "LinkedIn_FinServ": ("C01", "FinServ Outbound - LinkedIn scrape", "FinServ 51-1000"),
    "Purchased_EcomEU": ("C02", "Ecom EU - purchased DB",             "Ecom EU 11-200"),
    "Referral":         ("C03", "Referral & network follow-up",       "Warm network"),
    "JobChange":        ("C04", "Job-change trigger",                 "ICP movers"),
    "Webinar":          ("C05", "Inbound webinar follow-up",          "Webinar attendees"),
    "Recycled2024":     ("C06", "2024 recycled re-engagement",        "Cold 2024 base"),
}


def decay_mult(age_days: int) -> float:
    if age_days <= 30:
        return 1.00
    if age_days <= 60:
        return 0.88
    if age_days <= 90:
        return 0.68
    return 0.60


def age_bucket(age_days: int) -> str:
    if age_days <= 30:
        return "0-30d"
    if age_days <= 60:
        return "31-60d"
    if age_days <= 90:
        return "61-90d"
    return ">90d"


def pick_industry(source: str) -> str:
    inds, w = zip(*INDUSTRY_MIX[source])
    return str(rng.choice(inds, p=w))


# ---------------------------------------------------------------- build dims
dim_sdr = SDRS.copy()

dim_list = pd.DataFrame(
    [(f"L{i+1:02d}", name, src, pd.Timestamp(pdate).date(), cost)
     for i, (name, src, pdate, cost) in enumerate(BATCHES)],
    columns=["ListID", "ListName", "SourceType", "PurchaseDate", "PurchaseCost"],
)
batch_map = {f"L{i+1:02d}": (src, pd.Timestamp(pdate), cost)
             for i, (name, src, pdate, cost) in enumerate(BATCHES)}

dim_campaign = pd.DataFrame(
    [(cid, name, seg) for src, (cid, name, seg) in CAMP.items()],
    columns=["CampaignID", "CampaignName", "Segment"],
)

dim_date = pd.DataFrame({"DateKey": pd.bdate_range("2024-12-01", "2025-04-30")})
dim_date["Date"] = pd.to_datetime(dim_date["DateKey"]).dt.date
dim_date["Year"] = pd.to_datetime(dim_date["Date"]).dt.year
dim_date["MonthNo"] = pd.to_datetime(dim_date["Date"]).dt.month
dim_date["Month"] = pd.to_datetime(dim_date["Date"]).dt.strftime("%b")
dim_date["YearMonth"] = pd.to_datetime(dim_date["Date"]).dt.strftime("%Y-%m")
dim_date["YearMonthSort"] = dim_date["Year"] * 100 + dim_date["MonthNo"]
dim_date["IsBusinessDay"] = pd.to_datetime(dim_date["Date"]).dt.weekday < 5
dim_date = dim_date.drop(columns=["DateKey"])


# ---------------------------------------------------------------- build facts
send_rows, reply_rows, meeting_rows, prospect_rows = [], [], [], []
prospect_source = {}
sid = rid = mid = pid = 0

for source, cfg in SOURCES.items():
    n = int(round(TOTAL_SENDS * cfg["share"]))

    # prospect sequence sizes (1-3 steps) that consume exactly n sends
    sizes, total = [], 0
    while total < n:
        k = int(rng.choice([1, 2, 3], p=[.45, .40, .15]))
        sizes.append(k)
        total += k
    over = total - n
    i = len(sizes) - 1
    while over > 0:
        if sizes[i] > 1:
            take = min(sizes[i] - 1, over)
            sizes[i] -= take
            over -= take
        i -= 1

    days = [BDAYS[j] for j in rng.integers(0, len(BDAYS), size=n)]
    src_batches = [lid for lid, (s, _, _) in batch_map.items() if s == source]

    idx = 0
    for k in sizes:
        pid += 1
        PID = f"P{pid:05d}"
        prospect_rows.append((PID, pick_industry(source),
                              str(rng.choice(SIZE_BANDS)), str(rng.choice(TITLE_BANDS))))
        prospect_source[PID] = source
        seq = sorted(days[idx: idx + k])
        idx += k

        for step, d in enumerate(seq, start=1):
            sid += 1
            ts = pd.Timestamp(d)
            eligible = [lid for lid in src_batches if batch_map[lid][1] <= ts]
            lid = eligible[int(rng.integers(0, len(eligible)))] if eligible else src_batches[0]
            s_src, purchase_ts, _ = batch_map[lid]
            sdr = SDRS.iloc[int(rng.integers(0, len(SDRS)))]
            age = max((ts - purchase_ts).days, 0)

            bounced  = rng.random() < cfg["bounce"]
            delivered = not bounced
            opened   = delivered and (rng.random() < cfg["open"])
            replied  = delivered and (rng.random() < cfg["reply"] * decay_mult(age) * sdr["ReplyMult"])
            unsubbed = delivered and (rng.random() < cfg["unsub"])

            cid = CAMP[source][0]
            send_rows.append((f"S{sid:06d}", d, cid, lid, sdr["SDRID"], PID, step,
                              int(opened), int(replied), int(bounced), int(unsubbed), age))

            if replied:
                rid += 1
                reply_date = min(pd.Timestamp(d) + pd.Timedelta(days=int(rng.integers(0, 6))),
                                 WINDOW_END)
                if rng.random() < cfg["positive"]:
                    rclass = "Positive"
                else:
                    rclass = str(rng.choice(["Neutral", "Negative", "OOO"], p=[.45, .30, .25]))
                reply_rows.append((f"R{rid:05d}", f"S{sid:06d}", reply_date.date(), rclass))

                if rclass == "Positive" and rng.random() < cfg["booked"]:
                    booked = reply_date + pd.Timedelta(days=int(rng.integers(3, 15)))
                    if booked > BOOK_CUTOFF:
                        continue
                    mdate = booked + pd.Timedelta(days=int(rng.integers(0, 7)))
                    showed = rng.random() < cfg["show"]
                    if not showed:
                        outcome = "Pending" if rng.random() < .60 else "Lost"
                    elif mdate >= RECENT_CUTOFF:
                        outcome = "Pending"
                    elif rng.random() < cfg["close"]:
                        outcome = "Won"
                    else:
                        outcome = "Lost" if rng.random() < .70 else "Pending"
                    lo, hi = cfg["won"] if outcome == "Won" else cfg["est"]
                    value = round(float(rng.uniform(lo, hi)) / 50) * 50
                    mid += 1
                    meeting_rows.append((f"M{mid:05d}", PID, booked.date(), mdate.date(),
                                         int(showed), outcome, value))

fact_sends    = pd.DataFrame(send_rows, columns=["SendID", "DateKey", "CampaignID", "ListID",
                                                 "SDRID", "ProspectID", "Step", "OpenFlag",
                                                 "ReplyFlag", "BouncedFlag", "UnsubFlag",
                                                 "ListAgeDays"])
fact_replies  = pd.DataFrame(reply_rows, columns=["ReplyID", "SendID", "ReplyDate", "Class"])
fact_meetings = pd.DataFrame(meeting_rows, columns=["MeetingID", "ProspectID", "BookedDate",
                                                    "MeetingDate", "ShowedFlag", "Outcome",
                                                    "DealValue"])
dim_prospect  = pd.DataFrame(prospect_rows, columns=["ProspectID", "Industry", "SizeBand",
                                                     "TitleBand"])


# ---------------------------------------------------------------- export
fact_sends.to_csv(OUT / "fact_sends.csv", index=False, date_format="%Y-%m-%d")
fact_replies.to_csv(OUT / "fact_replies.csv", index=False, date_format="%Y-%m-%d")
fact_meetings.to_csv(OUT / "fact_meetings.csv", index=False, date_format="%Y-%m-%d")
dim_list.to_csv(OUT / "dim_list.csv", index=False)
dim_sdr.to_csv(OUT / "dim_sdr.csv", index=False)
dim_campaign.to_csv(OUT / "dim_campaign.csv", index=False)
dim_prospect.to_csv(OUT / "dim_prospect.csv", index=False)
dim_date.to_csv(OUT / "dim_date.csv", index=False)


# ---------------------------------------------------------------- validation
def section(title):
    print(f"\n=== {title} ===")


sends_per_src = fact_sends.merge(dim_list[["ListID", "SourceType"]], on="ListID") \
                          .groupby("SourceType")["SendID"].count()

won = fact_meetings[(fact_meetings["ShowedFlag"] == 1) & (fact_meetings["Outcome"] == "Won")].copy()
won["SourceType"] = won["ProspectID"].map(prospect_source)
rev_by_src = won.groupby("SourceType")["DealValue"].sum()

section("VOLUME & REVENUE BY SOURCE")
for src in SOURCES:
    s = sends_per_src.get(src, 0)
    r = rev_by_src.get(src, 0)
    print(f"{src:18s} sends {s:6,} ({s/len(fact_sends):6.1%})  "
          f"closed rev ${r:9,.0f} ({r/won['DealValue'].sum():6.1%})")

section("INSIGHT 1 - Referral: sends share vs closed-revenue share")
ref_s = sends_per_src.get("Referral", 0) / len(fact_sends)
ref_r = rev_by_src.get("Referral", 0) / won["DealValue"].sum()
print(f"Referral: {ref_s:.1%} of sends -> {ref_r:.1%} of closed revenue "
      f"(target ~3% -> ~31%)  {'PASS' if .28 <= ref_r <= .34 else 'CHECK'}")

section("INSIGHT 2 - Recycled: revenue per 1,000 sends (worst?)")
per1k = {src: rev_by_src.get(src, 0) / (sends_per_src.get(src, 1) / 1000) for src in SOURCES}
for src, v in sorted(per1k.items(), key=lambda kv: kv[1]):
    print(f"{src:18s} ${v:9,.0f} per 1k sends")
print(f"Recycled is worst: {'PASS' if min(per1k, key=per1k.get) == 'Recycled2024' else 'CHECK'}")

section("INSIGHT 3 - List decay: reply rate by list-age bucket")
fact_sends["AgeBucket"] = fact_sends["ListAgeDays"].apply(age_bucket)
g = fact_sends.groupby("AgeBucket").agg(sends=("SendID", "count"), replies=("ReplyFlag", "sum"))
g["reply_rate"] = g["replies"] / g["sends"]
g = g.reindex(["0-30d", "31-60d", "61-90d", ">90d"])
print(g["reply_rate"].apply(lambda x: f"{x:.2%}").to_string())
drop = 1 - (g.loc[["61-90d", ">90d"], "reply_rate"].mean() /
            g.loc[["0-30d", "31-60d"], "reply_rate"].mean())
print(f"Drop >60d vs <=60d: {drop:.0%} (target ~40%)  {'PASS' if .25 <= drop <= .55 else 'CHECK'}")

section("INSIGHT 4 - Bounce concentration (Recycled)")
b = fact_sends.merge(dim_list[["ListID", "SourceType"]], on="ListID").groupby("SourceType")["BouncedFlag"].sum()
share = b.get("Recycled2024", 0) / b.sum()
print(f"Recycled = {share:.0%} of all bounces (target ~70%)  {'PASS' if share >= .60 else 'CHECK'}")

section("FUNNEL TOTALS")
delivered = (fact_sends["BouncedFlag"] == 0).sum()
print(f"sends {len(fact_sends):,} | delivered {delivered:,} | replies {fact_sends['ReplyFlag'].sum():,} "
      f"| positives {(fact_replies['Class'] == 'Positive').sum()} | meetings {len(fact_meetings):,} "
      f"| showed {fact_meetings['ShowedFlag'].sum():,} | won {(fact_meetings['Outcome'] == 'Won').sum()} "
      f"| closed revenue ${won['DealValue'].sum():,.0f}")

print(f"\nFiles written to {OUT}")
