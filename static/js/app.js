let currentPage = 1;
let pageSize = 25;
let activeStatus = "TODOS";
let searchTerm = "";
let dadosAuditoria = null;
let sortState = { field: "data", direction: "asc" };
let searchTimer = null;

const el = (id) => document.getElementById(id);
const mojibakeMarkers = ["Ã", "Â", "â€", "â€“", "â€”", "â€¦", "â€¢", "â„¢", "ðŸ", "ƒ", "Š", "‡", "œ", "�"];

function mojibakeScore(text) {
  return mojibakeMarkers.reduce((total, marker) => total + String(text).split(marker).length - 1, 0);
}

function decodeMojibakeRun(text) {
  let best = text;
  let bestScore = mojibakeScore(text);
  let queue = [text];
  const seen = new Set(queue);

  for (let depth = 0; depth < 4; depth += 1) {
    const next = [];
    for (const item of queue) {
      const bytes = Uint8Array.from(Array.from(item, (char) => char.charCodeAt(0) & 0xff));
      let candidate;
      try {
        candidate = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
      } catch {
        continue;
      }
      if (seen.has(candidate)) continue;
      seen.add(candidate);
      const score = mojibakeScore(candidate);
      if (score < bestScore) {
        best = candidate;
        bestScore = score;
      }
      next.push(candidate);
    }
    queue = next;
    if (!queue.length) break;
  }

  return best;
}

function fixMojibake(value) {
  if (typeof value !== "string") return value;
  if (!mojibakeMarkers.some((marker) => value.includes(marker))) return value;
  return value.replace(/[\u0080-\u00ff\u0152\u0153\u0160\u0161\u0178\u0192\u02c6\u02dc\u2013\u2014\u2018\u2019\u201a\u201c\u201d\u201e\u2020\u2021\u2022\u2026\u2030\u2039\u203a\u20ac]+/g, (part) => decodeMojibakeRun(part));
}

function cleanTextDeep(value) {
  if (typeof value === "string") return fixMojibake(value);
  if (Array.isArray(value)) return value.map(cleanTextDeep);
  if (value && typeof value === "object") {
    Object.keys(value).forEach((key) => {
      value[key] = cleanTextDeep(value[key]);
    });
  }
  return value;
}

document.addEventListener("DOMContentLoaded", () => {
  el("pdf_ponto").addEventListener("change", () => updateFilePill("pdf"));
  el("excel_refeicoes").addEventListener("change", () => updateFilePill("xls"));
  el("btn-analisar").addEventListener("click", analisar);
  el("btn-export").addEventListener("click", toggleExportMenu);
  el("btn-export-excel").addEventListener("click", exportar);
  el("btn-export-pdf").addEventListener("click", exportarPdf);
  el("page-size").addEventListener("change", (event) => {
    pageSize = Number(event.target.value);
    currentPage = 1;
    renderTabela();
  });

  el("search-input").addEventListener("input", (event) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      searchTerm = normalizeText(event.target.value);
      currentPage = 1;
      renderTabela();
    }, 250);
  });

  document.querySelectorAll(".filter-chip").forEach((button) => {
    button.addEventListener("click", () => {
      activeStatus = button.dataset.status;
      currentPage = 1;
      document.querySelectorAll(".filter-chip").forEach((b) => b.classList.remove("active"));
      button.classList.add("active");
      renderTabela();
    });
  });

  document.querySelectorAll(".audit-table th.sortable").forEach((th) => {
    th.addEventListener("click", () => ordenarPor(th.dataset.sort));
  });

  el("tabela-body").addEventListener("input", atualizarOcorrenciaEditavel);
  el("tabela-body").addEventListener("change", atualizarOcorrenciaEditavel);
  el("tabela-body").addEventListener("click", aprovarOcorrenciaManual);

  document.querySelectorAll(".file-remove").forEach((button) => {
    button.addEventListener("click", () => clearFile(button.dataset.target));
  });

  setupDropZone("pdf");
  setupDropZone("xls");

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".export-menu")) {
      el("export-options").classList.remove("open");
    }
  });
});

function setupDropZone(tipo) {
  const zone = el(tipo === "pdf" ? "drop-pdf" : "drop-xls");
  const input = el(tipo === "pdf" ? "pdf_ponto" : "excel_refeicoes");

  zone.addEventListener("dragover", (event) => {
    event.preventDefault();
    zone.classList.add("dragging");
  });

  zone.addEventListener("dragleave", () => zone.classList.remove("dragging"));
  zone.addEventListener("drop", (event) => {
    event.preventDefault();
    zone.classList.remove("dragging");
    input.files = event.dataTransfer.files;
    updateFilePill(tipo);
  });
}

