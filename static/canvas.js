let CANVAS_WIDTH = 480;
let CANVAS_HEIGHT = 800;
let GRID_SIZE = 40;
let GRID_PADDING = 4;
let REFRESH_INTERVAL = 1200;

const canvas = document.getElementById("gridCanvas");
const ctx = canvas.getContext("2d");

// UI Elements
const canvasWidthInput = document.getElementById("canvasWidthInput");
const canvasHeightInput = document.getElementById("canvasHeightInput");
const gridSizeInput = document.getElementById("gridSizeInput");
const gridPaddingInput = document.getElementById("gridPaddingInput");
const refreshIntervalInput = document.getElementById("refreshIntervalInput");
const applyCanvasSettingsBtn = document.getElementById("applyCanvasSettings");

const cellStaticTextInput = document.getElementById("cellStaticTextInput");
const cellImageSourceInput = document.getElementById("cellImageSourceInput");
const cellStaticImageFileInput = document.getElementById("cellStaticImageFileInput");
const cellStaticImageUrlInput = document.getElementById("cellStaticImageUrlInput");
const cellRoundInput = document.getElementById("cellRoundInput");

const cellNameInput = document.getElementById("cellNameInput");
const cellFnInput = document.getElementById("cellFnInput");
const cellFontSizeInput = document.getElementById("cellFontSizeInput");
const fontBoldInput = document.getElementById("fontBold");
const fontItalicInput = document.getElementById("fontItalic");
const cellWrapInput = document.getElementById("cellWrapInput");
const cellInvertInput = document.getElementById("cellInvertInput");
const cellScaleModeInput = document.getElementById("cellScaleModeInput");
const cellIndentInput = document.getElementById("cellIndentInput");
const cellOutlineInput = document.getElementById("cellOutlineInput");
const cellAutoTextSizeInput = document.getElementById("cellAutoTextSizeInput");
const cellTextTransformInput = document.getElementById("cellTextTransformInput");

const cellPrefixInput = document.getElementById("cellPrefixInput");
const cellSuffixInput = document.getElementById("cellSuffixInput");

const cellHaEntityIdInput = document.getElementById("cellHaEntityIdInput");
const haEntitiesCustomList = document.getElementById("haEntitiesCustomList");
const refreshHaEntitiesBtn = document.getElementById("refreshHaEntitiesBtn");
const haPreviewToggle = document.getElementById("haPreviewToggle");
const previewStatus = document.getElementById("previewStatus");

const addCellBtn = document.getElementById("addCellBtn");
const deleteCellBtn = document.getElementById("deleteCellBtn");
const lockLayoutBtn = document.getElementById("lockLayoutBtn");
const forceRefreshBtn = document.getElementById("forceRefreshBtn");

const cellHAlignInput = document.getElementById("cellHAlignInput");
const cellVAlignInput = document.getElementById("cellVAlignInput");

let cells = [];
let selectedCell = null;
let dragMode = null;
let dragOffsetX = 0;
let dragOffsetY = 0;
const HANDLE_SIZE = 10;
let globalHaEntities = [];

function setCanvasSize() {
  canvas.width = CANVAS_WIDTH;
  canvas.height = CANVAS_HEIGHT;
  draw();
}

function snapToGrid(value) {
  return Math.round(value / GRID_SIZE) * GRID_SIZE;
}

function clampFontSize(n) {
  if (isNaN(n)) return 12;
  return Math.max(6, Math.min(200, n));
}

