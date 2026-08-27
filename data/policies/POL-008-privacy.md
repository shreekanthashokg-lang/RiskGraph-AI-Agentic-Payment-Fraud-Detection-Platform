---
doc_id: POL-008
title: Data Minimization and Privacy
version: "1.0"
category: privacy
---

# Data Minimization and Privacy

- Local development and demo environments use synthetic or public-dataset
  data only; no real customer PII is stored.
- Identifiers used in the UI and logs are pseudonymous (e.g. cust_00042)
  rather than real names, phone numbers, or account numbers.
- Access to full audit trails and investigation cases is restricted to
  authenticated risk analyst roles (see Security section of the README for
  the authentication architecture this scaffold is built to support).