function updateFilePill(tipo) {
  const input = tipo === "pdf" ? el("pdf_ponto") : el("excel_refeicoes");
  const files = Array.from(input.files || []);
  const pill = el(`${tipo}-file-pill`);
  const name = el(`nome-${tipo}`);
  const size = el(`size-${tipo}`);

  if (!files.length) {
    pill.classList.remove("visible");
    name.textContent = "";
    size.textContent = "";
    return;
  }

  name.textContent = files.length > 1 ? `${files.length} arquivos selecionados` : files[0].name;
  size.textContent = files.length > 1
    ? `${files.length} PDFs · ${formatFileSize(files.reduce((total, file) => total + file.size, 0))}`
    : formatFileSize(files[0].size);
  pill.classList.add("visible");
}

function clearFile(tipo) {
  const input = tipo === "pdf" ? el("pdf_ponto") : el("excel_refeicoes");
  input.value = "";
  updateFilePill(tipo);
}

function formatFileSize(bytes) {
  if (!bytes) return "";
  const mb = bytes / 1024 / 1024;
  if (mb >= 1) return `${mb.toFixed(2).replace(".", ",")} MB`;
  return `${(bytes / 1024).toFixed(0)} KB`;
}

async function analisar() {
  const pdfInput = el("pdf_ponto");
  const excelInput = el("excel_refeicoes");

  if (!pdfInput.files[0]) {
    mostrarErro("Selecione o PDF do cartão de ponto.");
    return;
  }

  if (!excelInput.files[0]) {
    mostrarErro("Selecione a planilha de refeições.");
    return;
  }

  limparErro();
  el("loader").style.display = "block";
  el("btn-analisar").disabled = true;

  const form = new FormData();
  Array.from(pdfInput.files).forEach((file) => form.append("pdf_ponto", file));
  form.append("excel_refeicoes", excelInput.files[0]);

  try {
    const resp = await fetch("/api/analisar", { method: "POST", body: form });
    const data = cleanTextDeep(await resp.json());

    if (!resp.ok || data.erro) {
      mostrarErro(data.erro || "Erro desconhecido.");
      return;
    }

    dadosAuditoria = cleanTextDeep(data);
    prepararOcorrenciasEditaveis(dadosAuditoria.ocorrencias);
    renderizar(data);
  } catch (error) {
    mostrarErro(`Falha na comunicação com o servidor: ${error.message}`);
  } finally {
    el("loader").style.display = "none";
    el("btn-analisar").disabled = false;
  }
}

function renderizar(data) {
  const { funcionario, resumo } = data;
  activeStatus = "TODOS";
  searchTerm = "";
  currentPage = 1;
  sortState = { field: "data", direction: "asc" };
  el("search-input").value = "";
  document.querySelectorAll(".filter-chip").forEach((b) => b.classList.remove("active"));
  document.querySelector('.filter-chip[data-status="TODOS"]').classList.add("active");

  el("main-title").textContent = funcionario?.nome || "Todos os colaboradores";
  el("meta-matricula").textContent = funcionario?.matricula || "Todos";
  el("meta-periodo").textContent = data.periodo_excel
    ? `${data.periodo_excel.inicio || "—"} a ${data.periodo_excel.fim || "—"}`
    : `${funcionario?.periodo_inicio || "—"} a ${funcionario?.periodo_fim || "—"}`;
  el("periodo-planilha").textContent = data.periodo_excel
    ? `${data.periodo_excel.inicio || "—"} a ${data.periodo_excel.fim || "—"}`
    : "—";
  el("total-colaboradores").textContent = countColaboradores(data.ocorrencias);
  el("ultima-auditoria").textContent = new Date().toLocaleString("pt-BR");

  updateKpis(resumo || {});
  renderTabela();
}

function countColaboradores(ocorrencias = []) {
  return new Set(ocorrencias.map((o) => o.matricula).filter(Boolean)).size || "—";
}

