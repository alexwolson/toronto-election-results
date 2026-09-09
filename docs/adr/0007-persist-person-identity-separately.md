# Persist Person identity separately from Candidacies

Status: accepted

No in-scope election authority publishes a stable cross-election person identifier, and the current
name-derived fuzzy clusters both merge different people and renumber existing IDs when new names are
added. Every ballot appearance therefore has its own stable Candidacy ID and may link many-to-one to
an opaque, persistent Person ID in a versioned identity registry. Authoritative identifiers and
previously audited aliases may confirm links; fuzzy matching may only propose them. Unresolved links
remain null, Incumbency uses confirmed links only, and merge or split corrections retain an audited
history rather than silently recycling published Person IDs. The ongoing curation cost is accepted
in exchange for stable cross-office career identity. Evidence-backed agent curation may confirm a
link when the retained sources uniquely establish identity; there is no blanket human-review gate,
and ambiguous cases remain unresolved. Each Candidacy preserves its source name and a normalized
display form; a Person's separate canonical name and audited aliases never rewrite the historical
ballot record.

The People and Candidacy-Person link artifacts from the prior successful release are operational
inputs to the next release. New Candidacies extend that registry; the build does not recreate it
from names on every run. The initial migration deliberately ignores pre-ledger draft output so
name-derived draft Candidacy IDs cannot seed the persistent registry.
Before reuse, all three prior identity-bearing artifacts (`people`, Candidacy-Person links, and
election results) must match their prior build-manifest checksums. This makes closed link history,
not only the active link state, an append-only operational input. An interrupted publication whose
artifacts and manifest disagree requires explicit recovery rather than silently trusting or
re-bootstrapping the registry.

Review status is part of that history. A machine-generated `proposed` link must be closed when it is
adjudicated: sufficient evidence produces `confirmed`, insufficient evidence produces `unresolved`
while retaining the proposed Person for audit, and contrary evidence produces `rejected`. Only
`confirmed` populates the modelling table; reviewed holds therefore remain null without being
mistaken for untouched review debt.

People may exist without an in-scope Candidacy when a pre-window officeholder or appointee is
needed to classify Incumbency, or when an evidence-bearing downstream dataset names a registered
candidate who is absent from the final certified field. Those downstream aliases are explicit,
sourced curations: they neither create a Candidacy nor permit fuzzy matching. Identity research is
limited to people needed by in-scope release contracts rather than attempting a comprehensive
political-biography dataset.