function addCell() {
  const defaultWidth = GRID_SIZE * 6;
  const defaultHeight = GRID_SIZE * 3;

  const cell = {
    id: Date.now() + "_" + Math.random().toString(36).slice(2),
    x: snapToGrid((CANVAS_WIDTH - defaultWidth) / 2),
    y: snapToGrid((CANVAS_HEIGHT - defaultHeight) / 2),
    w: defaultWidth,
    h: defaultHeight,
    name: cellNameInput.value.trim() || "Cell " + (cells.length + 1),
    fnName: cellFnInput.value.trim(),
    invert: cellInvertInput.checked,
    fontSize: clampFontSize(parseInt(cellFontSizeInput.value, 10)),
    autoTextSize: cellAutoTextSizeInput.checked,
    textTransform: cellTextTransformInput.value || "none",
    hAlign: cellHAlignInput.value || "left",
    vAlign: cellVAlignInput.value || "top",
    scaleMode: cellScaleModeInput.value || "fit",
    staticText: cellStaticTextInput.value || "",
    staticImage:
      cellImageSourceInput && cellImageSourceInput.value === "url"
        ? cellStaticImageUrlInput.value.trim()
        : "",
    staticImageSource: cellImageSourceInput
      ? cellImageSourceInput.value || "none"
      : "none",
    indent: parseInt(cellIndentInput.value, 10) || 0,
    outline: cellOutlineInput.checked,
    wrapText: cellWrapInput.checked,
    haEntityId: cellHaEntityIdInput ? cellHaEntityIdInput.value.trim() : "",
    prefix: cellPrefixInput.value || "",
    suffix: cellSuffixInput.value || "",
    round: cellRoundInput.value !== "" ? parseInt(cellRoundInput.value, 10) : null,
  };

  cells.push(cell);
  selectedCell = cell;
  draw();
}

function drawGrid() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.strokeStyle = "#dddddd";
  ctx.lineWidth = 1;

  for (let x = 0; x <= canvas.width; x += GRID_SIZE) {
    ctx.beginPath();
    ctx.moveTo(x + 0.5, 0);
    ctx.lineTo(x + 0.5, canvas.height);
    ctx.stroke();
  }

  for (let y = 0; y <= canvas.height; y += GRID_SIZE) {
    ctx.beginPath();
    ctx.moveTo(0, y + 0.5);
    ctx.lineTo(canvas.width, y + 0.5);
    ctx.stroke();
  }
}

function transformText(text, mode) {
  if (!text) return "";
  switch (mode) {
    case "uppercase":
      return String(text).toUpperCase();
    case "lowercase":
      return String(text).toLowerCase();
    case "capitalize":
      return String(text).charAt(0).toUpperCase() + String(text).slice(1);
    case "titlecase":
      return String(text).replace(/\w\S*/g, (t) =>
        t.charAt(0).toUpperCase() + t.slice(1).toLowerCase()
      );
    default:
      return String(text);
  }
}

function breakWordJS(ctx, word, maxW, lines) {
  let currentStr = "";
  for (let i = 0; i < word.length; i++) {
    let testStr = currentStr + word[i];
    if (ctx.measureText(testStr).width > maxW && currentStr !== "") {
      lines.push(currentStr);
      currentStr = word[i];
    } else {
      currentStr = testStr;
    }
  }
  return currentStr;
}

function wrapTextJS(ctx, text, maxW) {
  let lines = [];
  String(text)
    .split("\n")
    .forEach((p) => {
      if (!p) {
        lines.push("");
        return;
      }
      let words = p.split(" ");
      let line = "";

      for (let i = 0; i < words.length; i++) {
        let word = words[i];
        let testLine = line + (line === "" ? "" : " ") + word;

        if (ctx.measureText(testLine).width <= maxW) {
          line = testLine;
        } else {
          if (line !== "") {
            lines.push(line);
            line = word;
            if (ctx.measureText(word).width > maxW) {
              line = breakWordJS(ctx, word, maxW, lines);
            }
          } else {
            line = breakWordJS(ctx, word, maxW, lines);
          }
        }
      }
      if (line !== "") lines.push(line);
    });
  return lines;
}

