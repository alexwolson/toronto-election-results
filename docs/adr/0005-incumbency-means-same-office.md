# Incumbency means holding the same office category

Status: accepted

The dataset previously treated any sitting Toronto City Council member as an incumbent when they
ran for Mayor. That person-based rule collapses two different modelling signals once federal,
provincial, and school-board results are included. An **Incumbent** now means a candidate who belongs
to the last valid sitting roster for the same Office type and Represented body before the Election
event. For a dissolved legislature, this is the roster immediately before dissolution.
Electoral-district and boundary-regime changes do not end incumbency, but changing Office type or
Represented body does: a City Councillor running for Mayor, an MP running for MPP, or a trustee
changing School Boards is not an Incumbent in the new Contest. Person ID remains consistent across
Offices, allowing downstream consumers to derive broader officeholding and career-history features
without storing a separate cross-office `officeholder` flag.

An incumbent `true` requires a confirmed Person link and a supporting Office tenure in that final
sitting roster. `false` additionally requires a sufficiently complete roster to establish that the
Person was absent; otherwise Incumbency is null rather than guessed.
