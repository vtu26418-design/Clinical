# Canonical daily sales schema

| Field | Type | Meaning | Validation |
|---|---|---|---|
| date | YYYY-MM-DD | Observation date | Daily, timezone-free, valid |
| store | string | Store identifier | Nonempty; leading zeros preserved when reading CSV |
| item | string | Product identifier | Nonempty |
| sales | number | Observed units sold | Finite, nonnegative |

One row per date/store/item. All observations inside a selected series must be daily-contiguous; forecasting series must end on the same date. No inventory, lead-time, promotion or price field is inferred. Generated practice data is not measured retail demand. Downloaded sales may be constrained by stockouts.
