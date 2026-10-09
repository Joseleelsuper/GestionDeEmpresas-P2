const form = document.querySelector("#solve-form");
const exampleSelect = document.querySelector("#example-select");
const fileInput = document.querySelector("#instance-file");
const sequenceInput = document.querySelector("#sequence-input");
const searchAlgorithmInput = document.querySelector("#search-algorithm");
const searchMethodHelp = document.querySelector("#search-method-help");
const neighborhoodFields = document.querySelector("#neighborhood-fields");
const randomSearchFields = document.querySelector("#random-search-fields");
const annealingFields = document.querySelector("#annealing-fields");
const localSearchFields = document.querySelector("#local-search-fields");
const randomIterationsInput = document.querySelector("#random-iterations");
const initialTemperatureInput = document.querySelector("#initial-temperature");
const coolingRateInput = document.querySelector("#cooling-rate");
const iterationsPerTemperatureInput = document.querySelector("#iterations-per-temperature");
const finalTemperatureInput = document.querySelector("#final-temperature");
const annealingEstimate = document.querySelector("#annealing-estimate");
const refineWithLocalSearchInput = document.querySelector("#refine-with-local-search");
const maxIterationsInput = document.querySelector("#max-iterations");
const maxNeighborsInput = document.querySelector("#max-neighbors");
const calculateButton = document.querySelector("#calculate");
const searchButton = document.querySelector("#search-button");
const randomizeButton = document.querySelector("#randomize");
const statusElement = document.querySelector("#status");
const resultHeading = document.querySelector("#result-heading");
const sequenceResultBlock = document.querySelector("#sequence-result-block");
const sequenceDetails = document.querySelector("#sequence-details");
const sequenceDetailsSummary = document.querySelector("#sequence-details-summary");
const fullResultSequence = document.querySelector("#full-result-sequence");
const searchHistory = document.querySelector("#search-history");
const searchHistoryList = document.querySelector("#search-history-list");
const clearSearchHistory = document.querySelector("#clear-search-history");
const searchAnnouncement = document.querySelector("#search-announcement");
const results = document.querySelector("#results");
const numberFormat = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 2 });
const searchLabels = {
  method: {
    local_search: "Búsqueda local",
    random_search: "Búsqueda aleatoria",
    simulated_annealing: "Recocido simulado",
  },
  objective: { cmax: "Cmáx", fmax: "Fmáx" },
  strategy: {
    best: "Mejor vecino evaluado",
    first: "Primer vecino que mejora",
    random: "Aleatorio entre mejoras evaluadas",
  },
  neighborhood: { swap: "Intercambio", "2opt": "Inversión 2-opt" },
  stopReason: {
    local_optimum: "Óptimo local confirmado",
    sample_no_improvement: "Sin mejoras en la muestra",
    max_iterations: "Límite de iteraciones",
    iterations_complete: "Muestra aleatoria completada",
    final_temperature: "Temperatura final alcanzada",
    empty_neighborhood: "No hay movimientos posibles",
  },
};

const methodHelp = {
  local_search: "Mejora la secuencia indicada (o una aleatoria) mediante movimientos locales.",
  random_search: "Prueba permutaciones aleatorias y conserva la mejor encontrada; parte de la secuencia indicada si la hay.",
  simulated_annealing: "Explora vecinos y puede aceptar empeoramientos según la temperatura; devuelve la mejor solución visitada.",
};

function setSearchGroup(group, visible) {
  group.hidden = !visible;
  group.querySelectorAll("input, select").forEach((control) => {
    control.disabled = !visible;
  });
}

function annealingSchedule(initialTemperature, coolingRate, iterationsPerTemperature, finalTemperature) {
  let levels = 0;
  let temperature = initialTemperature;
  while (temperature >= finalTemperature) {
    levels += 1;
    if (levels * iterationsPerTemperature > 10000) return null;
    temperature *= coolingRate;
  }
  return { levels, evaluations: levels * iterationsPerTemperature };
}

