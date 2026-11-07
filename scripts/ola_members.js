// Collect every member of the Legislative Assembly of Ontario from the 35th Parliament on.
//
// ola.org serves its member pages to browsers only, so this runs in a browser tab open on
// https://www.ola.org/. Paste it into the developer console. It reads the list of members for
// each Parliament, then each member's profile, and saves one JSON file:
//
//   { retrieved_on, parliaments: {35: "...dates..."}, members: {slug: {...}} }
//
// Each member keeps the profile's name, the "Dates of service" rows, the "Riding
// representation" rows (riding, Parliament, start and end) and the "Party affiliation(s)" rows.
// scripts/build_ontario_members.py turns the file into data/reference/ontario_legislature_members.csv.

(async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const day = (time) => (time ? time.getAttribute("datetime").slice(0, 10) : "");
  const text = (node) => (node ? node.textContent.replace(/\s+/g, " ").trim() : "");
  const page = async (path) =>
    new DOMParser().parseFromString(await (await fetch(path)).text(), "text/html");

  const parliaments = {};
  const members = {};
  for (let parliament = 35; parliament <= 44; parliament++) {
    const doc = await page(`/en/members/parliament-${parliament}`);
    parliaments[parliament] = text(
      [...doc.querySelectorAll("h1, h2")].find((h) => /Parliament/.test(h.textContent)),
    );
    for (const row of doc.querySelectorAll("table tbody tr")) {
      const link = row.querySelector('a[href*="/members/all/"]');
      if (!link) continue;
      const slug = link.getAttribute("href").split("/members/all/")[1].split(/[?#]/)[0];
      const cells = [...row.querySelectorAll("td")].map((cell) => cell.textContent.trim());
      (members[slug] ||= { slug, list_name: cells[0], parliaments: [] }).parliaments.push([
        parliament,
        cells[1],
      ]);
    }
    await sleep(400);
  }

  for (const slug of Object.keys(members)) {
    const doc = await page(`/en/members/all/${slug}`);
    const member = members[slug];
    member.name = text(doc.querySelector("h1"));
    const heading = [...doc.querySelectorAll("h2")].find(
      (h) => h.textContent.trim() === "Dates of service",
    );
    const service =
      heading?.closest(".view") || doc.querySelector('[id^="collapsemember-dates-of-service"]');
    member.service = [...(service?.querySelectorAll(".views-row") || [])].map(
      (row) => {
        const field = (name) => row.querySelector(`.views-field-field-${name}`);
        return {
          start: day(field("start-date")?.querySelector("time")),
          start_reason: text(field("start-reason")).replace(/[()]/g, "").trim(),
          end: day(field("end-date")?.querySelector("time")),
          end_reason: text(field("end-reason")).replace(/[()]/g, "").trim(),
        };
      },
    );
    member.ridings = [];
    let riding = "";
    const ridings = doc.querySelector('[id^="collapsemember-riding-representation"]');
    for (const node of ridings ? ridings.querySelectorAll("h4, .views-row") : []) {
      if (node.tagName === "H4") {
        riding = text(node);
        continue;
      }
      // A former member's row has separate start and end fields; a current member's row has
      // one field with the start and, for an earlier Parliament, the end.
      const times = node.querySelectorAll("time");
      member.ridings.push({
        riding,
        parliament: text(node.querySelector("h5")),
        start: day(times[0]),
        end: day(times[1]),
      });
    }
    const parties = doc.querySelector('[id^="collapsemember-party-affiliations"]');
    member.parties = [...(parties ? parties.querySelectorAll("p") : [])].map((p) => {
      const times = p.querySelectorAll("time");
      return { party: (p.childNodes[0]?.textContent || "").trim(), start: day(times[0]), end: day(times[1]) };
    });
    await sleep(250);
  }

  const retrieved_on = new Date().toISOString().slice(0, 10);
  const blob = new Blob([JSON.stringify({ retrieved_on, parliaments, members }, null, 1)], {
    type: "application/json",
  });
  const anchor = document.createElement("a");
  anchor.href = URL.createObjectURL(blob);
  anchor.download = `ola-members-${retrieved_on}.json`;
  anchor.click();
})();