const _canvasImageCache = {};
function drawCells() {
  for (const cell of cells) {
    const fillColor = cell.invert ? "#000000" : "#ffffff";
    const textColor = cell.invert ? "#ffffff" : "#000000";
    const handleColor = "#808080";

    ctx.fillStyle = fillColor;
    ctx.fillRect(cell.x, cell.y, cell.w, cell.h);

    if (cell === selectedCell || cell.outline) {
      ctx.lineWidth = cell === selectedCell ? 3 : 1.5;
      ctx.strokeStyle = cell === selectedCell ? "#7e7e7eff" : "#000000ff";
      ctx.strokeRect(cell.x, cell.y, cell.w, cell.h);
    }

    ctx.fillStyle = handleColor;
    ctx.fillRect(
      cell.x + cell.w - HANDLE_SIZE,
      cell.y + cell.h - HANDLE_SIZE,
      HANDLE_SIZE,
      HANDLE_SIZE
    );

    ctx.fillStyle = textColor;
    ctx.textBaseline = "middle";

    // 1. Determine base text
    let label = "";

    // 1. Get raw content
    if (haPreviewToggle && haPreviewToggle.checked && cell.haEntityId) {
        const entity = globalHaEntities.find((e) => e.id === cell.haEntityId);
        label = entity ? entity.state : `[HA: ${cell.haEntityId}]`;
    } else {
        label = (cell.staticText && cell.staticText.trim().length > 0)
            ? cell.staticText
            : cell.name + (cell.fnName ? " • " + cell.fnName : "");
    }

    // --- NEW ROUNDING LOGIC ---
    if (cell.round !== null && cell.round !== undefined && !isNaN(parseFloat(label))) {
        let num = parseFloat(label);
        label = num.toFixed(cell.round);
    }

    // 2. APPLY PRE/POST FIXES
    if (cell.prefix) label = cell.prefix + label;
    if (cell.suffix) label = label + cell.suffix;

    // 3. APPLY TRANSFORMATIONS (now applies to the whole string ex: "TEMP: 22C")
    label = transformText(label, cell.textTransform);

    // --- NEW IMAGE PREVIEW LOGIC ---
    let imgPath = cell.staticImage;

    // AUTO-WEATHER ICON RESOLUTION
    if (haPreviewToggle.checked && cell.haEntityId && cell.haEntityId.startsWith("weather.")) {
        const entity = globalHaEntities.find(e => e.id === cell.haEntityId);
        if (entity) {
            const state = entity.state.toLowerCase().replace(/[^a-z0-9]/g, '');
            const iconMap = {
                "partlycloudy": "https://img.icons8.com/forma-bold/100/partly-cloudy-day.png",
                "sunny": "https://img.icons8.com/forma-bold/100/sun.png",
                "cloudy": "https://img.icons8.com/forma-bold/100/cloud.png",
                "rainy": "https://img.icons8.com/forma-bold/100/light-rain.png",
                "clear": "https://img.icons8.com/forma-bold/100/sun.png"
            };
            imgPath = iconMap[state] || "https://img.icons8.com/forma-bold/100/error.png";
        }
    }

    if (cell.staticImage && cell.staticImageSource !== "none") {
        const imgPath = cell.staticImage;
        
        if (!_canvasImageCache[imgPath]) {
            const imgObj = new Image();
            imgObj.src = imgPath.startsWith('http') ? imgPath : '/' + imgPath;
            imgObj.onload = () => {
                _canvasImageCache[imgPath] = imgObj;
                draw(); // Redraw once loaded
            };
            // Draw placeholder while loading
            ctx.fillStyle = "#ccc";
            ctx.fillText("Loading...", cell.x + cell.w/2, cell.y + cell.h/2);
        } else {
            const cachedImg = _canvasImageCache[imgPath];
            const mode = (cell.scaleMode || "fit").toLowerCase();
            const padding = (cell.indent || 0) + 4;

            ctx.save();
            ctx.beginPath();
            ctx.rect(cell.x, cell.y, cell.w, cell.h);
            ctx.clip();

            if (cell.invert) {
                ctx.filter = "invert(100%)";
            }

            if (mode === "fill") {
                ctx.drawImage(cachedImg, cell.x, cell.y, cell.w, cell.h);
            } else if (mode === "none") {
                ctx.drawImage(cachedImg, cell.x + padding, cell.y + padding);
            } else { // fit
                const scale = Math.min((cell.w - padding*2) / cachedImg.width, (cell.h - padding*2) / cachedImg.height);
                const nw = cachedImg.width * scale;
                const nh = cachedImg.height * scale;
                ctx.drawImage(cachedImg, cell.x + (cell.w - nw)/2, cell.y + (cell.h - nh)/2, nw, nh);
            }
            ctx.restore();
            continue; // Skip text rendering if we drew an image
        }
    }

    // 2. Apply transformations
    label = transformText(label, cell.textTransform);

    const hAlign = (cell.hAlign || "left").toLowerCase();
    const vAlign = (cell.vAlign || "top").toLowerCase();
    const padding = (cell.indent || 0) + 4;
    const maxW = Math.max(10, cell.w - 2 * padding);
    const maxH = Math.max(10, cell.h - 2 * padding);
    const shouldWrap = cell.wrapText !== false;
    const autoSize = cell.autoTextSize === true;
    let fontSize = clampFontSize(cell.fontSize || 12);

    let wrappedLines = [];
    let activeFontSize = fontSize;

    // 3. Size and Wrap
    if (autoSize) {
      let testSize = Math.min(maxH, 200);
      while (testSize >= 6) {
        ctx.font = `${cell.fontItalic ? "italic " : ""}${
          cell.fontBold ? "bold " : ""
        }${testSize}px system-ui, sans-serif`;
        wrappedLines = shouldWrap
          ? wrapTextJS(ctx, label, maxW)
          : String(label).split("\n");

        const totalH = (testSize + 2) * wrappedLines.length;
        const maxLineW = Math.max(
          ...wrappedLines.map((l) => ctx.measureText(l).width),
          0
        );

        if (totalH <= maxH && maxLineW <= maxW) break;
        testSize--;
      }
      activeFontSize = testSize;
    } else {
      ctx.font = `${cell.fontItalic ? "italic " : ""}${
        cell.fontBold ? "bold " : ""
      }${activeFontSize}px system-ui, sans-serif`;
      wrappedLines = shouldWrap
        ? wrapTextJS(ctx, label, maxW)
        : label.split("\n");
    }

    const lineHeight = activeFontSize + 2;
    const totalH = lineHeight * wrappedLines.length;

    let yStart;
    if (vAlign === "middle") {
      yStart = cell.y + cell.h / 2 - totalH / 2 + lineHeight / 2;
    } else if (vAlign === "bottom") {
      yStart = cell.y + cell.h - padding - totalH + lineHeight / 2;
    } else {
      yStart = cell.y + padding + lineHeight / 2;
    }

    ctx.save();
    ctx.beginPath();
    ctx.rect(cell.x, cell.y, cell.w, cell.h);
    ctx.clip();

    wrappedLines.forEach((line, i) => {
      const tw = ctx.measureText(line).width;
      let tx;
      if (hAlign === "center") tx = cell.x + (cell.w - tw) / 2;
      else if (hAlign === "right") tx = cell.x + cell.w - padding - tw;
      else tx = cell.x + padding;

      const currY = yStart + i * lineHeight;
      if (
        currY + activeFontSize / 2 <= cell.y + cell.h + 2 &&
        currY - activeFontSize / 2 >= cell.y - 2
      ) {
        ctx.fillText(line, tx, currY);
      }
    });

    ctx.restore();
  }
}

