const form = document.querySelector("#solve-form");
const exampleSelect = document.querySelector("#example-select");
const fileInput = document.querySelector("#instance-file");
const sequenceInput = document.querySelector("#sequence-input");
const calculateButton = document.querySelector("#calculate");
const randomizeButton = document.querySelector("#randomize");
const statusElement = document.querySelector("#status");
const results = document.querySelector("#results");
const emptyState = document.querySelector("#empty-state");
const numberFormat = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 2 });

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
  statusElement.hidden = !isError || !message;
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

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!fileInput.files.length && !exampleSelect.value) {
    setStatus("Elige un ejemplo o carga un archivo TXT.", true);
    return;
  }

  const data = new FormData(form);
  if (fileInput.files.length) data.delete("example");
  else data.delete("file");

  calculateButton.disabled = true;
  randomizeButton.disabled = true;
  setStatus("Calculando la matriz…");
  try {
    const response = await fetch("/api/solve", { method: "POST", body: data });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "No se pudo calcular la instancia.");

    document.querySelector("#result-source").textContent = `${result.source} · ${result.jobs} órdenes · ${result.machines} máquinas`;
    document.querySelector("#result-sequence").textContent = result.sequence.join(", ");
    document.querySelector("#metric-cmax").textContent = result.cmax;
    document.querySelector("#metric-fmax").textContent = result.fmax;
    renderTable(document.querySelector("#completion-table"), result.rows, "completion", result.machines);
    const originalRows = [...result.rows].sort((first, second) => first.job - second.job);
    renderTable(document.querySelector("#processing-table"), originalRows, "processing", result.machines);
    sequenceInput.value = result.sequence.join(", ");
    emptyState.hidden = true;
    results.hidden = false;
    setStatus("");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    calculateButton.disabled = false;
    randomizeButton.disabled = false;
  }
});

loadExamples();
