# Security policy

## Supported versions

Only the latest commit on `main` receives fixes. There are no maintained release branches.

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub's advisory form:
https://github.com/hellpuffyt/pdf-tables/security/advisories/new

Do not open a public issue for a suspected vulnerability. Include the version or commit,
a minimal reproduction, and the impact you observed. You should receive an acknowledgement
within a few days; fixes are released as soon as they are verified.

## Scope

pdf-tables parses PDFs with pdfplumber/pdfminer and writes CSV files and a manifest into the `--out` directory; it makes no network calls. Relevant reports include: a crafted PDF that executes code, writes outside the output directory, or exhausts resources disproportionately. Note: CSV cells are written verbatim, so spreadsheet formula injection from untrusted PDFs is a documented limitation, not a bug.