function draw() {
  drawGrid();
  drawCells();
}

function getMousePos(evt) {
  const rect = canvas.getBoundingClientRect();
  return { x: evt.clientX - rect.left, y: evt.clientY - rect.top };
}

function hitTestCell(x, y) {
  for (let i = cells.length - 1; i >= 0; i--) {
    const c = cells[i];
    if (x >= c.x && x <= c.x + c.w && y >= c.y && y <= c.y + c.h) return c;
  }
  return null;
}

function isOnResizeHandle(cell, x, y) {
  return (
    x >= cell.x + cell.w - HANDLE_SIZE &&
    x <= cell.x + cell.w &&
    y >= cell.y + cell.h - HANDLE_SIZE &&
    y <= cell.y + cell.h
  );
}

[cellPrefixInput, cellSuffixInput].forEach((el) => {
    el.addEventListener("input", () => {
        if (selectedCell) {
            selectedCell.prefix = cellPrefixInput.value;
            selectedCell.suffix = cellSuffixInput.value;
            draw();
        }
    });
});

cellRoundInput.addEventListener("input", () => {
    if (selectedCell) {
        let val = cellRoundInput.value;
        selectedCell.round = val !== "" ? parseInt(val, 10) : null;
        draw();
    }
});

// Event Listeners
canvas.addEventListener("mousedown", (evt) => {
    const pos = getMousePos(evt);
    const cell = hitTestCell(pos.x, pos.y);

    if (!cell) {
        selectedCell = null;
        dragMode = null;
        draw();
        return;
    }

    selectedCell = cell;

    cellPrefixInput.value = selectedCell.prefix || "";
    cellSuffixInput.value = selectedCell.suffix || "";
    cellRoundInput.value = (selectedCell.round !== null && selectedCell.round !== undefined) ? selectedCell.round : "";

    cellNameInput.value = cell.name;
    cellFnInput.value = cell.fnName || "";
    cellInvertInput.checked = !!cell.invert;
    cellFontSizeInput.value = clampFontSize(cell.fontSize || 12);
    cellAutoTextSizeInput.checked = !!cell.autoTextSize;
    cellTextTransformInput.value = cell.textTransform || "none";
    fontBoldInput.checked = !!cell.fontBold;
    fontItalicInput.checked = !!cell.fontItalic;
    cellHAlignInput.value = cell.hAlign || "left";
    cellVAlignInput.value = cell.vAlign || "top";
    cellWrapInput.checked = cell.wrapText !== false;
    cellScaleModeInput.value = cell.scaleMode || "fit";
    cellStaticTextInput.value = cell.staticText || "";
    const src = cell.staticImageSource || (cell.staticImage ? "url" : "none");
    cellImageSourceInput.value = src;
    cellStaticImageUrlInput.value = src === "url" ? cell.staticImage || "" : "";
    cellStaticImageFileInput.value = "";
    cellIndentInput.value = selectedCell.indent || 0;
    cellOutlineInput.checked = !!selectedCell.outline;
    if (cellHaEntityIdInput) cellHaEntityIdInput.value = cell.haEntityId || "";

    if (isOnResizeHandle(cell, pos.x, pos.y)) {
        dragMode = "resize";
        dragOffsetX = pos.x - (cell.x + cell.w);
        dragOffsetY = pos.y - (cell.y + cell.h);
    } else {
        dragMode = "move";
        dragOffsetX = pos.x - cell.x;
        dragOffsetY = pos.y - cell.y;
    }

    draw();
});

