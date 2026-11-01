const ROLE = { mess: "Mess", ngo: "NGO", rider: "Rider" };

let sitting = new Date().getHours() < 16 ? "lunch" : "dinner";
let loc = null;
let busy = false;

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function show(id) {
  for (const node of document.querySelectorAll("main > section")) node.hidden = true;
  document.getElementById(id).hidden = false;
  window.scrollTo(0, 0);
}

function flash(id, text) {
  const node = document.getElementById(id);
  if (!text) {
    node.hidden = true;
    node.textContent = "";
    return;
  }
  node.hidden = false;
  node.textContent = text;
}

function detail(data) {
  if (!data) return "Something went wrong.";
  if (typeof data.detail === "string") return data.detail;
  if (data.message) return data.message;
  return "Something went wrong.";
}

async function api(path, options = {}) {
  const opts = { credentials: "include", ...options };
  if (opts.body) opts.headers = { "content-type": "application/json" };
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  data._status = res.status;
  return data;
}

function role() {
  return document.querySelector('input[name="role"]:checked').value;
}

function syncRole() {
  const current = role();
  document.getElementById("field-fssai").hidden = current === "rider";
  document.getElementById("field-veg-mess").hidden = current !== "mess";
  document.getElementById("field-veg-ngo").hidden = current !== "ngo";
  document.getElementById("field-upi").hidden = current !== "rider";
}

function setLoc(next) {
  loc = next;
  document.getElementById("loc-label").textContent = next
    ? `Location set to ${next.area}`
    : "No location yet";
  for (const chip of document.querySelectorAll("#area-picks button")) {
    chip.classList.toggle("on", next && chip.dataset.area === next.area);
  }
}

async function loadAreas() {
  const data = await api("/api/areas");
  const box = document.getElementById("area-picks");
  box.innerHTML = "";
  for (const area of data.areas || []) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "chip";
    button.textContent = area.label;
    button.dataset.area = area.label;
    button.addEventListener("click", () => setLoc({ lat: area.lat, lng: area.lng, area: area.label }));
    box.appendChild(button);
  }
}

