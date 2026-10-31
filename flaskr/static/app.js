const state = {
  dashboard: { plazas_total: 0, plazas_ocupadas: 0, plazas_disponibles: 0, estancias_activas: [] },
  clientes: [],
  vehiculos: [],
  plazas: [],
  operadores: [],
  editingSpaceId: null,
  toastTimer: null,
};

const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[character]);

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers },
  });
  if (response.status === 204) return null;
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error?.message || "No se pudo completar la operación.");
  return payload;
}

function notify(message, isError = false) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("visible");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => toast.classList.remove("visible"), 3500);
}

function formatDate(value) {
  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function showView(name) {
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("active", view.id === `view-${name}`);
  });
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.viewTarget === name);
  });
  const titles = { overview: "Resumen", entries: "Entradas y salidas", people: "Clientes y vehículos", spaces: "Plazas" };
  $("#page-title").textContent = titles[name] || "Resumen";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderStayRows(stays, target) {
  $(target).innerHTML = stays.map((stay) => `
    <tr>
      <td><span class="vehicle-pill">${escapeHtml(stay.matricula)}</span></td>
      <td>${escapeHtml(stay.cliente)}</td>
      <td>${escapeHtml(stay.plaza)}</td>
      <td>${escapeHtml(formatDate(stay.entrada))}</td>
      <td>${escapeHtml(stay.operador)}</td>
      <td><button class="button button-secondary button-small" data-exit-id="${stay.id}">Registrar salida</button></td>
    </tr>`).join("");
}

function renderParkingLot(plazas, stays) {
  const activeBySpace = new Map(stays.map((stay) => [stay.plaza_id, stay]));
  $("#parking-lot").innerHTML = plazas.map((space) => {
    const stay = activeBySpace.get(space.id);
    return `
      <article class="parking-space ${stay ? "is-occupied" : "is-available"}" title="${escapeHtml(space.codigo)}: ${stay ? `ocupada por ${escapeHtml(stay.matricula)}` : "disponible"}">
        <span class="parking-space-code">${escapeHtml(space.codigo)}</span>
        <span class="parking-car" aria-hidden="true">${stay ? "🚘" : "✓"}</span>
        <span class="parking-space-status">${stay ? escapeHtml(stay.matricula) : "Disponible"}</span>
      </article>`;
  }).join("");
}

function renderActivity(stays) {
  $("#active-stays").innerHTML = stays.map((stay) => `
    <article class="activity-item">
      <span class="activity-icon">${stay.matricula ? "🚘" : "↔"}</span>
      <div class="activity-copy">
        <strong>${escapeHtml(stay.matricula)} <span>· ${escapeHtml(stay.plaza)}</span></strong>
        <small>${escapeHtml(stay.cliente)} · ${escapeHtml(formatDate(stay.entrada))}</small>
      </div>
      <span class="activity-status" aria-label="Estancia activa"></span>
    </article>`).join("");
}

function render() {
  const { dashboard, clientes, vehiculos, plazas, operadores } = state;
  $("#stat-total").textContent = dashboard.plazas_total;
  $("#stat-available").textContent = dashboard.plazas_disponibles;
  $("#stat-occupied").textContent = dashboard.plazas_ocupadas;
  $("#stat-active").textContent = dashboard.estancias_activas.length;
  $("#active-count").textContent = `${dashboard.estancias_activas.length} activas`;

  renderStayRows(dashboard.estancias_activas, "#entry-stays");
  renderParkingLot(plazas, dashboard.estancias_activas);
  renderActivity(dashboard.estancias_activas);
  $("#empty-overview").hidden = plazas.length > 0;
  $("#empty-activity").hidden = dashboard.estancias_activas.length > 0;
  $("#empty-entries").hidden = dashboard.estancias_activas.length > 0;

  $("#client-count").textContent = `${clientes.length} ${clientes.length === 1 ? "cliente" : "clientes"}`;
  $("#clients-table").innerHTML = clientes.map((client) => `
    <tr><td>${escapeHtml(client.nombre)}</td><td>${escapeHtml(client.email || "—")}</td><td>#${client.id}</td></tr>`).join("");
  $("#empty-clients").hidden = clientes.length > 0;

  $("#vehicle-count").textContent = `${vehiculos.length} ${vehiculos.length === 1 ? "vehículo" : "vehículos"}`;
  $("#vehicles-table").innerHTML = vehiculos.map((vehicle) => `
    <tr><td><span class="vehicle-pill">${escapeHtml(vehicle.matricula)}</span></td><td>${escapeHtml(vehicle.cliente)}</td><td>#${vehicle.id}</td></tr>`).join("");
  $("#empty-vehicles").hidden = vehiculos.length > 0;

  $("#space-count").textContent = `${plazas.length} ${plazas.length === 1 ? "plaza" : "plazas"}`;
  $("#spaces-grid").innerHTML = plazas.map((space) => `
    <article class="space-card">
      <span class="space-symbol">▤</span>
      <div class="space-info"><strong>${escapeHtml(space.codigo)}</strong><small class="space-status ${space.ocupada ? "occupied" : ""}">${space.ocupada ? "Ocupada" : "Disponible"}</small></div>
      <div class="space-actions">
        <button class="icon-button" data-edit-space="${space.id}" aria-label="Editar plaza ${escapeHtml(space.codigo)}" title="Editar">✎</button>
        <button class="icon-button danger" data-delete-space="${space.id}" aria-label="Eliminar plaza ${escapeHtml(space.codigo)}" title="Eliminar">×</button>
      </div>
    </article>`).join("");
  $("#empty-spaces").hidden = plazas.length > 0;

  const vehicleSelect = $("#entry-vehicle");
  vehicleSelect.innerHTML = `<option value="">Selecciona una matrícula</option>${vehiculos.map((vehicle) =>
    `<option value="${vehicle.id}">${escapeHtml(vehicle.matricula)} · ${escapeHtml(vehicle.cliente)}</option>`).join("")}`;
  const availableSpaces = plazas.filter((space) => !space.ocupada);
  $("#entry-space").innerHTML = `<option value="">Selecciona una plaza</option>${availableSpaces.map((space) =>
    `<option value="${space.id}">${escapeHtml(space.codigo)}</option>`).join("")}`;
  $("#entry-operator").innerHTML = `<option value="">Selecciona un operador</option>${operadores.map((operator) =>
    `<option value="${operator.id}">${escapeHtml(operator.nombre)}</option>`).join("")}`;
  $("#vehicle-client").innerHTML = `<option value="">Selecciona un cliente</option>${clientes.map((client) =>
    `<option value="${client.id}">${escapeHtml(client.nombre)}</option>`).join("")}`;
}