function prepararOcorrenciasEditaveis(ocorrencias = []) {
  ocorrencias.forEach((o, index) => {
    cleanTextDeep(o);
    o._row_id = o._row_id || `oc-${index}-${Date.now()}`;
    o.descricao = fixMojibake(o.descricao || o.motivo || "");
    o.motivo = o.descricao;
    o.acao_recomendada = fixMojibake(o.acao_recomendada || "");
  });
}

function updateKpis(resumo) {
  const total = resumo.total_refeicoes ?? resumo.total ?? 0;
  const ok = resumo.ok || 0;
  const glosas = resumo.glosas || 0;
  const revisoes = (resumo.excecoes || 0) + (resumo.alertas || 0) + (resumo.pendentes || 0) + (resumo.divergencias || 0);

  el("kpi-total").textContent = total;
  el("kpi-ok").textContent = ok;
  el("kpi-glosa").textContent = glosas;
  el("kpi-revisao").textContent = revisoes;

  const pct = (value) => total ? `${((value / total) * 100).toFixed(2).replace(".", ",")}% do total` : "0% do total";
  el("kpi-total-pct").textContent = total ? "100% do total" : "0% do total";
  el("kpi-ok-pct").textContent = pct(ok);
  el("kpi-glosa-pct").textContent = pct(glosas);
  el("kpi-revisao-pct").textContent = pct(revisoes);
}

function recalcularResumoLocal() {
  if (!dadosAuditoria) return;

  const ocorrencias = dadosAuditoria.ocorrencias || [];
  const resumo = dadosAuditoria.resumo || {};
  const refeicoes = ocorrencias.filter((o) => o.origem === "REFEIÇÕES");
  const somarQtd = (status) => refeicoes
    .filter((o) => normalizeText(o.status) === normalizeText(status))
    .reduce((soma, o) => soma + Number(o.quantidade || 1), 0);
  resumo.total = ocorrencias.length;
  resumo.total_refeicoes = refeicoes.reduce((soma, o) => soma + Number(o.quantidade || 1), 0);
  resumo.ok = somarQtd("OK");
  resumo.glosas = somarQtd("GLOSA");
  resumo.excecoes = somarQtd("EXCEÇÃO");
  resumo.alertas = ocorrencias.filter((o) => o.status === "ALERTA").length;
  resumo.pendentes = ocorrencias.filter((o) => o.status === "PENDENTE").length;
  resumo.divergencias = ocorrencias.filter((o) => normalizeText(o.status) === "DIVERGENCIA").length;
  resumo.sem_cartao = ocorrencias.filter((o) => normalizeText(o.motivo).includes("NAO POSSUI CARTAO DE PONTO")).length;
  dadosAuditoria.resumo = resumo;
  recalcularFinanceiroLocal();
  updateKpis(resumo);
}

function recalcularFinanceiroLocal() {
  const financeiro = dadosAuditoria?.financeiro;
  if (!financeiro) return;

  const ocorrencias = dadosAuditoria?.ocorrencias || [];
  const totalProvisionado = Number(financeiro.total_provisionado || financeiro.total_provisionado_calculado || 0);
  const valorUnitarioPadrao = Number(financeiro.valor_unitario || 0);

  const glosaRecomendada = ocorrencias
    .filter((o) => o.status === "GLOSA")
    .reduce((soma, o) => {
      const valorLancamento = Number(o.valor_total_refeicao);
      if (Number.isFinite(valorLancamento) && valorLancamento > 0) {
        return soma + valorLancamento;
      }
      return soma + (Number(o.quantidade || 1) * valorUnitarioPadrao);
    }, 0);

  const totalConforme = Math.max(totalProvisionado - glosaRecomendada, 0);
  financeiro.total_conforme = totalConforme;
  financeiro.glosa_recomendada = glosaRecomendada;
  financeiro.divergencia = glosaRecomendada;
}

function renderTabela() {
  const ocorrencias = dadosAuditoria?.ocorrencias || [];
  let rows = activeStatus === "TODOS"
    ? [...ocorrencias]
    : ocorrencias.filter((o) => normalizeText(o.status) === normalizeText(activeStatus));

  if (searchTerm) {
    rows = rows.filter((o) => searchableText(o).includes(searchTerm));
  }

  rows.sort((a, b) => compararOcorrencias(a, b));
  updateSortMarks();

  const totalRows = rows.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / pageSize));
  currentPage = Math.min(currentPage, totalPages);
  const start = (currentPage - 1) * pageSize;
  const pageRows = rows.slice(start, start + pageSize);

  el("tabela-body").innerHTML = pageRows.map(renderRow).join("");
  el("no-data").style.display = pageRows.length ? "none" : "block";
  updateTableFooter(totalRows, start, pageRows.length, totalPages);
}

