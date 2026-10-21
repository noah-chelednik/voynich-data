# Upstream tracking

Roadmap item 2.1. Every source VCAT builds from is a file René Zandbergen's voynich.nu serves, cached in
`data_sources/cache/` and pinned in `data_sources/sources.yaml` by its URL, SHA-256 and upstream version. Upstream
tracking checks that the site still serves those bytes, and says what changed when it does not.

## The weekly check

`.github/workflows/upstream.yml` runs every Monday (and on demand) on GitHub:
`python scripts/check_upstream.py` fetches every source the registry marks `url_fetched` and compares the bytes' SHA-256
with the pin. Its exit status: 0 when every source is unchanged, 1 when any changed, 2 when any could not be fetched,
3 when both, 4 when the check itself failed (an import that fails included). On a change (1 or 3) the workflow opens an
issue labelled `upstream-change` with the report (or comments on the one already open); on every other status but 0
(an unreachable source, a failed check, a check that did not finish) the run fails, so nothing goes unseen behind
anything else. The JSON and Markdown reports are kept as the
run's artifact. The workflow reads the code and writes issues, nothing else.

The check reports and never adopts. A new upstream version becomes VCAT's only as a change of its own: a new pin in
`data_sources/sources.yaml`, a rebuild, the suite and the review, an entry in `ERRATA.md` if the data changes.

The same command runs locally: `python scripts/check_upstream.py --markdown report.md`.

GitHub disables a scheduled workflow in a public repository after 60 days without activity in the repository; it then
stops with no failed run and no issue. A quiet data repository can reach that, so the weekly check is not a guarantee
by itself: the Actions tab shows the workflow as disabled, and enabling it there (or running it on demand) restarts it.
Whoever maintains the repository should look there whenever it has been quiet for two months.

## The source diff

For a changed source the report holds its diff against the cached file, locus by locus (`vcat/upstream.py`): a locus is
identified by its page, its number and, in an interlinear file, its transcriber, and it is

- added when only the new file holds it,
- removed when only the old file holds it,
- changed when both hold it and any byte of its lines differs: its identifier, the spacing after it, its text as
  written, a wrapped continuation, its line ending;
- moved when both hold it and its place among the loci both hold changed;

every other line (page headers, comments, a line the parser reports instead of reading as a locus, a line in no
encoding) is compared as its exact bytes, in order, within the gap after the locus it follows: a line outside the
gap's longest common run is removed or added, so a repeated line, a line moved to another place and lines reordered
within one gap are seen, and no line of either file is outside the comparison. Whatever the lists name, the two files
differ whenever their bytes do: `scripts/source_diff.py` exits 1 then (2 when it cannot compare a file at all), and the issue body says the bytes differ. Lines
are cut where the parser cuts them (CR LF, LF or CR), and nothing is decoded or normalised. Two loci with one identity in a file are refused, since the diff would lose one.

`python scripts/source_diff.py OLD NEW` gives the same diff for any two IVTFF files: each release's source diff report
is this command run on the files the previous release was built from against the files of the new one.
