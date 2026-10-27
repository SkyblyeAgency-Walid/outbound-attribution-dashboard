# PB2 Data Dictionary

All dates are ISO `YYYY-MM-DD`. All flag columns are 0/1 integers.

## Fact tables

### fact_sends.csv - 14,400 rows (grain: one email send)

| Column | Type | Description |
|--------|------|-------------|
| SendID | text (PK) | Unique send id, `S000001`... |
| DateKey | date | Send date (business day). FK -> dim_date |
| CampaignID | text | FK -> dim_campaign |
| ListID | text | FK -> dim_list. **The attribution key** - drives all source analysis |
| SDRID | text | FK -> dim_sdr |
| ProspectID | text | FK -> dim_prospect. Bridge to fact_meetings (multi-hop attribution) |
| Step | int | Sequence position within the prospect's cadence (1-3) |
| OpenFlag | 0/1 | Email was opened (only possible if not bounced) |
| ReplyFlag | 0/1 | Prospect replied (only possible if delivered) |
| BouncedFlag | 0/1 | Send bounced (hard bounce; blocks open/reply) |
| UnsubFlag | 0/1 | Prospect unsubscribed from this send |
| ListAgeDays | int | Days between send date and the list batch's PurchaseDate (0 = fresh). Use for decay buckets: 0-30 / 31-60 / 61-90 / >90 |

### fact_replies.csv - 650 rows (grain: one reply)

| Column | Type | Description |
|--------|------|-------------|
| ReplyID | text (PK) | `R00001`... |
| SendID | text | FK -> fact_sends |
| ReplyDate | date | Reply received date (send date + 0-5 days, capped at window end) |
| Class | text | `Positive` (meeting-intent) / `Neutral` / `Negative` / `OOO` |

### fact_meetings.csv - 136 rows (grain: one booked meeting)

| Column | Type | Description |
|--------|------|-------------|
| MeetingID | text (PK) | `M00001`... |
| ProspectID | text | FK -> dim_prospect (which links back to sends -> list source) |
| BookedDate | date | Meeting booked on |
| MeetingDate | date | Meeting held on (BookedDate + 0-7 days) |
| ShowedFlag | 0/1 | Prospect attended |
| Outcome | text | `Won` / `Lost` / `Pending`. Revenue: count ONLY ShowedFlag=1 AND Outcome="Won" |
| DealValue | int | USD. For Won rows = closed revenue. For Lost/Pending rows = rough estimate placeholder - do NOT sum for revenue |

## Dimension tables

### dim_list.csv - 11 rows (grain: one purchased/scraped list batch)

| Column | Type | Description |
|--------|------|-------------|
| ListID | text (PK) | `L01`-`L11` |
| ListName | text | Human label incl. batch and purchase month |
| SourceType | text | The 6 sources: `LinkedIn_FinServ` / `Purchased_EcomEU` / `Referral` / `JobChange` / `Webinar` / `Recycled2024` |
| PurchaseDate | date | When the batch was acquired (drives ListAgeDays) |
| PurchaseCost | int | USD paid for the batch (drives cost-per-deal measures) |

### dim_campaign.csv - 6 rows

| Column | Type | Description |
|--------|------|-------------|
| CampaignID | text (PK) | `C01`-`C06`, 1:1 with SourceType |
| CampaignName | text | Campaign label |
| Segment | text | Target segment label |

### dim_prospect.csv - 8,519 rows

| Column | Type | Description |
|--------|------|-------------|
| ProspectID | text (PK) | `P00001`... |
| Industry | text | FinServ / SaaS / Insurance / Ecom / Retail / Logistics / Healthcare / Manufacturing |
| SizeBand | text | 1-10 / 11-50 / 51-200 / 201-1000 / 1000+ employees |
| TitleBand | text | C-Level / VP / Director / Manager |

### dim_sdr.csv - 3 rows

| Column | Type | Description |
|--------|------|-------------|
| SDRID | text (PK) | `SDR-01`-`SDR-03` |
| SDRName | text | Ana Duarte / Bruno Lima / Carla Mendes |
| ReplyMult | decimal | Latent reply-rate multiplier used by the generator (1.06 / 1.00 / 0.92). Useful as an Easter egg for SDR-level analysis |

### dim_date.csv - 108 rows (business days only)

| Column | Type | Description |
|--------|------|-------------|
| Date | date (PK) | 2024-12-02 to 2025-04-30, weekdays only |
| Year | int | Year |
| MonthNo | int | 1-12 - **sort key for Month** |
| Month | text | Jan / Feb / ... |
| YearMonth | text | `2025-01` format |
| YearMonthSort | int | `202501` - **sort key for YearMonth** |
| IsBusinessDay | bool | Always TRUE in this table (calendar is business days only) |

## Relationship map (Power BI)

```
fact_sends[DateKey]      *:1  dim_date[Date]
fact_sends[ListID]       *:1  dim_list[ListID]
fact_sends[CampaignID]   *:1  dim_campaign[CampaignID]
fact_sends[SDRID]        *:1  dim_sdr[SDRID]
fact_sends[ProspectID]   *:1  dim_prospect[ProspectID]
fact_replies[SendID]     *:1  fact_sends[SendID]
fact_meetings[ProspectID] *:1 dim_prospect[ProspectID]
```

Multi-hop attribution (list -> revenue) works because
`fact_meetings -> dim_prospect <- fact_sends -> dim_list` is a single unidirectional path.