canvas.addEventListener("mousemove", (evt) => {
  if (!selectedCell || !dragMode) return;
  const pos = getMousePos(evt);
  if (dragMode === "move") {
    let newX = snapToGrid(pos.x - dragOffsetX);
    let newY = snapToGrid(pos.y - dragOffsetY);
    newX = Math.max(0, Math.min(newX, CANVAS_WIDTH - selectedCell.w));
    newY = Math.max(0, Math.min(newY, CANVAS_HEIGHT - selectedCell.h));
    selectedCell.x = newX;
    selectedCell.y = newY;
  } else if (dragMode === "resize") {
    let newW = snapToGrid(pos.x - selectedCell.x - dragOffsetX);
    let newH = snapToGrid(pos.y - selectedCell.y - dragOffsetY);
    const minSize = GRID_SIZE * 1;
    newW = Math.max(minSize, Math.min(newW, CANVAS_WIDTH - selectedCell.x));
    newH = Math.max(minSize, Math.min(newH, CANVAS_HEIGHT - selectedCell.y));
    selectedCell.w = newW;
    selectedCell.h = newH;
  }
  draw();
});

window.addEventListener("mouseup", () => {
  dragMode = null;
});
canvas.addEventListener("mouseleave", () => {
  dragMode = null;
});

// Setting Inputs listeners
[
  cellNameInput,
  cellFnInput,
  cellFontSizeInput,
  cellInvertInput,
  cellAutoTextSizeInput,
  cellTextTransformInput,
  fontBoldInput,
  fontItalicInput,
  cellHAlignInput,
  cellVAlignInput,
  cellScaleModeInput,
  cellIndentInput,
  cellOutlineInput,
  cellWrapInput,
].forEach((el) => {
  el.addEventListener("change", () => {
    if (!selectedCell) return;
    selectedCell.name = cellNameInput.value.trim() || selectedCell.name;
    selectedCell.fnName = cellFnInput.value.trim();
    selectedCell.invert = cellInvertInput.checked;
    selectedCell.fontSize = clampFontSize(parseInt(cellFontSizeInput.value, 10));
    selectedCell.autoTextSize = cellAutoTextSizeInput.checked;
    selectedCell.textTransform = cellTextTransformInput.value || "none";
    selectedCell.fontBold = fontBoldInput.checked;
    selectedCell.fontItalic = fontItalicInput.checked;
    selectedCell.hAlign = cellHAlignInput.value || "left";
    selectedCell.vAlign = cellVAlignInput.value || "top";
    selectedCell.scaleMode = (cellScaleModeInput.value || "fit").toLowerCase();
    selectedCell.indent = parseInt(cellIndentInput.value, 10) || 0;
    selectedCell.outline = cellOutlineInput.checked;
    selectedCell.wrapText = cellWrapInput.checked;
    draw();
  });
});

