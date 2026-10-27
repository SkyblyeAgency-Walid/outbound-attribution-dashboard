# PB2 - QA Backup (demo defense)

Answers to the questions a technical viewer (agency head of delivery, analytics
lead, or a skeptical founder) will ask. Keep these in your head, not on screen.

---

**Q: Is this real data?**
No - fully synthetic, generated with a seeded script (seed=7, `etl/pb2_generator.py`
in the repo, reproducible byte-for-byte). It's modeled on a realistic 3-SDR program:
14,400 sends over 60 business days, 6 sources with distinct quality profiles. The
product is the methodology and the model, not the numbers.

**Q: How does revenue get attributed back to a list source?**
Multi-hop path through the star schema: `fact_meetings -> dim_prospect <- fact_sends
-> dim_list`. The generator guarantees each prospect is contacted from exactly one
source (verified - source-pure), so there is no double counting. Meeting -> prospect
-> sends -> list is a single unidirectional path.

**Q: Why single-direction relationships? Why CROSSFILTER in measures?**
Bidirectional filtering at model level creates ambiguity risk as the model grows and
transfers filters in ways visuals don't make visible. The bridge is owned explicitly
by the meeting measures via `CROSSFILTER(..., BOTH)` - the filter path is documented
in DAX where reviewers can see it. Same discipline as an enterprise model.

**Q: How does the Quality Score work?**
Five components with fixed weights: reply rate 30, positive-reply rate 25, bounce
rate 20 (inverted - lowest bounce gets full points), show rate 15, close rate 10.
Each component is normalized against the best source in the current selection, so
best-in-class = full points and the total reads 0-100. Components are separate
measures, so the stacked-bar visual shows exactly where the points come from.

**Q: What about small samples - Recycled shows a 100% show rate?**
Correct and called out on the page: it's 3 meetings. That's why the score page
carries an n-caveat and why the cost page (page 3) is the decisive one for
Recycled - $5,000 per deal, 0.7x ROI needs no sample-size defense. With a client's
real volumes the noise shrinks; the model doesn't change.

**Q: Why does the cost page have no month slicer?**
`List Spend` is batch-level: a batch's full purchase cost counts once its sends
appear in the filter context. Slicing by month would count the same batch in
multiple months. Page 3 is fixed-window economics by design - it's labeled on the
page.

**Q: What does list age mean exactly?**
Days between the send date and the batch's purchase date, stored per send
(`ListAgeDays`), bucketed 0-30 / 31-60 / 61-90 / >90. The sort key column pattern
(`List Age Sort`) is the same trick used for Month/YearMonth - text buckets always
get a numeric sort key.

**Q: How would you run this on our real data?**
Page 5 is the mapping template: their export needs source/list name, list cost and
purchase date, send-level flags, reply class, and meeting outcomes with values.
Tables rename to the same fact_/dim_ schema, types and relationships per the setup
doc, and all ~45 measures work unchanged. Typical week-one deliverable: their
verdict sentence on the cover - "[X]% of sends produced [Y]% of revenue".

**Q: What's the model size / performance story?**
8 tables, ~24k fact rows, star schema, no bidirectionals, measures over calculated
columns only where row logic is needed. This class of model loads in seconds and
renders instantly - the same architecture scales to hundreds of thousands of sends
before any optimization is needed (aggregations, then incremental refresh).

**Q: Why [DealValue for Lost/Pending] rows exist if revenue ignores them?**
Pipeline visibility: the pending tail is real (meetings booked, outcome unknown).
The model separates "won revenue" from "pipeline value" so the client sees both;
only Won-and-shown rows feed revenue measures.

**Q: What would make you change a SCALE/REPAIR/RETIRE call?**
Two consecutive months with the component evidence moving - e.g., a REPAIR source
whose reply points hold but bounce points collapse after a fresh batch. The
disposition thresholds (70 / 45) are policy, not math - adjustable per client risk
appetite.
