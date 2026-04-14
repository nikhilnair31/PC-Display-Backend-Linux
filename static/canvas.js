// canvas.js

let CANVAS_WIDTH = 480;
let CANVAS_HEIGHT = 800;
let GRID_SIZE = 40;
let GRID_PADDING = 4;
let REFRESH_INTERVAL = 1200;

const canvas = document.getElementById("gridCanvas");
const ctx = canvas.getContext("2d");

const canvasWidthInput = document.getElementById("canvasWidthInput");
const canvasHeightInput = document.getElementById("canvasHeightInput");
const gridSizeInput = document.getElementById("gridSizeInput");
const gridPaddingInput = document.getElementById("gridPaddingInput");
const refreshIntervalInput = document.getElementById("refreshIntervalInput");
const applyCanvasSettingsBtn = document.getElementById("applyCanvasSettings");

const cellStaticTextInput = document.getElementById("cellStaticTextInput");
const cellImageSourceInput = document.getElementById("cellImageSourceInput");
const cellStaticImageFileInput = document.getElementById("cellStaticImageFileInput");
const cellStaticImageUrlInput  = document.getElementById("cellStaticImageUrlInput");

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

const cellHaEntityIdInput = document.getElementById("cellHaEntityIdInput");
const cellHaEntityTypeInput = document.getElementById("cellHaEntityTypeInput");

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
    const name = cellNameInput.value.trim() || ("Cell " + (cells.length + 1));
    const fnName = cellFnInput.value.trim();
    const invert = cellInvertInput.checked;
    const fontSize = clampFontSize(parseInt(cellFontSizeInput.value, 10));
    
    const defaultWidth = GRID_SIZE * 6;
    const defaultHeight = GRID_SIZE * 3;

    const cell = {
        id: Date.now() + "_" + Math.random().toString(36).slice(2),
        x: snapToGrid((CANVAS_WIDTH - defaultWidth) / 2),
        y: snapToGrid((CANVAS_HEIGHT - defaultHeight) / 2),
        w: defaultWidth,
        h: defaultHeight,
        name: name,
        fnName: fnName,
        invert: invert,
        fontSize: fontSize,
        autoTextSize: cellAutoTextSizeInput.checked,
        textTransform: cellTextTransformInput.value || "none",
        hAlign: cellHAlignInput.value || "left",
        vAlign: cellVAlignInput.value || "top",
        scaleMode: cellScaleModeInput.value || "fit",
        staticText: cellStaticTextInput.value || "",
        staticImage: (cellImageSourceInput && cellImageSourceInput.value === "url") ? (cellStaticImageUrlInput.value.trim()) : "",
        staticImageSource: cellImageSourceInput ? (cellImageSourceInput.value || "none") : "none",
        indent: 0,
        outline: false,
        wrapText: true,
        haEntityId: cellHaEntityIdInput ? cellHaEntityIdInput.value.trim() : "",
        haEntityType: cellHaEntityTypeInput ? cellHaEntityTypeInput.value : "none",
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

// Function to handle Text Transformation
function transformText(text, mode) {
    if (!text) return "";
    switch (mode) {
        case "uppercase": return text.toUpperCase();
        case "lowercase": return text.toLowerCase();
        case "capitalize": return text.charAt(0).toUpperCase() + text.slice(1);
        case "titlecase": return text.replace(/\w\S*/g, t => t.charAt(0).toUpperCase() + t.slice(1).toLowerCase());
        default: return text;
    }
}

// Function to handle text wrapping identically to Python logic
function wrapTextJS(ctx, text, maxW) {
    let lines = [];
    text.split('\n').forEach(p => {
        let words = p.split(' ');
        if(words.length === 0) return;
        let line = words[0];
        for (let n = 1; n < words.length; n++) {
            let testLine = line + ' ' + words[n];
            if (ctx.measureText(testLine).width <= maxW) {
                line = testLine;
            } else {
                lines.push(line);
                line = words[n];
            }
        }
        lines.push(line);
    });
    return lines;
}

function drawCells() {
    for (const cell of cells) {
        const fillColor = cell.invert ? "#000000" : "#ffffff";
        const textColor = cell.invert ? "#ffffff" : "#000000";
        const handleColor = "#808080";

        ctx.fillStyle = fillColor;
        ctx.fillRect(cell.x, cell.y, cell.w, cell.h);

        if (cell === selectedCell || cell.outline) {
            ctx.lineWidth = (cell === selectedCell) ? 3 : 1.5;
            ctx.strokeStyle = (cell === selectedCell) ? "#7e7e7eff" : "#000000ff";
            ctx.strokeRect(cell.x, cell.y, cell.w, cell.h);
        }

        ctx.fillStyle = handleColor;
        ctx.fillRect(cell.x + cell.w - HANDLE_SIZE, cell.y + cell.h - HANDLE_SIZE, HANDLE_SIZE, HANDLE_SIZE);

        ctx.fillStyle = textColor;
        ctx.textBaseline = "middle";

        let label = (cell.staticText && cell.staticText.trim().length > 0) 
            ? cell.staticText 
            : (cell.name + (cell.fnName ? (" • " + cell.fnName) : ""));

        // Text Processing
        label = transformText(label, cell.textTransform);

        const hAlign = (cell.hAlign || "left").toLowerCase();
        const vAlign = (cell.vAlign || "top").toLowerCase();
        const padding = (cell.indent || 0) + 4;
        const maxW = Math.max(10, cell.w - (2 * padding));
        const maxH = Math.max(10, cell.h - (2 * padding));
        const shouldWrap = cell.wrapText !== false;
        const autoSize = cell.autoTextSize === true;
        let fontSize = clampFontSize(cell.fontSize || 12);
        
        let wrappedLines = [];
        let activeFontSize = fontSize;

        if (autoSize) {
            let testSize = Math.min(maxH, 200);
            while (testSize >= 6) {
                ctx.font = `${cell.fontItalic ? 'italic ' : ''}${cell.fontBold ? 'bold ' : ''}${testSize}px system-ui, sans-serif`;
                wrappedLines = shouldWrap ? wrapTextJS(ctx, label, maxW) : label.split('\n');
                
                const totalH = (testSize + 2) * wrappedLines.length;
                const maxLineW = Math.max(...wrappedLines.map(l => ctx.measureText(l).width), 0);
                
                if (totalH <= maxH && maxLineW <= maxW) {
                    break;
                }
                testSize--;
            }
            activeFontSize = testSize;
        } else {
            ctx.font = `${cell.fontItalic ? 'italic ' : ''}${cell.fontBold ? 'bold ' : ''}${activeFontSize}px system-ui, sans-serif`;
            wrappedLines = shouldWrap ? wrapTextJS(ctx, label, maxW) : label.split('\n');
        }

        const lineHeight = activeFontSize + 2;
        const totalH = lineHeight * wrappedLines.length;

        let yStart;
        if (vAlign === "middle") {
            yStart = cell.y + (cell.h / 2) - (totalH / 2) + (lineHeight / 2);
        } else if (vAlign === "bottom") {
            yStart = cell.y + cell.h - padding - totalH + (lineHeight / 2);
        } else {
            yStart = cell.y + padding + (lineHeight / 2);
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

            const currY = yStart + (i * lineHeight);
            if (currY + (activeFontSize/2) <= cell.y + cell.h + 2 && currY - (activeFontSize/2) >= cell.y - 2) {
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

    // Load into form
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
    cellStaticImageUrlInput.value = src === "url" ? (cell.staticImage || "") : "";
    cellStaticImageFileInput.value = "";
    cellIndentInput.value = selectedCell.indent || 0;
    cellOutlineInput.checked = !!selectedCell.outline;
    if(cellHaEntityIdInput) cellHaEntityIdInput.value = cell.haEntityId || "";
    if(cellHaEntityTypeInput) cellHaEntityTypeInput.value = cell.haEntityType || "none";

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
        selectedCell.x = newX; selectedCell.y = newY;
    } else if (dragMode === "resize") {
        let newW = snapToGrid(pos.x - selectedCell.x - dragOffsetX);
        let newH = snapToGrid(pos.y - selectedCell.y - dragOffsetY);
        const minSize = GRID_SIZE * 1;
        newW = Math.max(minSize, Math.min(newW, CANVAS_WIDTH - selectedCell.x));
        newH = Math.max(minSize, Math.min(newH, CANVAS_HEIGHT - selectedCell.y));
        selectedCell.w = newW; selectedCell.h = newH;
    }
    draw();
});

window.addEventListener("mouseup", () => { dragMode = null; });
canvas.addEventListener("mouseleave", () => { dragMode = null; });

// Update cell properties when form changes
cellNameInput.addEventListener("change", () => { if (selectedCell) { selectedCell.name = cellNameInput.value.trim() || selectedCell.name; draw(); } });
cellFnInput.addEventListener("change", () => { if (selectedCell) { selectedCell.fnName = cellFnInput.value.trim(); draw(); } });
cellInvertInput.addEventListener("change", () => { if (selectedCell) { selectedCell.invert = cellInvertInput.checked; draw(); } });
cellFontSizeInput.addEventListener("change", () => { if (selectedCell) { selectedCell.fontSize = clampFontSize(parseInt(cellFontSizeInput.value, 10)); draw(); } });
cellAutoTextSizeInput.addEventListener("change", () => { if (selectedCell) { selectedCell.autoTextSize = cellAutoTextSizeInput.checked; draw(); } });
cellTextTransformInput.addEventListener("change", () => { if (selectedCell) { selectedCell.textTransform = cellTextTransformInput.value || "none"; draw(); } });
fontBoldInput.addEventListener("change", () => { if (selectedCell) { selectedCell.fontBold = fontBoldInput.checked; draw(); } });
fontItalicInput.addEventListener("change", () => { if (selectedCell) { selectedCell.fontItalic = fontItalicInput.checked; draw(); } });
cellHAlignInput.addEventListener("change", () => { if (selectedCell) { selectedCell.hAlign = cellHAlignInput.value || "left"; draw(); } });
cellVAlignInput.addEventListener("change", () => { if (selectedCell) { selectedCell.vAlign = cellVAlignInput.value || "top"; draw(); } });
cellScaleModeInput.addEventListener("change", () => {
    if (selectedCell) {
        const v = (cellScaleModeInput.value || "fit").toLowerCase();
        if (v === "fit" || v === "fill" || v === "none") { selectedCell.scaleMode = v; draw(); }
    }
});
cellStaticTextInput.addEventListener("input", () => { if (selectedCell) { selectedCell.staticText = cellStaticTextInput.value || ""; draw(); } });
cellImageSourceInput.addEventListener("change", () => {
    if (!selectedCell) return;
    const src = cellImageSourceInput.value || "none";
    selectedCell.staticImageSource = src;
    if (src === "none") {
        selectedCell.staticImage = "";
        cellStaticImageUrlInput.value = "";
        cellStaticImageFileInput.value = "";
    }
    draw();
});
cellStaticImageFileInput.addEventListener("change", async (e) => {
    if (!selectedCell) return;
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    try {
        const resp = await fetch("/upload_static_image", { method: "POST", body: formData });
        if (!resp.ok) {
            const txt = await resp.text();
            alert("Failed to upload image: " + resp.status + " - " + txt);
            return;
        }
        const data = await resp.json();
        selectedCell.staticImage = data.path;
        selectedCell.staticImageSource = "upload";
        cellImageSourceInput.value = "upload";
        draw();
    } catch (err) {
        alert("Error uploading image (see console).");
    }
});
cellStaticImageUrlInput.addEventListener("change", () => {
    if (!selectedCell) return;
    const url = cellStaticImageUrlInput.value.trim();
    selectedCell.staticImage = url;
    selectedCell.staticImageSource = url ? "url" : "none";
    cellImageSourceInput.value = selectedCell.staticImageSource;
    draw();
});
cellIndentInput.addEventListener("change", () => { if (selectedCell) { selectedCell.indent = parseInt(cellIndentInput.value, 10) || 0; draw(); } });
cellOutlineInput.addEventListener("change", () => { if (selectedCell) { selectedCell.outline = cellOutlineInput.checked; draw(); } });
cellWrapInput.addEventListener("change", () => { if (selectedCell) { selectedCell.wrapText = cellWrapInput.checked; draw(); } });
cellHaEntityIdInput.addEventListener("change", () => { if (selectedCell) { selectedCell.haEntityId = cellHaEntityIdInput.value.trim(); draw(); } });
cellHaEntityTypeInput.addEventListener("change", () => { if (selectedCell) { selectedCell.haEntityType = cellHaEntityTypeInput.value; draw(); } });

addCellBtn.addEventListener("click", addCell);
deleteCellBtn.addEventListener("click", () => {
    if (!selectedCell) return;
    cells = cells.filter(c => c !== selectedCell);
    selectedCell = null;
    draw();
});

applyCanvasSettingsBtn.addEventListener("click", () => {
    CANVAS_WIDTH = Math.max(100, parseInt(canvasWidthInput.value, 10) || CANVAS_WIDTH);
    CANVAS_HEIGHT = Math.max(100, parseInt(canvasHeightInput.value, 10) || CANVAS_HEIGHT);
    GRID_SIZE = Math.max(5, parseInt(gridSizeInput.value, 10) || GRID_SIZE);
    GRID_PADDING = Math.max(4, parseInt(gridPaddingInput.value, 10) || GRID_PADDING);
    REFRESH_INTERVAL = Math.max(60, parseInt(refreshIntervalInput.value, 10) || REFRESH_INTERVAL);
    setCanvasSize();
});

lockLayoutBtn.addEventListener("click", async () => {
    const layout = {
        canvas: { 
            width: CANVAS_WIDTH, height: CANVAS_HEIGHT, 
            gridSize: GRID_SIZE, padding: GRID_PADDING, refreshInterval: REFRESH_INTERVAL
        },
        cells: cells.map(c => ({
            id: c.id, x: c.x, y: c.y, w: c.w, h: c.h,
            name: c.name, fnName: c.fnName || "",
            invert: !!c.invert,
            fontSize: clampFontSize(c.fontSize || 12),
            autoTextSize: !!c.autoTextSize,
            textTransform: c.textTransform || "none",
            fontBold: !!c.fontBold,
            fontItalic: !!c.fontItalic,
            wrapText: c.wrapText !== false,
            hAlign: c.hAlign || "left", vAlign: c.vAlign || "top",
            scaleMode: c.scaleMode || "fit",
            staticText: c.staticText || "",
            staticImage: c.staticImage || "", staticImageSource: c.staticImageSource || "none",
            indent: c.indent || 0,
            outline: !!c.outline,
            haEntityId: c.haEntityId || "", haEntityType: c.haEntityType || "none",
        }))
    };
    try {
        const resp = await fetch("/canvas_layout", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify(layout)
        });
        if (!resp.ok) alert("Failed to save layout: " + resp.status);
        else alert("Layout saved.");
    } catch (e) {
        alert("Error saving layout (see console).");
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
        alert("Error connecting to server.");
        forceRefreshBtn.disabled = false;
    }
});

async function loadSavedLayout() {
    try {
        const resp = await fetch("/canvas_layout");
        if (!resp.ok) { setCanvasSize(); return; }
        const data = await resp.json();
        if (!data || !data.canvas) { setCanvasSize(); return; }

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

        cells = (data.cells || []).map(c => ({
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

loadSavedLayout();