cellStaticTextInput.addEventListener("input", () => {
  if (selectedCell) {
    selectedCell.staticText = cellStaticTextInput.value || "";
    draw();
  }
});

// HA Preview Toggle listener
if (haPreviewToggle) {
  haPreviewToggle.addEventListener("change", () => {
    if (haPreviewToggle.checked) {
      if (previewStatus) previewStatus.innerText = "Fetching live states...";
      loadHaEntities().then(() => {
        if (previewStatus) previewStatus.innerText = "Live";
        draw();
      });
    } else {
      if (previewStatus) previewStatus.innerText = "";
      draw();
    }
  });
}

// Rest of the supporting functions (HA Dropdown, Fetch, etc.)
function renderDropdown(filterText = "") {
  if (!haEntitiesCustomList) return;
  haEntitiesCustomList.innerHTML = "";
  const lowerFilter = filterText.toLowerCase();

  const filtered = globalHaEntities
    .filter(
      (ent) =>
        ent.id.toLowerCase().includes(lowerFilter) ||
        (ent.name && ent.name.toLowerCase().includes(lowerFilter))
    )
    .slice(0, 100);

  if (filtered.length === 0) {
    const empty = document.createElement("div");
    empty.className = "dropdown-option empty";
    empty.innerText = "No matching entities found";
    haEntitiesCustomList.appendChild(empty);
    return;
  }

  filtered.forEach((ent) => {
    const div = document.createElement("div");
    div.className = "dropdown-option";
    div.innerHTML = `<strong>${ent.name || "Unnamed Entity"}</strong><small>${
      ent.id
    }</small>`;

    div.addEventListener("mousedown", (e) => {
      e.preventDefault();
      cellHaEntityIdInput.value = ent.id;
      haEntitiesCustomList.classList.add("hidden");
      if (selectedCell) {
        selectedCell.haEntityId = ent.id;
        draw();
      }
    });
    haEntitiesCustomList.appendChild(div);
  });
}

if (cellHaEntityIdInput) {
  cellHaEntityIdInput.addEventListener("focus", () => {
    renderDropdown(cellHaEntityIdInput.value);
    haEntitiesCustomList.classList.remove("hidden");
  });
  cellHaEntityIdInput.addEventListener("input", (e) => {
    renderDropdown(e.target.value);
    haEntitiesCustomList.classList.remove("hidden");
    if (selectedCell) {
      selectedCell.haEntityId = e.target.value.trim();
      draw();
    }
  });
  cellHaEntityIdInput.addEventListener("blur", () => {
    haEntitiesCustomList.classList.add("hidden");
  });
}

refreshHaEntitiesBtn.addEventListener("click", loadHaEntities);

async function loadHaEntities() {
  try {
    const resp = await fetch("/api/ha_entities");
    if (resp.ok) {
      globalHaEntities = await resp.json();
      if (document.activeElement === cellHaEntityIdInput)
        renderDropdown(cellHaEntityIdInput.value);
    }
  } catch (e) {
    console.error("Failed to fetch HA entities", e);
  }
}

