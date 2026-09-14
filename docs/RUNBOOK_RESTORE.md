# Runbook — restoring the encrypted database backup

Closes the runbook half of TD-73. The other half is
[`.github/workflows/db-backup.yml`](../.github/workflows/db-backup.yml), which
produces the artifact this document consumes.

**A backup that has never been restored is a hypothesis.** The point of this
file is to turn it into a fact, on a calm afternoon, before it matters. Walk it
end to end once and write the date in *Rehearsal log* at the bottom.

---

## Last rehearsed

| Date | By | Artifact restored | Result | Notes |
| --- | --- | --- | --- | --- |
| _(never)_ | | | | Fill this in the first time. Until there is a row here, the backup is unverified. |

---

## 0. What you need before you start

| Thing | Where it comes from | If you don't have it |
| --- | --- | --- |
| `BACKUP_PASSPHRASE` | The founder's password manager | **Stop. The backup cannot be opened.** It exists nowhere else — not in the repository, not in GitHub, not recoverable from Anthropic or GitHub support. |
| Docker Desktop | Installed locally | Install it. The restore needs PostgreSQL **17** with `pgvector`, and `pgvector/pgvector:pg17` provides both in one command. |
| `gpg` | Ships with Git for Windows — already on PATH in Git Bash | `gpg --version` |
| The artifact | GitHub Actions run page | See step 1 |

**Use PostgreSQL 17, not 16.** Production is 17.6. Restoring a 17 dump into a
16 server is not a supported direction and can fail on catalog differences — and
a rehearsal that doesn't match the server major isn't a rehearsal. This is why
the runbook uses Docker rather than a local install: the version is pinned in
the command instead of being whatever is on the machine.

All commands below are **Git Bash** (not PowerShell).

---

## 1. Download the artifact

Browser route, which is the one that always works:

1. GitHub → **Actions** → **DB backup** → pick a successful run.
2. Scroll to **Artifacts** → click `db-backup-YYYY-MM-DD` → it downloads a `.zip`.
3. Unzip it. Inside is a single file: `dump.pgc.gpg`.

With the `gh` CLI, if you have it on the machine you are using:

```bash
gh run download <run-id> -n db-backup-YYYY-MM-DD
```

**Keep the run page open in a tab.** Step 6 compares against numbers printed in
that run's log, and you want the two side by side.

```bash
cd /c/Users/<you>/Downloads/db-backup-YYYY-MM-DD   # wherever you unzipped it
ls -l dump.pgc.gpg
```

---

## 2. Decrypt

```bash
gpg --output dump.pgc --decrypt dump.pgc.gpg
```

`gpg` prompts for the passphrase. On success you get `dump.pgc`, a
PostgreSQL custom-format archive.

Two checks worth ten seconds, because both failure modes look like success
until much later:

```bash
head -c 5 dump.pgc          # must print exactly: PGDMP
pg_restore --list dump.pgc | head -20   # optional; needs pg_restore locally
```

If the magic bytes are not `PGDMP`, stop — the file is not an archive and
nothing downstream will tell you so clearly.

> The workflow already performs this same decrypt-and-read-the-TOC check on
> every run, before it uploads anything. So a failure here means the artifact
> was damaged in download or the wrong passphrase was used — not that a bad
> backup was published.

---

## 3. Start PostgreSQL 17 with pgvector

```bash
docker run --name pg-restore \
  -e POSTGRES_PASSWORD=postgres \
  -p 55432:5432 \
  -d pgvector/pgvector:pg17
```

Port **55432** on the host, deliberately — it will not collide with a local
PostgreSQL on 5432, and it is visibly not production.

This mirrors what `backend-ci.yml` already does with `pgvector/pgvector:pg16`
for the live-Postgres test job; the tag differs because CI builds a *schema*
from migrations while this restores a *production dump*.

Wait a few seconds, then confirm it is up:

```bash
docker exec pg-restore pg_isready -U postgres
```

---

## 4. Create the database and the extension

```bash
docker exec pg-restore createdb -U postgres philosopher_restore

docker exec pg-restore psql -U postgres -d philosopher_restore \
  -c 'CREATE EXTENSION IF NOT EXISTS vector;'
```

**This step is mandatory and the restore fails without it.** `pg_dump
--schema=public` does **not** emit `CREATE EXTENSION` — extensions are only
dumped when no schema filter is given. Four columns in the dump are typed
`vector(1536)` (`memory_entries.embedding`, `source_chunks.embedding`, and the
two HNSW indexes over them), so without the extension the restore dies on type
resolution.

`vector` must land in **`public`**, which is where the bare `CREATE EXTENSION`
above puts it, and where production has it. (The abandoned Ireland project has
it in `extensions` instead — one of several reasons not to use that project as a
reference for anything.)

**Which extensions to create** is not guesswork: every backup run logs the
target's full extension list under **"INSTALLED EXTENSIONS"**. Read that section
of the run you are restoring. As of 2026-09-14 only `vector` matters for a
`--schema=public` restore; `pgcrypto`, `uuid-ossp` and `pg_stat_statements` live
in the `extensions` schema and are not referenced by public objects, and
`postgres_fdw` is installed but unused (no foreign servers, no foreign tables) —
a leftover from the May 2026 Ireland→Oregon migration.

