
const app = document.getElementById("app");
const modalRoot = document.getElementById("modal-root");

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
}[c]));

async function api(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function navigate(path) {
  history.pushState({}, "", path);
  router();
}

window.addEventListener("popstate", router);

function urgencyClass(value) {
  return `badge-${String(value || "low").toLowerCase().replace(" ", "-")}`;
}

function projectCard(p) {
  const s = p.summary || {};
  return `
    <article class="card" onclick="navigate('/project/${encodeURIComponent(p.id)}')">
      <div class="heading">
        <span class="muted">#${s.ranking ?? "—"}</span>
        <span class="badge ${urgencyClass(s.urgency)}">${esc(s.urgency || "Not assessed")}</span>
      </div>
      <h2>${esc(p.road_name)}</h2>
      <div class="muted">${esc(p.location)} · ${esc(p.road_type)}</div>
      <div class="project-meta">
        <div class="meta"><small>Priority</small><b class="priority">${s.priority_index ?? "—"}</b></div>
        <div class="meta"><small>Latest inspection</small><b>${esc(p.inspections?.at(-1)?.date || "None")}</b></div>
      </div>
      <div class="scorebar"><span style="width:${Math.min(s.priority_index || 0, 100)}%"></span></div>
    </article>`;
}

async function showDashboard() {
  app.innerHTML = `<div class="loading">Loading road intelligence...</div>`;
  const projects = await api("/projects/");
  const assessed = projects.filter(p => p.summary?.priority_index != null);
  const critical = assessed.filter(p => p.summary.urgency === "Critical").length;
  const high = assessed.filter(p => ["Very High", "High"].includes(p.summary.urgency)).length;
  app.innerHTML = `
    <div class="heading">
      <div><h1>Road Priority Overview</h1><div class="muted">Live view of inspected road assets</div></div>
    </div>
    <section class="grid stats">
      <div class="stat"><span class="muted">Total Roads</span><b>${projects.length}</b></div>
      <div class="stat"><span class="muted">Critical</span><b>${critical}</b></div>
      <div class="stat"><span class="muted">High Priority</span><b>${high}</b></div>
      <div class="stat"><span class="muted">Assessed</span><b>${assessed.length}</b></div>
    </section>
    <section class="grid cards">
      ${projects.length ? projects.map(projectCard).join("") : `<div class="empty">No road projects yet. Add your first project.</div>`}
    </section>`;
}

async function showProject(id) {
  const p = await api(`/projects/${encodeURIComponent(id)}`);
  const s = p.summary || {};
  app.innerHTML = `
    <button class="back" onclick="navigate('/dashboard')">← Dashboard</button>
    <div class="heading">
      <div><h1>${esc(p.road_name)}</h1><div class="muted">${esc(p.location)} · ${esc(p.road_type)}</div></div>
      <div class="actions">
        <button class="ghost" onclick="openEditProject('${esc(p.id)}')">Edit</button>
        <button class="primary" onclick="openInspectionModal('${esc(p.id)}')">+ Inspection</button>
        <button class="danger" onclick="deleteProject('${esc(p.id)}')">Delete</button>
      </div>
    </div>

    <section class="grid info-grid">
      <div class="panel">
        <div class="muted">CURRENT PRIORITY</div>
        <div class="priority">${s.priority_index ?? "—"}</div>
        <span class="badge ${urgencyClass(s.urgency)}">${esc(s.urgency || "Not assessed")}</span>
        <div class="scorebar"><span style="width:${s.priority_index || 0}%"></span></div>
      </div>
      <div class="panel">
        <h3>Road Profile</h3>
        <div class="project-meta">
          <div class="meta"><small>Length</small><b>${p.length_km ?? "—"} km</b></div>
          <div class="meta"><small>Traffic</small><b>${esc(p.traffic_level || "—")}</b></div>
          <div class="meta"><small>Importance</small><b>${esc(p.importance || "—")}</b></div>
          <div class="meta"><small>Ranking</small><b>#${s.ranking ?? "—"}</b></div>
        </div>
        <div class="muted">${esc(p.importance_details || "")}</div>
        <div class="section"><b>Connectivity</b><div class="muted">${esc(p.connectivity || "—")}</div></div>
      </div>
    </section>

    <section class="section">
      <div class="heading"><h2>Inspection History</h2></div>
      <div class="panel">
        ${(p.inspections || []).length ? p.inspections.map(i => `
          <div class="inspection" onclick="navigate('/project/${encodeURIComponent(p.id)}/inspection/${encodeURIComponent(i.id)}')">
            <div class="heading">
              <div><b>${esc(i.date)}</b><div class="muted">${esc(i.inspector || "Inspector not specified")}</div></div>
              <span>${i.images?.length || 0} image(s) →</span>
            </div>
          </div>`).join("") : `<div class="empty">No inspections yet.</div>`}
      </div>
    </section>`;
}

async function showInspection(projectId, inspectionId) {
  const p = await api(`/projects/${encodeURIComponent(projectId)}`);
  const i = p.inspections.find(x => x.id === inspectionId);
  if (!i) return navigate(`/project/${encodeURIComponent(projectId)}`);

  app.innerHTML = `
    <button class="back" onclick="navigate('/project/${encodeURIComponent(projectId)}')">← ${esc(p.road_name)}</button>
    <div class="heading">
      <div><h1>Inspection</h1><div class="muted">${esc(i.date)} · ${esc(i.inspector || "Inspector not specified")}</div></div>
      <button class="danger" onclick="deleteInspection('${esc(projectId)}','${esc(inspectionId)}')">Delete</button>
    </div>
    <section class="grid info-grid">
      <div class="panel">
        <div class="muted">PROJECT PRIORITY</div>
        <div class="priority">${p.summary?.priority_index ?? "—"}</div>
        <span class="badge ${urgencyClass(p.summary?.urgency)}">${esc(p.summary?.urgency || "Not assessed")}</span>
      </div>
      <div class="panel">
        <h3>Maintenance</h3>
        <div class="muted">Last maintenance</div>
        <b>${esc(i.maintenance?.last_maintenance_date || "—")}</b>
        <p class="muted">${esc(i.maintenance?.notes || "")}</p>
      </div>
    </section>

    <section class="section">
      <div class="heading"><h2>AI Inspection Results</h2></div>
      <div class="grid images">
        ${(i.images || []).map(image => imageCard(image)).join("")}
      </div>
    </section>`;
}

function imageCard(image) {
  const ai = image.ai_inspection || {};
  const yolo = image.yolo || {};

  const imagePath = image.yolo_path || image.original_path;

  const imageUrl = "/" + imagePath
    .replaceAll("\\", "/")
    .replace(/^data\/uploads\//, "uploads/")
    .replace(/^\/+/, "");

  return `
    <article class="image-card">

      <img
        src="${esc(imageUrl)}"
        alt="${esc(image.filename)}"
      >

      <div class="body">

        <div class="heading">
          <b>${esc(image.filename)}</b>
          <span class="badge ${urgencyClass(ai.severity)}">
            ${esc(ai.severity || "—")}
          </span>
        </div>

        <h3>
          ${esc(ai.overall_condition || "Assessment pending")}
        </h3>

        <div class="muted">
          YOLO ·
          Potholes: ${yolo.class_counts?.Potholes || 0}
          · Top confidence:
          ${yolo.pothole_top_confidence ?? "—"}
        </div>

        <div class="findings">
          ${(ai.observed_deterioration || [])
      .map(x => `<span class="finding">${esc(x)}</span>`)
      .join("")}
        </div>

        <div class="section">
          <b>Agent reasoning</b>
          <p class="muted">
            ${esc(ai.reasoning || "—")}
          </p>
        </div>

        <div>
          <b>Recommended action</b>
          <p class="muted">
            ${esc(ai.recommended_action || "—")}
          </p>
        </div>

        ${(ai.safety_concerns || []).length
      ? `
              <div>
                <b>Safety concerns</b>
                <p class="muted">
                  ${ai.safety_concerns.map(esc).join(" · ")}
                </p>
              </div>
            `
      : ""
    }

      </div>
    </article>
  `;
}

function modal(title, body) {
  modalRoot.innerHTML = `
    <div class="modal-backdrop" onclick="if(event.target===this)closeModal()">
      <div class="modal">
        <div class="modal-head"><h2>${title}</h2><button class="ghost" onclick="closeModal()">✕</button></div>
        ${body}
      </div>
    </div>`;
}
function closeModal() { modalRoot.innerHTML = ""; }

function openProjectModal(project = null) {
  const edit = !!project;
  modal(edit ? "Edit Road Project" : "Add Road Project", `
    <form onsubmit="submitProject(event, ${edit ? `'${project.id}'` : "null"})">
      <div class="form-grid">
        ${field("road_name", "Road name", project?.road_name, true)}
        ${field("location", "Location", project?.location)}
        ${field("road_type", "Road type", project?.road_type)}
        ${field("length_km", "Length (km)", project?.length_km, "", "number")}
        ${field("importance", "Importance", project?.importance)}
        ${field("traffic_level", "Traffic level", project?.traffic_level)}
        ${field("importance_details", "Importance details", project?.importance_details, true, "textarea")}
        ${field("connectivity", "Connectivity", project?.connectivity, true, "textarea")}
      </div>
      <div class="modal-actions"><button type="button" class="ghost" onclick="closeModal()">Cancel</button><button class="primary">${edit ? "Save changes" : "Create project"}</button></div>
    </form>`);
}
function field(name, label, value = "", full = false, type = "text") {
  if (type === "textarea") return `<div class="${full ? "form-full" : ""}"><label>${label}</label><textarea name="${name}" rows="3">${esc(value)}</textarea></div>`;
  return `<div class="${full ? "form-full" : ""}"><label>${label}</label><input name="${name}" type="${type}" value="${esc(value)}" ${name === "road_name" ? "required" : ""}></div>`;
}
async function submitProject(e, id) {
  e.preventDefault();
  const form = new FormData(e.target);
  const body = Object.fromEntries(form.entries());
  if (body.length_km) body.length_km = Number(body.length_km);
  const result = id
    ? await api(`/projects/${encodeURIComponent(id)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
    : await api("/projects/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  closeModal();
  navigate(`/project/${encodeURIComponent(result.id)}`);
}
function openEditProject(id) {
  api(`/projects/${encodeURIComponent(id)}`).then(p => openProjectModal(p));
}

function openInspectionModal(projectId) {
  modal("New Inspection", `
    <form onsubmit="submitInspection(event,'${esc(projectId)}')">
      <div class="form-grid">
        ${field("date", "Inspection date", new Date().toISOString().slice(0, 10), false, "date")}
        ${field("inspector", "Inspector")}
        ${field("last_maintenance_date", "Last maintenance date", "", "", "date")}
        ${field("maintenance_notes", "Maintenance notes", "", "form-full", "textarea")}
        ${field("notes", "Inspection notes", "", "form-full", "textarea")}
        <div class="form-full"><label>Road images</label><input name="images" type="file" accept="image/*" multiple required></div>
      </div>
      <div class="modal-actions"><button type="button" class="ghost" onclick="closeModal()">Cancel</button><button class="primary">Analyze inspection</button></div>
    </form>`);
}
async function submitInspection(e, projectId) {
  e.preventDefault();
  const fd = new FormData(e.target);
  const res = await api(`/inspections/${encodeURIComponent(projectId)}`, { method: "POST", body: fd });
  closeModal();
  navigate(`/project/${encodeURIComponent(projectId)}/inspection/${encodeURIComponent(res.inspection.id)}`);
}

async function deleteProject(id) {
  if (!confirm("Delete this project and all its inspections?")) return;
  await api(`/projects/${encodeURIComponent(id)}`, { method: "DELETE" });
  navigate("/dashboard");
}
async function deleteInspection(projectId, id) {
  if (!confirm("Delete this inspection and its images?")) return;
  await api(`/projects/${encodeURIComponent(projectId)}/inspections/${encodeURIComponent(id)}`, { method: "DELETE" });
  navigate(`/project/${encodeURIComponent(projectId)}`);
}

function router() {
  const path = window.location.pathname.replace(/\/+$/, "") || "/dashboard";
  const parts = path.split("/").filter(Boolean);
  if (!parts.length || parts[0] === "dashboard") return showDashboard();
  if (parts[0] === "project" && parts[2] === "inspection") return showInspection(parts[1], parts[3]);
  if (parts[0] === "project") return showProject(parts[1]);
  navigate("/dashboard");
}

router();