async function loadSavedLayout() {
  try {
    const resp = await fetch("/canvas_layout");
    if (!resp.ok) {
      setCanvasSize();
      return;
    }
    const data = await resp.json();
    if (!data || !data.canvas) {
      setCanvasSize();
      return;
    }

    CANVAS_WIDTH = data.canvas.width || CANVAS_WIDTH;
    CANVAS_HEIGHT = data.canvas.height || CANVAS_HEIGHT;
    GRID_SIZE = data.canvas.gridSize || GRID_SIZE;
    GRID_PADDING = data.canvas.padding || 4;
    REFRESH_INTERVAL = data.canvas.refreshInterval || 1200;

    canvasWidthInput.value = CANVAS_WIDTH;
    canvasHeightInput.value = CANVAS_HEIGHT;
    gridSizeInput.value = GRID_SIZE;
    gridPaddingInput.value = GRID_PADDING;
    refreshIntervalInput.value = REFRESH_INTERVAL;

    cells = (data.cells || []).map((c) => ({
      ...c,
      invert: !!c.invert,
      fontSize: clampFontSize(c.fontSize || 12),
      autoTextSize: !!c.autoTextSize,
      textTransform: c.textTransform || "none",
      fontBold: !!c.fontBold,
      fontItalic: !!c.fontItalic,
      scaleMode: (c.scaleMode || "fit").toLowerCase(),
      wrapText: c.wrapText !== false,
      outline: !!c.outline,
    }));
    setCanvasSize();
  } catch (e) {
    setCanvasSize();
  }
}

// Initial Load
loadSavedLayout();
loadHaEntities();

addCellBtn.addEventListener("click", addCell);
deleteCellBtn.addEventListener("click", () => {
  if (!selectedCell) return;
  cells = cells.filter((c) => c !== selectedCell);
  selectedCell = null;
  draw();
});

applyCanvasSettingsBtn.addEventListener("click", () => {
  CANVAS_WIDTH =
    Math.max(100, parseInt(canvasWidthInput.value, 10)) || CANVAS_WIDTH;
  CANVAS_HEIGHT =
    Math.max(100, parseInt(canvasHeightInput.value, 10)) || CANVAS_HEIGHT;
  GRID_SIZE = Math.max(5, parseInt(gridSizeInput.value, 10)) || GRID_SIZE;
  GRID_PADDING =
    Math.max(0, parseInt(gridPaddingInput.value, 10)) || GRID_PADDING;
  REFRESH_INTERVAL =
    Math.max(60, parseInt(refreshIntervalInput.value, 10)) || REFRESH_INTERVAL;
  setCanvasSize();
});

lockLayoutBtn.addEventListener("click", async () => {
  const layout = {
    canvas: {
        width: CANVAS_WIDTH,
        height: CANVAS_HEIGHT,
        gridSize: GRID_SIZE,
        padding: GRID_PADDING,
        refreshInterval: REFRESH_INTERVAL,
    },
    cells: cells.map((c) => ({
        id: c.id,
        x: c.x,
        y: c.y,
        w: c.w,
        h: c.h,
        name: c.name,
        fnName: c.fnName || "",
        invert: !!c.invert,
        fontSize: clampFontSize(c.fontSize || 12),
        autoTextSize: !!c.autoTextSize,
        textTransform: c.textTransform || "none",
        fontBold: !!c.fontBold,
        fontItalic: !!c.fontItalic,
        wrapText: c.wrapText !== false,
        hAlign: c.hAlign || "left",
        vAlign: c.vAlign || "top",
        scaleMode: c.scaleMode || "fit",
        staticText: c.staticText || "",
        staticImage: c.staticImage || "",
        staticImageSource: c.staticImageSource || "none",
        indent: c.indent || 0,
        outline: !!c.outline,
        haEntityId: c.haEntityId || "",
        prefix: c.prefix || "",
        suffix: c.suffix || "",
        round: (c.round !== null && c.round !== undefined) ? c.round : null,
    })),
  };
  try {
    const resp = await fetch("/canvas_layout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(layout),
    });
    if (!resp.ok) alert("Failed to save layout");
    else alert("Layout saved.");
  } catch (e) {
    alert("Error saving layout");
  }
});

forceRefreshBtn.addEventListener("click", async () => {
  try {
    forceRefreshBtn.innerText = "Refreshing...";
    forceRefreshBtn.disabled = true;
    const resp = await fetch("/force_push", { method: "POST" });
    if (resp.ok) {
      setTimeout(() => {
        forceRefreshBtn.innerText = "Force Refresh Pi";
        forceRefreshBtn.disabled = false;
      }, 2000);
    } else {
      alert("Failed to trigger refresh.");
      forceRefreshBtn.disabled = false;
    }
  } catch (e) {
    alert("Error connecting");
    forceRefreshBtn.disabled = false;
  }
});