function renderRow(o) {
  const acao = o.acao_recomendada || "Nenhuma ação";
  const actionClass = getActionClass(acao);
  const podeAprovar = o.status === "GLOSA";

  return `
    <tr data-row-id="${escapeHtml(o._row_id)}">
      <td>${escapeHtml(o.matricula)}</td>
      <td>${escapeHtml(o.nome)}</td>
      <td>${escapeHtml(o.data || o.dia)}</td>
      <td>${escapeHtml(o.dia_semana)}</td>
      <td>${escapeHtml(o.tipo_refeicao)}</td>
      <td>
        ${badgeHtml(o.status)}
        ${podeAprovar ? `<button type="button" class="approve-btn" data-action="aprovar" title="Aprovar esta glosa como exceção">Aprovar</button>` : ""}
      </td>
      <td class="desc-cell">
        <textarea class="inline-edit desc-edit" data-field="descricao" rows="2">${escapeHtml(o.descricao || o.motivo)}</textarea>
      </td>
      <td class="action-cell ${actionClass}">
        <textarea class="inline-edit action-edit" data-field="acao_recomendada" rows="2">${escapeHtml(acao)}</textarea>
      </td>
    </tr>
  `;
}

function encontrarOcorrenciaPorLinha(target) {
  const row = target.closest("tr[data-row-id]");
  if (!row || !dadosAuditoria) return null;
  return (dadosAuditoria.ocorrencias || []).find((o) => o._row_id === row.dataset.rowId) || null;
}

function atualizarOcorrenciaEditavel(event) {
  const field = event.target.dataset.field;
  if (!field) return;

  const ocorrencia = encontrarOcorrenciaPorLinha(event.target);
  if (!ocorrencia) return;

  ocorrencia[field] = event.target.value;
  if (field === "descricao") {
    ocorrencia.motivo = event.target.value;
  }
  if (field === "acao_recomendada") {
    const cell = event.target.closest("td");
    cell?.classList.remove("action-ok", "action-danger", "action-info", "action-warn");
    cell?.classList.add(getActionClass(event.target.value));
  }
}

function aprovarOcorrenciaManual(event) {
  const button = event.target.closest("[data-action='aprovar']");
  if (!button) return;

  const ocorrencia = encontrarOcorrenciaPorLinha(button);
  if (!ocorrencia) return;

  ocorrencia.status = "EXCEÇÃO";
  ocorrencia.acao_recomendada = "Nenhuma ação";
  ocorrencia.aprovado_manual = true;
  ocorrencia.autorizacao_status = ocorrencia.autorizacao_status || "APROVADO_MANUAL";

  if (!normalizeText(ocorrencia.descricao || ocorrencia.motivo).includes("APROVADO MANUALMENTE")) {
    const descricaoAtual = ocorrencia.descricao || ocorrencia.motivo || "";
    ocorrencia.descricao = `${descricaoAtual}${descricaoAtual ? " | " : ""}Aprovado manualmente na auditoria.`;
    ocorrencia.motivo = ocorrencia.descricao;
  }

  recalcularResumoLocal();
  renderTabela();
}

function updateTableFooter(totalRows, start, count, totalPages) {
  const from = totalRows ? start + 1 : 0;
  const to = totalRows ? start + count : 0;
  el("table-info").textContent = `Mostrando ${from}-${to} de ${totalRows} registros`;

  const pagination = el("pagination");
  pagination.innerHTML = "";

  const prev = document.createElement("button");
  prev.type = "button";
  prev.textContent = "‹";
  prev.disabled = currentPage === 1;
  prev.addEventListener("click", () => {
    currentPage -= 1;
    renderTabela();
  });
  pagination.appendChild(prev);

  const pages = paginationPages(totalPages);
  pages.forEach((page) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = page;
    button.classList.toggle("active", page === currentPage);
    button.addEventListener("click", () => {
      currentPage = page;
      renderTabela();
    });
    pagination.appendChild(button);
  });

  const next = document.createElement("button");
  next.type = "button";
  next.textContent = "›";
  next.disabled = currentPage === totalPages;
  next.addEventListener("click", () => {
    currentPage += 1;
    renderTabela();
  });
  pagination.appendChild(next);
}