function updateAnnealingEstimate() {
  const initialTemperature = Number(initialTemperatureInput.value);
  const coolingRate = Number(coolingRateInput.value);
  const iterationsPerTemperature = Number(iterationsPerTemperatureInput.value);
  const finalTemperature = Number(finalTemperatureInput.value);
  if (
    !Number.isFinite(initialTemperature) || initialTemperature <= 0
    || !Number.isFinite(coolingRate) || coolingRate <= 0 || coolingRate >= 1
    || !Number.isInteger(iterationsPerTemperature) || iterationsPerTemperature < 1
    || !Number.isFinite(finalTemperature) || finalTemperature <= 0
  ) {
    annealingEstimate.textContent = "Introduce temperaturas positivas, 0 < α < 1 y L(T) ≥ 1.";
  } else if (initialTemperature < finalTemperature) {
    annealingEstimate.textContent = "T₀ debe ser mayor o igual que Tf.";
  } else {
    const schedule = annealingSchedule(
      initialTemperature, coolingRate, iterationsPerTemperature, finalTemperature,
    );
    annealingEstimate.textContent = schedule
      ? `${schedule.levels} temperaturas · ${numberFormat.format(schedule.evaluations)} propuestas (máximo 10.000)`
      : "La combinación supera el máximo de 10.000 propuestas.";
  }
}

function updateSearchControls() {
  const method = searchAlgorithmInput.value;
  const isLocal = method === "local_search";
  const isRandom = method === "random_search";
  const isAnnealing = method === "simulated_annealing";
  setSearchGroup(neighborhoodFields, isLocal || isAnnealing);
  setSearchGroup(randomSearchFields, isRandom);
  setSearchGroup(annealingFields, isAnnealing);
  setSearchGroup(localSearchFields, isLocal || (isAnnealing && refineWithLocalSearchInput.checked));
  searchMethodHelp.textContent = methodHelp[method];
  updateAnnealingEstimate();
}

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

function renderSequence(sequence) {
  const fullSequence = sequence.join(", ");
  const isLong = sequence.length > 18;
  resultHeading.classList.toggle("has-long-sequence", isLong);
  sequenceResultBlock.classList.toggle("sequence-result--long", isLong);
  document.querySelector("#result-sequence").textContent = isLong
    ? `${sequence.slice(0, 12).join(", ")}, …`
    : fullSequence;
  sequenceDetails.hidden = !isLong;
  sequenceDetails.open = false;
  sequenceDetailsSummary.textContent = `Ver las ${sequence.length} órdenes`;
  fullResultSequence.textContent = fullSequence;
}

function createHistoryCard(result) {
  const { search } = result;
  const method = search.method || "local_search";
  const card = document.createElement("article");
  card.className = "history-card";
  card.setAttribute("role", "listitem");

  const heading = document.createElement("div");
  heading.className = "history-card-heading";
  const strategy = document.createElement("h4");
  strategy.textContent = `${searchLabels.method[method]}${search.refined_with_local_search ? " + búsqueda local" : ""}`;
  const context = document.createElement("p");
  context.className = "history-card-context";
  const contextParts = [];
  if (method === "local_search") contextParts.push(searchLabels.strategy[search.strategy]);
  if (search.neighborhood) contextParts.push(searchLabels.neighborhood[search.neighborhood]);
  contextParts.push(`objetivo ${searchLabels.objective[search.objective]}`);
  if (method === "random_search") {
    contextParts.push(`${numberFormat.format(search.iterations)} muestras aleatorias`);
  }
  if (method === "simulated_annealing") {
    contextParts.push(
      `${numberFormat.format(search.temperature_levels)} temperaturas · T₀ ${numberFormat.format(search.initial_temperature)} · α ${numberFormat.format(search.cooling_rate)} · L ${search.iterations_per_temperature} · Tf ${numberFormat.format(search.final_temperature)}`,
    );
  }
  if (search.refinement) {
    contextParts.push(
      `refinamiento: ${searchLabels.strategy[search.refinement.strategy]} · ${numberFormat.format(search.refinement.iterations)} iteraciones · ${numberFormat.format(search.refinement.neighbors_evaluated)} vecinos`,
    );
  }
  contextParts.push(`${result.jobs} órdenes · ${result.machines} máquinas`);
  context.textContent = contextParts.join(" · ");
  heading.append(strategy, context);

  const measures = document.createElement("div");
  measures.className = "history-measures";
  for (const [key, label] of [["cmax", "Cmáx"], ["fmax", "Fmáx"]]) {
    const measure = document.createElement("div");
    measure.className = "history-measure";
    if (search.objective === key) measure.classList.add("history-measure--objective");
    const name = document.createElement("span");
    name.textContent = label;
    const value = document.createElement("strong");
    value.textContent = `${numberFormat.format(search.initial_metrics[key])} → ${numberFormat.format(search.final_metrics[key])}`;
    measure.append(name, value);
    measures.append(measure);
  }

  const stats = document.createElement("div");
  stats.className = "history-stats";
  const secondStat = method === "simulated_annealing"
    ? ["cycle", numberFormat.format(search.temperature_levels), "temperaturas"]
    : ["cycle", `${search.iterations}/${search.max_iterations}`, "iteraciones"];
  for (const [iconName, value, label] of [
    ["home", numberFormat.format(search.evaluations ?? search.neighbors_evaluated), search.evaluation_label ?? "vecinos"],
    secondStat,
  ]) {
    const stat = document.createElement("div");
    stat.className = "history-stat";
    const icon = document.createElement("span");
    icon.className = "material-symbols-outlined history-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = iconName;
    const copy = document.createElement("span");
    copy.className = "history-stat-copy";
    const statValue = document.createElement("strong");
    statValue.textContent = value;
    const statLabel = document.createElement("small");
    statLabel.textContent = label;
    copy.append(statValue, statLabel);
    stat.append(icon, copy);
    stats.append(stat);
  }

  const stop = document.createElement("p");
  stop.className = "history-stop";
  const stopMessages = [searchLabels.stopReason[search.stop_reason]];
  if (search.refinement) {
    stopMessages.push(`Refinamiento: ${searchLabels.stopReason[search.refinement.stop_reason]}`);
  }
  stop.textContent = stopMessages.filter(Boolean).join(" · ");

  const sequenceDetails = document.createElement("details");
  sequenceDetails.className = "history-sequence";
  const sequenceSummary = document.createElement("summary");
  sequenceSummary.textContent = "Ver secuencia resultante";
  const sequenceText = document.createElement("p");
  sequenceText.textContent = result.sequence.join(", ");
  sequenceDetails.append(sequenceSummary, sequenceText);

  card.append(heading, measures, stats, stop, sequenceDetails);
  return card;
}

