# Restricted-access ECG datasets

Datasets that require formal approval, an MTA, or institutional credentials
before HeartScan can use them. None of these are checked into the repo and
none are pulled by the default download scripts. Document any approval
status changes here so future operators can pick up the trail.

## CODE (full Brazilian dataset, ~2.47 M ECGs)

| Field | Value |
|-------|-------|
| Owner | Telesalud, Universidade Federal de Minas Gerais (UFMG) |
| Licence | Material Transfer Agreement (MTA), case-by-case |
| Volume | 2,470,424 ECGs / 1,773,689 patients (2010-2016) |
| Lead time | 4–8 weeks for review |
| Form | <https://docs.google.com/forms/d/e/1FAIpQLSfSHnaQIJo5OyXh01V6FTvlWi5qOEpsP6a28kZYMvfye4v_rw/viewform> |
| Required from us | Affiliation letter, intended use statement, MTA signed by both legal teams |
| Compatible with HeartScan? | Research yes; commercial requires explicit clearance in the MTA |

Operational steps:

1. Draft the research-question paragraph and run it past legal.
2. Submit the Google form on behalf of the institution; archive the response.
3. When approved, request the access link + receive `code_full.tar` (TBs).
4. Mirror to encrypted storage; never replicate to laptops.
5. Add the dataset to [`docs/DATASHEET_TRAINING.md`](DATASHEET_TRAINING.md)
   with the license clause from the MTA.

## UK Biobank ECG (~90 K resting + ~90 K exercise)

| Field | Value |
|-------|-------|
| Owner | UK Biobank Ltd. |
| Licence | Research project approval per data field |
| Volume | ~90,000 resting 12-lead + ~90,000 exercise 4-lead |
| Lead time | 6–12 weeks for project registration + IRAS-style review |
| Form | <https://www.ukbiobank.ac.uk/enable-your-research/apply-for-access> |
| Cost | Access fees apply per project |
| Required from us | UK Biobank registered researcher account; bona fide research project; data management plan |
| Compatible with HeartScan? | Research only. **Cannot ship derived weights** without UK Biobank publication review. |

Operational steps:

1. Register a UK Biobank account; obtain bona fide researcher status.
2. Submit a project application that explicitly names the ECG data fields
   (5984 resting, 5991 exercise, etc.) and the analysis plan.
3. Pay the access fee.
4. Use only the secure environment recommended by UK Biobank for analysis.
5. Any model trained with UK Biobank data must go through a Material
   Outputs review before publication or deployment.

## Apple Heart Study (~419 K participants)

Not publicly released. The Apple Heart Study published aggregate results
but did not distribute the raw PPG/ECG data. Track <https://med.stanford.edu/appleheartstudy.html>
for any future releases.

## Other access-controlled datasets

| Dataset | Status |
|---------|--------|
| Hefei Hi-Tech Cup 2019 / Tianchi | Hosted on Tianchi; account required; competition over. |
| AHA Database | Restricted distribution by the American Heart Association. |
| China PLA General Hospital | Not publicly released. |

## Status log

| Date | Dataset | Action | Owner |
|------|---------|--------|-------|
| 2026-04-19 | CODE full | Not yet requested | TBD |
| 2026-04-19 | UK Biobank | Not yet requested | TBD |
| 2026-04-19 | MIMIC-IV-ECG | CITI training pending | TBD |

Update this table whenever an application is submitted or its status
changes; treat it as the audit trail for compliance.
