# PROM pipeline stats

## Legend

- `n_found`: number of .pdf/.docx files discovered in the directory
- `n_extract_ok`: extraction returned a `PromForm`
- `n_extract_bad`: extraction returned an error string (problem file)
- `bad_files`: filenames (no paths) for extract-bad files
- `n_none`: extraction returned `None`
- `n_duplicates`: duplicates removed by `filter_duplicates`
- `n_unique`: remaining unique forms after dedupe
- `n_embed_ok`: passed embed validation and completed embedding/insertion step
- `n_embed_skip_missing`: skipped due to missing/empty required fields
- `n_embed_skip_empty`: skipped due to empty embed string
- Percentages are out of `n_found`.

---

## Run: 2026-02-27 00:00:25

### Directory: `2019`

- n_found: **166**
- n_extract_ok: **148** (89.2%)
- n_extract_bad: **18** (10.8%)
- n_none: **0** (0.0%)
- n_duplicates: **92** (55.4%)
- n_unique: **56** (33.7%)
- n_embed_ok: **55** (33.1%)
- n_embed_skip_missing: **1** (0.6%)
- n_embed_skip_empty: **0** (0.0%)
- timing_sec: extract=0.45, dedupe=0.00, embed=3.80, total=4.24

- bad_files (18):
  - `attachment(1).pdf`
  - `attachment(10).pdf`
  - `attachment(13).PDF`
  - `attachment(17).pdf`
  - `attachment(2).pdf`
  - `attachment(34).docx`
  - `attachment(35).docx`
  - `attachment(4).pdf`
  - `attachment(45).docx`
  - `attachment-0001(12).PDF`
  - `attachment-0001(16).pdf`
  - `attachment-0001(27).docx`
  - `attachment-0001(33).docx`
  - `attachment-0001(51).docx`
  - `attachment-0001(6).pdf`
  - `attachment-0001(8).pdf`
  - `attachment-0001(9).pdf`
  - `attachment-0002(1).pdf`

- extract_bad_reasons (top 5):
  - `Can't find target: 1. The chemical or material in ../files/promForms/2019/attachment(35).docx`: **1**
  - `Can't find target: 1. The chemical or material in ../files/promForms/2019/attachment(1).pdf`: **1**
  - `Can't find target: 1. The chemical or material in ../files/promForms/2019/attachment-0001(16).pdf`: **1**
  - `Can't find target: 1. The chemical or material in ../files/promForms/2019/attachment(13).PDF`: **1**
  - `Can't find target: 1. The chemical or material in ../files/promForms/2019/attachment(34).docx`: **1**

- embed_skipped_files:
  - missing_required:
    - `attachment-0002(2).pdf`

### Directory: `2020`

- n_found: **66**
- n_extract_ok: **64** (97.0%)
- n_extract_bad: **2** (3.0%)
- n_none: **0** (0.0%)
- n_duplicates: **38** (57.6%)
- n_unique: **26** (39.4%)
- n_embed_ok: **26** (39.4%)
- n_embed_skip_missing: **0** (0.0%)
- n_embed_skip_empty: **0** (0.0%)
- timing_sec: extract=0.22, dedupe=0.00, embed=3.96, total=4.18

- bad_files (2):
  - `attachment-0001(3).docx`
  - `attachment-0001(9).docx`

- extract_bad_reasons (top 5):
  - `Can't find target: 1. The chemical or material in ../files/promForms/2020/attachment-0001(9).docx`: **1**
  - `Can't find target: 1. The chemical or material in ../files/promForms/2020/attachment-0001(3).docx`: **1**

### Directory: `2021`

- n_found: **188**
- n_extract_ok: **176** (93.6%)
- n_extract_bad: **12** (6.4%)
- n_none: **0** (0.0%)
- n_duplicates: **109** (58.0%)
- n_unique: **67** (35.6%)
- n_embed_ok: **62** (33.0%)
- n_embed_skip_missing: **5** (2.7%)
- n_embed_skip_empty: **0** (0.0%)
- timing_sec: extract=0.71, dedupe=0.00, embed=4.56, total=5.27

- bad_files (12):
  - `attachment(11).docx`
  - `attachment(21).docx`
  - `attachment(39).docx`
  - `attachment(55).docx`
  - `attachment-0001(41).docx`
  - `attachment-0001(42).docx`
  - `attachment-0001(45).docx`
  - `attachment-0001(64).docx`
  - `attachment-0002(2).docx`
  - `attachment-0002(8).docx`
  - `attachment-0003(1).docx`
  - `attachment-0003(4).docx`

- extract_bad_reasons (top 5):
  - `Can't find target: 2. Vendor/manufacturer info in ../files/promForms/2021/attachment(11).docx`: **1**
  - `Can't find target: 2. Vendor/manufacturer info in ../files/promForms/2021/attachment-0001(41).docx`: **1**
  - `Can't find target: 2. Vendor/manufacturer info in ../files/promForms/2021/attachment-0001(45).docx`: **1**
  - `Can't find target: 2. Vendor/manufacturer info in ../files/promForms/2021/attachment-0002(8).docx`: **1**
  - `Can't find target: 2. Vendor/manufacturer info in ../files/promForms/2021/attachment-0001(64).docx`: **1**

- embed_skipped_files:
  - missing_required:
    - `attachment(37).docx`
    - `attachment(60).docx`
    - `attachment-0001(12).docx`
    - `attachment-0001(58).docx`
    - `attachment-0001(69).docx`

