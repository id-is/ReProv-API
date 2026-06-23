# TODO

## Dependabot dependency vulnerabilities (in progress)

Auditing the built image with `pip-audit` (OSV/GitHub advisory data, same source
as Dependabot). `gh` is not authenticated in this environment, so we read alerts
via `pip-audit` instead.

### Flagged project dependencies (from `pip-audit` on `reprov-api-api`)

**starlette 0.36.3** — several advisories:
- CVE-2024-47874 (high, multipart DoS) → fixed in **0.40.0**
- CVE-2025-54121 → fixed in 0.47.2
- CVE-2026-48818 / 48817 → fixed in 1.1.0
- CVE-2026-54283 / 54282 → fixed in 1.3.x
- PYSEC-2026-161 → fixed in 1.0.1

**urllib3 1.26.20** — several advisories:
- CVE-2025-50181 → 2.5.0
- CVE-2025-66418 / 66471 → 2.6.0
- CVE-2026-21441 → 2.6.3
- PYSEC-2026-141 → 2.7.0

(pip / wheel / setuptools also show in pip-audit but are base-image build tooling,
not in `requirements.txt`, so not Dependabot-flagged for this repo. Optional: bump
them in the Dockerfile for hygiene.)

### Key constraints discovered (why we can't just bump)

- **urllib3 is hard-pinned `<2` transitively by `reana-client==0.9.2`**:
  `reana-client -> reana-commons -> bravado -> requests (urllib3>=1.26,<3)` and the
  rest of the REANA/cwltool stack expect the 1.26 line. Moving urllib3 to 2.x risks
  breaking `reana-client`. Need to verify whether reana-client 0.9.2 actually
  tolerates urllib3 2.x (requests itself allows `<3`); the blocker is the broader
  REANA stack (bravado/cwltool/yadage). **Likely cannot fix urllib3 without
  upgrading reana-client (no newer 0.9.x?) — investigate.**
- **starlette is pinned by `fastapi==0.110.0`** (`>=0.36.3,<0.37.0`). Bumping
  starlette requires bumping **fastapi**. `pydantic` stays `<2` (pinned to 1.10.26
  by reana stack); newer FastAPI still supports pydantic v1, but VERIFY.

### Plan / next steps

1. Bump `fastapi` + `starlette` together to clear the high-severity starlette
   CVE(s):
   - Try `fastapi>=0.115,<0.116` (pulls starlette 0.40.x → clears CVE-2024-47874).
     Reaching 0.47.2 / 1.x is likely NOT possible while staying on this FastAPI
     line; document residual low/moderate ones.
   - Confirm app still imports/boots and `pydantic==1.10.26` still works.
2. Investigate urllib3: test whether the image still builds + `reana-client`
   imports with `urllib3>=2.5`. If the REANA stack breaks, leave pinned and record
   as a known/accepted issue tied to reana-client 0.9.2 (and check for a newer
   reana-client release that relaxes it).
3. (Optional hygiene) In `Dockerfile`, `pip install --upgrade pip setuptools wheel`
   before installing requirements, to clear the base-image tooling advisories.
4. After each change: rebuild `reprov-api-api`, run `pytest tests -q` in the image,
   and do a boot smoke test (`docker compose ... up`, hit `/docs`).
5. Update `requirements.txt` and commit on a branch, then push/merge as usual
   (keep `doc/`, `mock*`, `aiod.override.yml` out).

### Useful commands

```bash
# audit installed versions
docker run --rm reprov-api-api bash -c "pip install -q pip-audit && pip-audit --progress-spinner off"
# why is urllib3 constrained
docker run --rm reprov-api-api bash -c "pip install -q pipdeptree && pipdeptree -r -p urllib3"
```
