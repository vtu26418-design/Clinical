## GitHub milestones and review rules
Keep one repository. Extract a later cumulative ZIP to a temporary folder, compare changes, and copy its contents into your existing project root. Preserve your `.git`, private data, local experiments and personal edits. Do not nest week ZIPs inside one another or overwrite your work blindly.

Commit actual work throughout each week. Example messages: `week1: explain missing-sales audit`, `week2: verify seasonal baseline`, `week3: compare validation errors`, `week4: test forecast export`. Make your own documented experiments and explanations; supplied code is a reference, not fabricated evidence of your work. Do not backdate or create empty commits to imitate internship activity.

After checking a real milestone you may tag it:
```bash
git tag -a week-1-complete -m "Week 1 data audit and EDA"
git push origin week-1-complete
```
Use your assigned member branch if working in a team. Solo workers may use main under the supplied execution rules. Push regularly, and preserve Git history when upgrading ZIP contents.

According to the uploaded execution PDF: complete two projects in two months; mid-review requires commits on at least 10 distinct days in the preceding 14-day period, collectively across the team repository; final review requires activity on every day of the preceding 20 days. Weekly tags do not replace daily activity. Submit the Work Distribution Document before Month 1 mid-review. Respond within 24 hours; report 48-hour unresponsiveness via the organization's stated process while continuing independent work.

The document conflicts about final-review windows: its detailed section says 5th–10th of the next month; summary/reminders say 7th–15th. Confirm your actual assigned date/timezone with your mentor. Prepare a review-ready package by the 4th where applicable; continue meaningful work until review.

## Final report checklist
- Business question and forecast horizon.
- Dataset source/terms/acquisition date, canonical schema and filtering.
- Missing dates, zero sales, stockout and return limitations.
- Train/validation/test dates and leakage boundaries.
- Measured baseline/model comparison and chosen model rationale.
- Error analysis by product/time, with units and sample counts.
- Inventory inputs, equations and assumptions; no fabricated observed stock.
- Application screenshots and reproduction commands.
- Tests executed and outcomes; environment/package versions.
- Supplied starter code versus your contribution, team responsibilities and limitations.

YouTube channel-search links deliberately point to topic searches within the named educator's channel; select the relevant current lesson. Learn concepts and practise here rather than copying arbitrary tutorial results.