function localStamp(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function prepTimes() {
  const prep = document.getElementById("rel-prep");
  const useBy = document.getElementById("rel-useby");
  if (!prep.value) prep.value = localStamp(new Date());
  if (!useBy.value) useBy.value = localStamp(new Date(Date.now() + 4 * 60 * 60 * 1000));
}

function prettyDate(iso) {
  const [year, month, day] = String(iso || "").split("-").map(Number);
  if (!year || !month || !day) return iso || "";
  return new Date(year, month - 1, day).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
}

function track(state) {
  const labels = ["Rider", "Pickup", "Drop", "Received", "Paid"];
  const index = {
    draft_match: 0,
    awaiting_rider: 0,
    awaiting_pickup: 1,
    awaiting_drop: 2,
    awaiting_received: 3,
    awaiting_pay: 4,
    settled: 5,
  }[state];
  if (index == null) return "";
  return `<ol class="track">${labels.map((label, i) => {
    const cls = i < index ? "done" : i === index ? "now" : "";
    return `<li class="${cls}"><span></span>${esc(label)}</li>`;
  }).join("")}</ol>`;
}

function paintBoard(data) {
  const person = data.me;
  document.getElementById("who-role").textContent = ROLE[person.role] || person.role;
  document.getElementById("who-name").textContent = person.display_name;
  document.getElementById("who-meta").textContent = `${person.area} · ${prettyDate(data.sitting_date)}`;
  document.getElementById("km").textContent = String(data.nearby_km).replace(/\.0$/, "");
  document.getElementById("sit-lunch").classList.toggle("on", data.sitting === "lunch");
  document.getElementById("sit-dinner").classList.toggle("on", data.sitting === "dinner");

  const recordPanel = document.getElementById("panel-record");
  const record = data.record;
  recordPanel.hidden = !record;
  if (record) {
    const plates = Number(record.plates_handed_over) || 0;
    document.getElementById("record-total").innerHTML = `${esc(plates)} <span>plates handed over</span>`;
    document.getElementById("record-caption").textContent = plates
      ? `${record.row_count} Schedule II ${record.row_count === 1 ? "row" : "rows"}. Counted only after an NGO confirms receipt.`
      : "Schedule II starts when an NGO confirms they received the food.";
    document.getElementById("record-item7").textContent = record.item_7
      ? "Eat Right Campus item 7 can be marked yes: safe surplus was shared. This is audit evidence for the campus, not a payment."
      : "Eat Right Campus item 7 stays unmarked until plates are handed over.";
    const box = document.getElementById("record-rows");
    box.innerHTML = record.rows.length
      ? `<table class="register"><thead><tr><th>Date</th><th>Kitchen</th><th>Food</th><th>Plates</th><th>°C</th></tr></thead><tbody>${
        record.rows.map((line) => `<tr><td>${esc(line.date)}${line.sitting ? `<br>${esc(line.sitting)}` : ""}</td><td>${esc(line.kitchen)}</td><td>${esc(line.food)}</td><td>${esc(line.plates)}</td><td>${esc(line.temp_c ?? "—")}</td></tr>`).join("")
      }</tbody></table>`
      : "";
  }

  const needPanel = document.getElementById("panel-need");
  const releasePanel = document.getElementById("panel-release");
  needPanel.hidden = person.role !== "ngo";
  releasePanel.hidden = person.role !== "mess";
  document.getElementById("need-text").textContent = data.need_text || "";
  document.getElementById("need-form").hidden = !data.need_open;
  document.getElementById("release-text").textContent = data.release_text || "";
  document.getElementById("release-form").hidden = !data.release_open;
  document.getElementById("no-leftover").hidden = !data.release_open;
  if (person.veg_policy === "veg" || person.veg_policy === "nonveg") {
    document.getElementById("rel-veg").value = person.veg_policy;
  }
  if (person.role === "ngo" && person.veg_policy) {
    document.getElementById("need-veg").value = person.veg_policy;
  }
  prepTimes();

  const trips = document.getElementById("trips");
  document.getElementById("trip-section").hidden = !data.trips.length && person.role !== "rider";
  if (!data.trips.length) {
    const idle = {
      ngo: "Ask for plates. When a nearby mess releases safe leftover, a rider is assigned.",
      mess: "Release unused food. A nearby NGO request can match it.",
      rider: "When a nearby mess and NGO match, Accept shows up here.",
    }[person.role];
    trips.innerHTML = `<p class="fine">${esc(idle)}</p>`;
  } else {
    trips.innerHTML = data.trips.map((trip) => `
      <article class="trip">
        <h3>${esc(trip.title)}</h3>
        <p class="meta">${esc(trip.state_label)}</p>
        ${track(trip.state)}
        <p class="meta">From ${esc(trip.from)}</p>
        <p class="meta">Rider · ${esc(trip.rider)}</p>
        ${trip.pack ? `<p>${esc(trip.pack)}</p>` : ""}
        ${trip.pay ? `<p class="pay">${esc(trip.pay)}</p>` : ""}
        ${trip.actions.length ? `<div class="actions">${trip.actions.map((action, index) =>
          `<button type="button" class="${index ? "secondary" : ""}" data-act="${esc(action.id)}" data-trip="${esc(trip.id)}">${esc(action.label)}</button>`
        ).join("")}</div>` : ""}
      </article>
    `).join("");
  }

  const updates = document.getElementById("updates");
  updates.innerHTML = data.updates.length
    ? data.updates.map((line) => `<p>${esc(line)}</p>`).join("")
    : `<p class="fine">No messages yet.</p>`;

  const nearby = document.getElementById("nearby");
  nearby.innerHTML = data.nearby.length
    ? data.nearby.map((item) => {
      const away = Number(item.distance_km) < 0.05 ? "Here" : `${item.distance_km} km`;
      const initial = String(item.display_name || "?").trim().charAt(0).toUpperCase();
      const detailLine = [item.note, item.veg_policy].filter(Boolean).join(" · ");
      return `
        <article class="person">
          <span class="avatar">${esc(initial)}</span>
          <div>
            <strong>${esc(item.display_name)}</strong>
            <span class="meta">${esc(ROLE[item.role] || item.role)} · ${esc(item.area)}</span>
            <span class="meta">${esc(detailLine)}</span>
          </div>
          <span class="dist">${esc(away)}</span>
        </article>`;
    }).join("")
    : `<p class="fine">No one else is within ${esc(data.nearby_km)} km yet.</p>`;
}

async function showBoard(message) {
  const data = await api(`/api/board?sitting=${sitting}`);
  if (data._status === 401) {
    show("view-home");
    return;
  }
  if (!data.ok) {
    flash("flash", detail(data));
    show("view-board");
    return;
  }
  paintBoard(data);
  flash("flash", message || "");
  show("view-board");
}

function bind() {
  document.getElementById("go-register").addEventListener("click", async () => {
    flash("reg-flash", "");
    if (!document.getElementById("area-picks").children.length) await loadAreas();
    syncRole();
    show("view-register");
  });
  document.getElementById("go-login").addEventListener("click", () => {
    flash("login-flash", "");
    show("view-login");
  });
  document.getElementById("reg-back").addEventListener("click", () => show("view-home"));
  document.getElementById("login-back").addEventListener("click", () => show("view-home"));
  document.querySelectorAll("#login-form [data-phone]").forEach((button) => {
    button.addEventListener("click", () => {
      document.getElementById("login-phone").value = button.dataset.phone;
      document.getElementById("login-pin").value = button.dataset.pin;
      document.getElementById("login-form").requestSubmit();
    });
  });
  document.querySelectorAll('input[name="role"]').forEach((input) => {
    input.addEventListener("change", syncRole);
  });
  document.getElementById("use-location").addEventListener("click", () => {
    if (!navigator.geolocation) {
      flash("reg-flash", "This browser has no location. Pick a demo area.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLoc({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          area: "Current location",
        });
        flash("reg-flash", "");
      },
      () => flash("reg-flash", "Location was blocked. Pick a demo area instead.")
    );
  });
  document.getElementById("reg-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    if (!loc) {
      flash("reg-flash", "Set a location first.");
      return;
    }
    const current = role();
    const payload = {
      role: current,
      display_name: document.getElementById("reg-name").value,
      phone: document.getElementById("reg-phone").value,
      pin: document.getElementById("reg-pin").value,
      area: loc.area,
      lat: loc.lat,
      lng: loc.lng,
      fssai: document.getElementById("reg-fssai").value,
      upi_id: document.getElementById("reg-upi").value,
      veg_policy: current === "mess"
        ? document.getElementById("reg-veg-mess").value
        : document.getElementById("reg-veg-ngo").value,
    };
    busy = true;
    const data = await api("/api/register", { method: "POST", body: JSON.stringify(payload) });
    busy = false;
    if (!data.ok) {
      flash("reg-flash", detail(data));
      return;
    }
    await showBoard("Account created.");
  });
  document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    busy = true;
    const data = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({
        phone: document.getElementById("login-phone").value,
        pin: document.getElementById("login-pin").value,
      }),
    });
    busy = false;
    if (!data.ok) {
      flash("login-flash", detail(data));
      return;
    }
    await showBoard("");
  });
  document.getElementById("sign-out").addEventListener("click", async () => {
    await api("/api/logout", { method: "POST", body: "{}" });
    show("view-home");
  });
  document.getElementById("sit-lunch").addEventListener("click", async () => {
    sitting = "lunch";
    await showBoard("");
  });
  document.getElementById("sit-dinner").addEventListener("click", async () => {
    sitting = "dinner";
    await showBoard("");
  });
  document.getElementById("need-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    busy = true;
    const data = await api("/api/need", {
      method: "POST",
      body: JSON.stringify({
        sitting,
        plates: Number(document.getElementById("need-plates").value),
        veg_policy: document.getElementById("need-veg").value,
      }),
    });
    busy = false;
    await showBoard(detail(data));
  });
  document.getElementById("release-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    busy = true;
    const data = await api("/api/release", {
      method: "POST",
      body: JSON.stringify({
        sitting,
        plates: Number(document.getElementById("rel-plates").value),
        dishes: document.getElementById("rel-dishes").value,
        veg: document.getElementById("rel-veg").value,
        temp_c: Number(document.getElementById("rel-temp").value),
        prep_at: document.getElementById("rel-prep").value,
        use_by: document.getElementById("rel-useby").value,
        unused_not_served: document.getElementById("rel-unused").checked,
        packed_covered: document.getElementById("rel-packed").checked,
        insulated: document.getElementById("rel-insulated").checked,
        perishable: true,
      }),
    });
    busy = false;
    await showBoard(detail(data));
  });
  document.getElementById("no-leftover").addEventListener("click", async () => {
    if (busy) return;
    busy = true;
    const data = await api("/api/none", { method: "POST", body: JSON.stringify({ sitting }) });
    busy = false;
    await showBoard(detail(data));
  });
  document.getElementById("check-again").addEventListener("click", async () => {
    if (busy) return;
    busy = true;
    const data = await api("/api/match", { method: "POST", body: JSON.stringify({ sitting }) });
    busy = false;
    await showBoard(detail(data));
  });
  document.getElementById("trips").addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-act]");
    if (!button || busy) return;
    busy = true;
    const data = await api(`/api/trips/${button.dataset.trip}/${button.dataset.act}`, {
      method: "POST",
      body: "{}",
    });
    busy = false;
    await showBoard(detail(data));
  });
}

async function boot() {
  bind();
  const data = await api("/api/me");
  if (data.signed_in && data.id) await showBoard("");
  else show("view-home");
}

boot();