**No Supabase roles are needed.** RLS is enabled on all 39 public tables but
there are **zero policies** — deny-all by default, with the API connecting as
the owner, which bypasses RLS. So the dump contains `ALTER TABLE … ENABLE ROW
LEVEL SECURITY` and no `CREATE POLICY`, and nothing references `anon`,
`authenticated` or `service_role`. You do not need to pre-create them.

---

## 5. Restore

```bash
docker cp dump.pgc pg-restore:/tmp/dump.pgc

docker exec pg-restore pg_restore \
  --no-owner \
  --no-privileges \
  -U postgres \
  -d philosopher_restore \
  /tmp/dump.pgc 2>&1 | tee restore.log
```

`--no-owner --no-privileges` match how the dump was taken: production's roles
(`postgres.<project-ref>`, `supabase_admin`, …) do not exist in the container
and are irrelevant to verifying the data.

**On errors:** `pg_restore` can report non-fatal errors and still produce a
correct database — that is normal for a cross-environment restore and is why
the command above does *not* use `--exit-on-error`. **Step 6 is the pass/fail
criterion, not a clean `restore.log`.**

> **First rehearsal:** paste whatever errors you actually see into *Known
> benign restore errors* at the bottom of this file. Right now that section is
> empty because this has not been run yet, and an empty list is honest where a
> guessed one would be worse than useless — the next person under pressure needs
> to know which errors are expected and which are new.

---

## 6. Verify — the three counts

This is the step that decides whether the restore worked.

```bash
docker exec pg-restore psql -U postgres -d philosopher_restore -c "
  SELECT 'users' AS table, count(*) FROM public.users
  UNION ALL SELECT 'memory_entries', count(*) FROM public.memory_entries
  UNION ALL SELECT 'weekly_letters', count(*) FROM public.weekly_letters
  ORDER BY 1;"
```

Compare against the **"DUMP-TIME VERIFICATION COUNTS"** block in that run's log
(workflow step *Record dump-time state*). The workflow prints exactly these
three counts, in this order, for exactly this reason — without them "it
restored" means only "`pg_restore` exited 0".

**All three must match exactly.** They are counts of the same rows at the same
instant; the dump is a single consistent snapshot, so there is no legitimate
reason for drift. A mismatch means the restore is incomplete — investigate, do
not round off.

For orientation, the production numbers on 2026-09-14 were `users` 22,
`memory_entries` 994, `weekly_letters` 26. **Do not verify against these** —
they grow daily. Verify against the log of the run you restored.

A worthwhile extra check, since embeddings are the bulk of the data and the
thing most likely to be quietly mangled:

```bash
docker exec pg-restore psql -U postgres -d philosopher_restore -c "
  SELECT count(*) AS chunks,
         count(embedding) AS with_embedding,
         (SELECT vector_dims(embedding) FROM public.source_chunks
           WHERE embedding IS NOT NULL LIMIT 1) AS dims
  FROM public.source_chunks;"
```

`dims` must be `1536`. If the vector type had failed to restore properly you
would find out here rather than months later.

---

## 7. Clean up

```bash
docker rm -f pg-restore
rm -f dump.pgc            # the PLAINTEXT copy of the whole database
```

**Delete `dump.pgc`.** It is an unencrypted copy of every user's conversations
sitting in your Downloads folder. Keep `dump.pgc.gpg` if you want; it is
encrypted and harmless.

Then add a row to *Rehearsal log*.

---

## What this backup does NOT contain

Worth knowing before an incident, not during one:

- **Only the `public` schema.** `auth`, `storage`, `realtime`, `vault` and
  `supabase_migrations` are excluded. That is currently lossless — `auth.users`
  and `storage.objects` are both empty, there are no cross-schema foreign keys,
  and authentication is the app's own OTP flow in `public.otp_codes`. The
  workflow **asserts this on every run** and fails if it stops being true, so
  this paragraph cannot quietly go stale.
- **No Supabase project configuration** — API keys, connection settings,
  extensions enabled at the project level, Vault secrets.
- **No Render or Netlify environment variables.** See
  [`DEPLOY_NOTES.md`](DEPLOY_NOTES.md) for what those need to be.
- **Not the passphrase.** Losing it loses every backup, all at once.
- **Restoring *into* production is not covered here** and is a different,
  far riskier operation. This runbook restores to a throwaway local container.
  If you ever need to restore production itself, stop and think it through
  rather than adapting these commands under pressure.

---

## Known benign restore errors

_Empty until the first rehearsal. Record what step 5 actually printed, with a
one-line note on why each is harmless._

---

## Rehearsal log

_Add a row each time the full procedure is walked end to end. Copy the row into
the table at the top of this file too._

| Date | By | Artifact | Counts matched | Notes |
| --- | --- | --- | --- | --- |