function readIntegerInput(input, minimum, maximum, errorMessage) {
  const rawValue = input.value.trim();
  const value = Number(rawValue);
  if (!rawValue || !Number.isInteger(value) || value < minimum || value > maximum) {
    setStatus(errorMessage, true);
    input.focus();
    return null;
  }
  return value;
}

function readPositiveInput(input, errorMessage) {
  const rawValue = input.value.trim();
  const value = Number(rawValue);
  if (!rawValue || !Number.isFinite(value) || value <= 0) {
    setStatus(errorMessage, true);
    input.focus();
    return null;
  }
  return value;
}

function readLocalSearchParameters(data) {
  const iterations = readIntegerInput(
    maxIterationsInput, 1, 1000, "Las iteraciones locales deben ser un entero entre 1 y 1000.",
  );
  if (iterations === null) return false;
  const neighbors = readIntegerInput(
    maxNeighborsInput, 0, 1000, "Los vecinos por iteración deben ser un entero entre 0 y 1000.",
  );
  if (neighbors === null) return false;
  data.set("max_iterations", String(iterations));
  data.set("max_neighbors", String(neighbors));
  return true;
}

function addSearchToHistory(result) {
  const card = createHistoryCard(result);
  searchHistory.hidden = false;
  const previousCards = [...searchHistoryList.children];
  const previousPositions = new Map(
    previousCards.map((previous) => [previous, previous.getBoundingClientRect().left]),
  );
  searchHistoryList.prepend(card);
  searchHistoryList.scrollLeft = 0;

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!reduceMotion && typeof card.animate === "function") {
    for (const previous of previousCards) {
      const offset = previousPositions.get(previous) - previous.getBoundingClientRect().left;
      if (Math.abs(offset) > 1) {
        previous.animate(
          [{ transform: `translateX(${offset}px)` }, { transform: "translateX(0)" }],
          { duration: 360, easing: "cubic-bezier(0.22, 1, 0.36, 1)" },
        );
      }
    }
    card.animate(
      [{ opacity: 0, transform: "translateY(18px)" }, { opacity: 1, transform: "translateY(0)" }],
      { duration: 420, easing: "cubic-bezier(0.22, 1, 0.36, 1)" },
    );
  }
  searchAnnouncement.textContent = `Búsqueda añadida al historial: ${searchLabels.objective[result.search.objective]} ${numberFormat.format(result.search.initial_value)} a ${numberFormat.format(result.search.final_value)}.`;
}

exampleSelect.addEventListener("change", () => {
  if (exampleSelect.value) fileInput.value = "";
});

fileInput.addEventListener("change", () => {
  if (fileInput.files.length) exampleSelect.value = "";
});

