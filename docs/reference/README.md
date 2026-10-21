# Offline references (not redistributed)

The files in this directory, except this README, are git-ignored. They are local copies of upstream documents so that the
independent reviewer, which runs offline inside the repository, can read them. Their redistribution rights are not
established, so they are never committed or published. Re-create them on a fresh clone with the commands below.

| file | source | sha256 (fetched 2026-10-08) |
|---|---|---|
| `IVTFF_format.pdf` | https://www.voynich.nu/software/ivtt/IVTFF_format.pdf (file format 2.0.1, document issue 2.0.2, 08/07/2025) | `7ac9c4a82064763cac8767cca6f661cc4e1b4503ab9342acc03032ddb6939d49` |
| `IVTFF_format.txt` | `pdftotext -layout IVTFF_format.pdf IVTFF_format.txt` (poppler) | derived |
| `voynich.nu_extra_sol_ent.html` | https://www.voynich.nu/extra/sol_ent.html (updated 10/12/2024; fetched 2026-10-21) | `f4d19d8415917c02d18add71aed409d04f3c19da51f409bb2ce4f3d599d033a5` |
| `voynich.nu_a4_word.html` | https://www.voynich.nu/a4_word.html (updated 24/05/2025; fetched 2026-10-21) | `66741a7d13cb3c5718236adaa215341a5fdb71bc407421d3ea3de57506069999` |

The two voynich.nu pages are the pinned sources of the reference checks (`data_sources/references.yaml`;
`python scripts/check_references.py` checks their hashes and quotes):

```
curl -sSfL -o docs/reference/voynich.nu_extra_sol_ent.html https://www.voynich.nu/extra/sol_ent.html
curl -sSfL -o docs/reference/voynich.nu_a4_word.html https://www.voynich.nu/a4_word.html
```

```
curl -sSfL -o docs/reference/IVTFF_format.pdf https://www.voynich.nu/software/ivtt/IVTFF_format.pdf
sha256sum docs/reference/IVTFF_format.pdf
pdftotext -layout docs/reference/IVTFF_format.pdf docs/reference/IVTFF_format.txt
```

Zandbergen's `ivtt` tool is not fetched yet; if it is used for differential testing it goes here too, and it is never run
from inside the repository.
