const form = document.querySelector("#solve-form");
const exampleSelect = document.querySelector("#example-select");
const fileInput = document.querySelector("#instance-file");
const sequenceInput = document.querySelector("#sequence-input");
const maxIterationsInput = document.querySelector("#max-iterations");
const calculateButton = document.querySelector("#calculate");
const searchButton = document.querySelector("#search-button");
const randomizeButton = document.querySelector("#randomize");
const statusElement = document.querySelector("#status");
const searchSummary = document.querySelector("#search-summary");
const results = document.querySelector("#results");
const numberFormat = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 2 });
const searchNumberFormat = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 4 });
const searchLabels = {
  objective: { cmax: "Cmáx", fmax: "Fmáx" },
  strategy: { best: "Mejor vecino", first: "Primer vecino que mejora", random: "Vecino aleatorio" },
  neighborhood: { swap: "Intercambio", "2opt": "Inversión 2-opt" },
  stopReason: { local_optimum: "no hay vecinos mejores", max_iterations: "límite de iteraciones" },
};

async function loadExamples() {
  try {
    const response = await fetch("/api/examples");
    if (!response.ok) throw new Error("No se pudieron cargar los ejemplos.");
    const examples = await response.json();
    exampleSelect.replaceChildren();
    for (const name of examples) {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      exampleSelect.append(option);
    }
    if (!examples.length) throw new Error("No hay archivos TXT en data/examples.");
  } catch (error) {
    setStatus(error.message, true);
  }
}

function setStatus(message, isError = false) {
  statusElement.textContent = message;
  statusElement.classList.toggle("status-error", isError);
  statusElement.hidden = !message;
}

function renderTable(container, rows, key, machines) {
  const table = document.createElement("table");
  const caption = document.createElement("caption");
  caption.className = "visually-hidden";
  caption.textContent = key === "completion" ? "Tiempos de finalización por orden y máquina" : "Duraciones originales por orden y máquina";
  table.append(caption);

  const head = table.createTHead().insertRow();
  const orderHeader = document.createElement("th");
  orderHeader.scope = "col";
  orderHeader.textContent = "Orden";
  head.append(orderHeader);
  for (let machine = 1; machine <= machines; machine += 1) {
    const header = document.createElement("th");
    header.scope = "col";
    header.textContent = `M${machine}`;
    head.append(header);
  }

  const body = table.createTBody();
  for (const row of rows) {
    const cells = body.insertRow();
    const order = document.createElement("th");
    order.scope = "row";
    order.textContent = `Orden ${row.job}`;
    cells.append(order);
    for (const value of row[key]) {
      const cell = cells.insertCell();
      cell.textContent = value;
    }
  }
  container.replaceChildren(table);
}

exampleSelect.addEventListener("change", () => {
  if (exampleSelect.value) fileInput.value = "";
});

fileInput.addEventListener("change", () => {
  if (fileInput.files.length) exampleSelect.value = "";
});

randomizeButton.addEventListener("click", () => {
  sequenceInput.value = "";
  form.requestSubmit();
});

maxIterationsInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    form.requestSubmit(searchButton);
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!fileInput.files.length && !exampleSelect.value) {
    setStatus("Elige un ejemplo o carga un archivo TXT.", true);
    return;
  }

  const data = new FormData(form);
  if (fileInput.files.length) data.delete("example");
  else data.delete("file");
  const algorithm = event.submitter?.value || "calculate";
  data.set("algorithm", algorithm);
  if (algorithm === "local_search") {
    const iterations = Number(maxIterationsInput.value);
    if (!Number.isInteger(iterations) || iterations < 1 || iterations > 1000) {
      setStatus("El máximo de iteraciones debe ser un entero entre 1 y 1000.", true);
      maxIterationsInput.focus();
      return;
    }
    data.set("max_iterations", String(iterations));
  } else {
    data.set("max_iterations", "100");
  }
  searchSummary.hidden = true;

  calculateButton.disabled = true;
  searchButton.disabled = true;
  randomizeButton.disabled = true;
  setStatus(algorithm === "local_search" ? "Buscando una secuencia mejor…" : "Calculando la matriz…");
  try {
    const response = await fetch("/api/solve", { method: "POST", body: data });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "No se pudo calcular la instancia.");

    document.querySelector("#result-source").textContent = `${result.source} · ${result.jobs} órdenes · ${result.machines} máquinas`;
    document.querySelector("#result-sequence").textContent = result.sequence.join(", ");
    document.querySelector("#metric-cmax").textContent = result.cmax;
    document.querySelector("#metric-fmax").textContent = result.fmax;
    if (result.search) {
      const search = result.search;
      const valueLabel = searchLabels.objective[search.objective];
      searchSummary.textContent = `Búsqueda local · ${searchLabels.strategy[search.strategy]} · ${searchLabels.neighborhood[search.neighborhood]} · ${valueLabel}: ${searchNumberFormat.format(search.initial_value)} → ${searchNumberFormat.format(search.final_value)} · ${search.iterations}/${search.max_iterations} iteraciones · parada: ${searchLabels.stopReason[search.stop_reason]}.`;
      searchSummary.hidden = false;
    }
    const orderedRows = [...result.rows].sort((first, second) => first.job - second.job);
    renderTable(document.querySelector("#completion-table"), orderedRows, "completion", result.machines);
    renderTable(document.querySelector("#processing-table"), orderedRows, "processing", result.machines);
    sequenceInput.value = result.sequence.join(", ");
    results.hidden = false;
    setStatus("");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    calculateButton.disabled = false;
    searchButton.disabled = false;
    randomizeButton.disabled = false;
  }
});

loadExamples();