async function loadAll() {
  const notice = $("#notice");
  notice.hidden = true;
  try {
    const [dashboard, clientes, vehiculos, plazas, operadores] = await Promise.all([
      api("/dashboard"), api("/clientes"), api("/vehiculos"), api("/plazas"), api("/operadores"),
    ]);
    Object.assign(state, { dashboard, clientes, vehiculos, plazas, operadores });
    render();
  } catch (error) {
    notice.textContent = `${error.message} Verifica que la base de datos esté inicializada y vuelve a cargar.`;
    notice.hidden = false;
  }
}

async function submitForm(form, path, successMessage, transform = (values) => values) {
  const values = Object.fromEntries(new FormData(form).entries());
  Object.keys(values).forEach((key) => {
    if (values[key] === "") delete values[key];
  });
  try {
    await api(path, { method: "POST", body: JSON.stringify(transform(values)) });
    form.reset();
    notify(successMessage);
    await loadAll();
  } catch (error) {
    notify(error.message, true);
  }
}

document.querySelectorAll("[data-view-target]").forEach((button) => {
  button.addEventListener("click", () => showView(button.dataset.viewTarget));
});

$("#entry-form").addEventListener("submit", (event) => {
  event.preventDefault();
  submitForm(event.currentTarget, "/estancias", "Entrada registrada.", (values) => ({
    vehiculo_id: Number(values.vehiculo_id),
    plaza_id: Number(values.plaza_id),
    usuario_id: Number(values.usuario_id),
  }));
});

$("#client-form").addEventListener("submit", (event) => {
  event.preventDefault();
  submitForm(event.currentTarget, "/clientes", "Cliente guardado.");
});

$("#vehicle-form").addEventListener("submit", (event) => {
  event.preventDefault();
  submitForm(event.currentTarget, "/vehiculos", "Vehículo guardado.", (values) => ({
    ...values,
    cliente_id: Number(values.cliente_id),
  }));
});

$("#add-operator").addEventListener("click", async () => {
  const input = $("#new-operator");
  if (!input.value.trim()) {
    notify("Escribe el nombre del operador.", true);
    input.focus();
    return;
  }
  try {
    const operator = await api("/operadores", { method: "POST", body: JSON.stringify({ nombre: input.value }) });
    input.value = "";
    await loadAll();
    $("#entry-operator").value = operator.id;
    notify("Operador agregado.");
  } catch (error) {
    notify(error.message, true);
  }
});

$("#space-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const editingId = state.editingSpaceId;
  const code = $("#space-code").value;
  try {
    await api(editingId ? `/plazas/${editingId}` : "/plazas", {
      method: editingId ? "PATCH" : "POST",
      body: JSON.stringify({ codigo: code }),
    });
    resetSpaceForm();
    notify(editingId ? "Plaza actualizada." : "Plaza agregada.");
    await loadAll();
  } catch (error) {
    notify(error.message, true);
  }
});

function resetSpaceForm() {
  state.editingSpaceId = null;
  $("#space-form").reset();
  $("#space-form-title").textContent = "Agregar una plaza";
  $("#space-submit").textContent = "＋ Agregar plaza";
  $("#space-cancel").hidden = true;
}

$("#space-cancel").addEventListener("click", resetSpaceForm);

document.body.addEventListener("click", async (event) => {
  const exitButton = event.target.closest("[data-exit-id]");
  if (exitButton) {
    exitButton.disabled = true;
    try {
      await api(`/estancias/${exitButton.dataset.exitId}/salida`, { method: "POST" });
      notify("Salida registrada. La plaza ya está disponible.");
      await loadAll();
    } catch (error) {
      notify(error.message, true);
      exitButton.disabled = false;
    }
    return;
  }

  const editButton = event.target.closest("[data-edit-space]");
  if (editButton) {
    const space = state.plazas.find((item) => item.id === Number(editButton.dataset.editSpace));
    if (!space) return;
    state.editingSpaceId = space.id;
    $("#space-code").value = space.codigo;
    $("#space-form-title").textContent = `Editar plaza ${space.codigo}`;
    $("#space-submit").textContent = "Guardar cambios";
    $("#space-cancel").hidden = false;
    $("#space-code").focus();
    return;
  }

  const deleteButton = event.target.closest("[data-delete-space]");
  if (deleteButton && window.confirm("¿Eliminar esta plaza? Las plazas con estancias registradas no se pueden eliminar.")) {
    try {
      await api(`/plazas/${deleteButton.dataset.deleteSpace}`, { method: "DELETE" });
      notify("Plaza eliminada.");
      await loadAll();
    } catch (error) {
      notify(error.message, true);
    }
  }
});

loadAll();

function updateDateTime() {
  const now = new Date();
  $("#current-datetime").textContent = new Intl.DateTimeFormat("es-CO", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(now);
}

updateDateTime();
setInterval(updateDateTime, 60_000);