randomizeButton.addEventListener("click", () => {
  sequenceInput.value = "";
  calculateButton.click();
});

clearSearchHistory.addEventListener("click", () => {
  searchHistoryList.replaceChildren();
  searchHistory.hidden = true;
  searchAnnouncement.textContent = "Historial de búsquedas limpio.";
});

searchAlgorithmInput.addEventListener("change", updateSearchControls);
refineWithLocalSearchInput.addEventListener("change", updateSearchControls);
for (const input of [initialTemperatureInput, coolingRateInput, iterationsPerTemperatureInput, finalTemperatureInput]) {
  input.addEventListener("input", updateAnnealingEstimate);
}
updateSearchControls();

for (const input of [
  maxIterationsInput,
  maxNeighborsInput,
  randomIterationsInput,
  initialTemperatureInput,
  coolingRateInput,
  iterationsPerTemperatureInput,
  finalTemperatureInput,
]) {
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      form.requestSubmit(searchButton);
    }
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!fileInput.files.length && !exampleSelect.value) {
    setStatus("Elige un ejemplo o carga un archivo TXT.", true);
    return;
  }

  const data = new FormData(form);
  if (fileInput.files.length) data.delete("example");
  else data.delete("file");
  const algorithm = event.submitter === calculateButton ? "calculate" : searchAlgorithmInput.value;
  data.set("algorithm", algorithm);
  const refinesAnnealing = algorithm === "simulated_annealing" && refineWithLocalSearchInput.checked;
  if ((algorithm === "local_search" || refinesAnnealing) && !readLocalSearchParameters(data)) return;
  if (algorithm === "random_search") {
    const iterations = readIntegerInput(
      randomIterationsInput, 1, 10000, "Las iteraciones aleatorias deben ser un entero entre 1 y 10000.",
    );
    if (iterations === null) return;
    data.set("random_iterations", String(iterations));
  }
  if (algorithm === "simulated_annealing") {
    const initialTemperature = readPositiveInput(
      initialTemperatureInput, "T₀ debe ser un número positivo y finito.",
    );
    if (initialTemperature === null) return;
    const coolingRate = Number(coolingRateInput.value);
    if (!Number.isFinite(coolingRate) || coolingRate <= 0 || coolingRate >= 1) {
      setStatus("α debe ser un número mayor que 0 y menor que 1.", true);
      coolingRateInput.focus();
      return;
    }
    const iterationsPerTemperature = readIntegerInput(
      iterationsPerTemperatureInput, 1, 10000, "L(T) debe ser un entero entre 1 y 10000.",
    );
    if (iterationsPerTemperature === null) return;
    const finalTemperature = readPositiveInput(
      finalTemperatureInput, "Tf debe ser un número positivo y finito.",
    );
    if (finalTemperature === null) return;
    if (initialTemperature < finalTemperature) {
      setStatus("T₀ debe ser mayor o igual que Tf.", true);
      initialTemperatureInput.focus();
      return;
    }
    const schedule = annealingSchedule(
      initialTemperature, coolingRate, iterationsPerTemperature, finalTemperature,
    );
    if (!schedule) {
      setStatus("La combinación supera el máximo de 10000 propuestas; ajusta α, L(T) o Tf.", true);
      coolingRateInput.focus();
      return;
    }
    data.set("initial_temperature", String(initialTemperature));
    data.set("cooling_rate", String(coolingRate));
    data.set("iterations_per_temperature", String(iterationsPerTemperature));
    data.set("final_temperature", String(finalTemperature));
    data.set("refine_with_local_search", String(refineWithLocalSearchInput.checked));
  }
  calculateButton.disabled = true;
  searchButton.disabled = true;
  randomizeButton.disabled = true;
  const progressMessages = {
    calculate: "Calculando la matriz…",
    local_search: "Buscando una secuencia mejor…",
    random_search: "Evaluando permutaciones aleatorias…",
    simulated_annealing: "Ejecutando recocido simulado…",
  };
  setStatus(progressMessages[algorithm]);
  try {
    const response = await fetch("/api/solve", { method: "POST", body: data });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "No se pudo calcular la instancia.");

    document.querySelector("#result-source").textContent = `${result.jobs} órdenes · ${result.machines} máquinas`;
    document.querySelector("#metric-cmax").textContent = result.cmax;
    document.querySelector("#metric-fmax").textContent = result.fmax;
    if (result.search) {
      addSearchToHistory(result);
    }
    renderSequence(result.sequence);
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
