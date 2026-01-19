# VCAT Source Verification Report
## Phase 0 Complete

**Date:** 2026-01-17
**Status:** ✓ PASS - All critical sources verified

---

## Summary

All required data sources for VCAT Horizon 1 have been verified and downloaded. We have two primary transcription sources available:

1. **Zandbergen-Landini (ZL) Transcription** - The most current, complete, and accurate EVA transcription
2. **Stolfi Interlinear File** - Historical interlinear format with multiple transcribers

Both sources are suitable for building the Horizon 1 datasets.

---

## Verified Sources

### 1. Zandbergen-Landini (ZL) Transcription
- **URL:** https://www.voynich.nu/data/ZL3b-n.txt
- **Status:** ✓ Accessible (HTTP 200)
- **Format:** IVTFF 2.0 with Extended EVA
- **Size:** 411,671 bytes
- **SHA256:** `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc`
- **Version:** 3b (May 2025)
- **Coverage:** Complete manuscript
- **Notes:**
  - Most accurate complete transcription available
  - Uses modern IVTFF 2.0 format with page variables
  - Includes extensive metadata ($Q=quire, $L=language, $H=hand, etc.)
  - Well-documented with inline comments

### 2. Takahashi IT Transcription (via voynich.nu)
- **URL:** https://www.voynich.nu/data/IT2a-n.txt
- **Status:** ✓ Accessible (HTTP 200)
- **Format:** IVTFF 2.0 with Basic EVA
- **Size:** 342,104 bytes
- **SHA256:** `7f27a8b0feed8f6de0a99900df6bf912dd1d295c38e5f830bac8b41c3f536fb5`
- **Coverage:** Complete manuscript
- **Notes:**
  - Extracted from LSI file, represents 1999 status
  - Useful for comparison with ZL

### 3. Stolfi Interlinear File (UNICAMP)
- **URL:** https://www.ic.unicamp.br/~stolfi/EXPORT/projects/voynich/Notes/104/work/L16+H-eva/text16e6.evt
- **Status:** ✓ Accessible (HTTP 200)
- **Format:** EVT (older interlinear format)
- **Size:** 1,680,872 bytes
- **SHA256:** `309e717d0dcc13115eace006eb40ece6c0ac89faab48f1569dcb9732d26b02f0`
- **Version:** Release 1.6e6 (Dec 1998)
- **Coverage:** Multiple transcribers interlinearly aligned
- **Includes:**
  - H: Takahashi (complete)
  - C: Currier
  - F: First Study Group (Friedman)
  - Plus others (L, R, K, J, etc.)
- **Notes:**
  - Historical reference value
  - Useful for transcription comparison/disagreement analysis

### 4. voynich.nu Website
- **URL:** https://www.voynich.nu/
- **Status:** ✓ Accessible (HTTP 200)
- **Content:** Comprehensive metadata resource
- **Key Pages:**
  - `/transcr.html` - Transcription overview and downloads
  - `/folios.html` - Folio-by-folio information
  - `/data/` - Direct data downloads
  - `/extra/sp_transcr.html` - Special topics

### 5. Stolfi UNICAMP Archive
- **URL:** https://www.ic.unicamp.br/~stolfi/voynich/
- **Status:** ✓ Accessible (HTTP 200)
- **Content:** Historical analyses and transcriptions
- **Notes:** Directory structure reorganized since original plan URLs

---

## Source Changes from Original Plan

The following URLs in the construction plan are outdated:

| Original URL | New URL | Status |
|-------------|---------|--------|
| `http://www.voynich.nu/data/beta/LSI_ivtff_0d.txt` | No longer at this path | Use ZL3b-n.txt instead |
| `http://www.voynich.nu/data/ivtff/ZL3a-n.txt` | Now at `/data/ZL3b-n.txt` | Version updated |
| `http://voynich.freie-literatur.de/` | May be inaccessible | Use voynich.nu instead |

**Recommendation:** Use ZL3b-n.txt from voynich.nu as primary source. It's more recent, complete, and uses the modern IVTFF 2.0 format.

---

## Data Format Summary

### IVTFF Format (ZL, IT files)
```
#=IVTFF Eva- 2.0 M 5                    # Header: format version
<f1r>      <! $Q=A $P=A ... >           # Page header with variables
<f1r.1,@P0> <%>fachys.ykal.ar.ataiin... # Locus: page.line,position text
```

Key IVTFF elements:
- Page variables: $Q (quire), $L (language), $H (hand), $I (illustration type)
- Locus format: `<page.line,position>`
- Position codes: @ (new unit), + (continue), = (end paragraph), * (new paragraph)
- Text markers: `.` (word separator), `-` (line break), `=` (paragraph end)
- Uncertainty: `[a:b]` (alternatives), `?` (uncertain), `!` (comment marker)

### Stolfi EVT Format
```
## <f1r.P1> {...}                        # Unit header
<f1r.P1.1;H> fachys.ykal.ar.ataiin...   # Line with transcriber code (;H = Takahashi)
```

Transcriber codes in Stolfi file:
- H: Takahashi
- C: Currier
- F: FSG (Friedman)
- A: Majority vote

---

## Files Downloaded

Location: `/home/claude/voynich-data/data_sources/raw_sources/`

| File | Source | Size |
|------|--------|------|
| ZL3b-n.txt | voynich.nu | 411,671 bytes |
| IT2a-n.txt | voynich.nu | 342,104 bytes |
| text16e6.evt | Stolfi UNICAMP | 1,680,872 bytes |
| 000_README.txt | voynich.nu | 3,940 bytes |
| checksums.txt | Generated | - |

---

## Recommended Primary Source Strategy

For VCAT Horizon 1:

1. **Primary EVA Dataset:** Use `ZL3b-n.txt` (Zandbergen-Landini)
   - Most accurate and complete
   - Modern IVTFF format
   - Rich metadata

2. **Mismatch Analysis:** Compare ZL against IT (Takahashi 1999 version)
   - Both complete
   - Different time periods
   - Same basic format

3. **Historical Reference:** Use `text16e6.evt` (Stolfi interlinear)
   - Contains Currier, FSG transcriptions
   - Useful for documenting transcription history

---

## Next Steps

Phase 0 is complete. Ready to proceed with Phase 1:

- [ ] Implement IVTFF parser for ZL format
- [ ] Build EVA lines dataset
- [ ] Extract metadata from page headers
- [ ] Validate against EVA character set specification

---

## Verification Protocol Results

All sources passed verification:
- ✓ URL accessible (HTTP 200)
- ✓ Content type matches expectations (text/plain)
- ✓ File format matches IVTFF/EVT specifications
- ✓ Page boundaries identifiable
- ✓ Line numbers present
- ✓ EVA character set confirmed
- ✓ No authentication required
- ✓ Local copies stored with checksums