function paginationPages(totalPages) {
  const pages = [];
  const start = Math.max(1, currentPage - 2);
  const end = Math.min(totalPages, start + 4);
  for (let page = start; page <= end; page += 1) pages.push(page);
  return pages;
}

function ordenarPor(field) {
  if (sortState.field === field) {
    sortState.direction = sortState.direction === "asc" ? "desc" : "asc";
  } else {
    sortState = { field, direction: "asc" };
  }
  renderTabela();
}

function compararOcorrencias(a, b) {
  const va = sortValue(a, sortState.field);
  const vb = sortValue(b, sortState.field);
  let result;

  if (typeof va === "number" && typeof vb === "number") {
    result = va - vb;
  } else {
    result = String(va).localeCompare(String(vb), "pt-BR", { numeric: true });
  }

  return sortState.direction === "asc" ? result : -result;
}

function sortValue(o, field) {
  if (field === "data") return dateOrder(o.data || o.dia);
  if (field === "descricao") return normalizeText(o.descricao || o.motivo);
  if (field === "matricula") return Number(o.matricula) || 0;
  return normalizeText(o[field]);
}

function dateOrder(value) {
  const match = String(value || "").match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (!match) return 0;
  return Number(`${match[3]}${match[2]}${match[1]}`);
}

function updateSortMarks() {
  document.querySelectorAll(".audit-table th.sortable").forEach((th) => {
    const mark = th.querySelector(".sort-mark");
    mark.textContent = th.dataset.sort === sortState.field
      ? (sortState.direction === "asc" ? "▲" : "▼")
      : "";
  });
}

function searchableText(o) {
  return normalizeText([
    o.matricula,
    o.nome,
    o.data || o.dia,
    o.dia_semana,
    o.tipo_refeicao,
    o.status,
    o.descricao || o.motivo,
    o.acao_recomendada
  ].join(" "));
}

function normalizeText(value) {
  return String(fixMojibake(value) || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase();
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = fixMojibake(value ?? "");
  return div.innerHTML;
}

function getActionClass(text) {
  const value = normalizeText(text);
  if (!value || value.includes("NENHUMA")) return "action-ok";
  if (value.includes("DESCONTAR")) return "action-danger";
  if (value.includes("AGUARDAR")) return "action-info";
  if (value.includes("VALIDAR")) return "action-warn";
  return "";
}

function badgeHtml(status) {
  const normalized = normalizeText(status);
  const map = {
    "OK": "badge-ok",
    "GLOSA": "badge-glosa",
    "EXCECAO": "badge-excecao",
    "EXCEÇÃO": "badge-excecao",
    "REVISAO": "badge-revisao",
    "REVISÃO": "badge-revisao",
    "ALERTA": "badge-alerta",
    "PENDENTE": "badge-pendente",
    "DIVERGENCIA": "badge-divergencia",
    "DIVERGÊNCIA": "badge-divergencia"
  };

  return `<span class="badge ${map[normalized] || "badge-pendente"}">${escapeHtml(status)}</span>`;
}

function toggleExportMenu() {
  el("export-options").classList.toggle("open");
}

async function exportar() {
  if (!dadosAuditoria) return;
  el("export-options").classList.remove("open");

  try {
    const resp = await fetch("/api/exportar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cleanTextDeep(structuredClone(dadosAuditoria)))
    });

    if (!resp.ok) {
      mostrarErro("Falha ao exportar.");
      return;
    }

    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Auditoria_${dadosAuditoria.funcionario?.nome || "resultado"}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    mostrarErro(`Erro ao exportar: ${error.message}`);
  }
}

async function exportarPdf() {
  if (!dadosAuditoria) return;
  el("export-options").classList.remove("open");

  try {
    const resp = await fetch("/api/exportar_pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cleanTextDeep(structuredClone(dadosAuditoria)))
    });

    if (!resp.ok) {
      mostrarErro("Falha ao exportar PDF.");
      return;
    }

    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Auditoria_Refeicoes_${new Date().toISOString().slice(0, 10)}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    mostrarErro(`Erro ao exportar PDF: ${error.message}`);
  }
}

function mostrarErro(msg) {
  const box = el("erro-box");
  box.textContent = `⚠ ERRO: ${fixMojibake(msg)}`;
  box.style.display = "block";
}

function limparErro() {
  el("erro-box").style.display = "none";
}
