/** @odoo-module **/

import { Component, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { isBinarySize } from "@web/core/utils/binary";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const DOCUMENTS = {
    certificate: {
        pdfField: "certificate_pdf",
        fields: ["company", "event_name", "event_date", "topics", "presented_by"],
        previewMethod: "get_certificate_pdf_preview_values",
        reportName: "event_certificates_signup.company_certificate_report",
    },
    signup_sheet: {
        pdfField: "signup_sheet_pdf",
        fields: ["company", "event_name", "event_date", "topic", "start_time", "finish_time", "instructor", "instructor_signature", "presented_by"],
        previewMethod: "get_signup_sheet_pdf_preview_values",
        reportName: "event_certificates_signup.signup_sheet_report",
    },
};
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

export class CertificatePdfDesigner extends Component {
    static template = "event_certificates_signup.CertificatePdfDesigner";
    static props = { ...standardFieldProps, documentType: { type: String, optional: true } };
    static defaultProps = { documentType: "certificate" };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.stage = useRef("stage");
        this.canvas = useRef("canvas");
        this.state = useState({
            fields: [], selectedId: null, loading: false, error: "", layoutError: "",
            pageWidth: 792, pageHeight: 612, stageWidth: 792,
            showValues: false, values: {},
        });
        this.fieldNames = this.documentConfig.fields;
        this.generation = 0;
        this.lastLayout = undefined;
        this.readLayout();

        useEffect(() => { this.readLayout(); }, () => [this.props.record.data[this.props.name]]);
        useEffect(() => {
            this.loadPdf();
            return () => { this.generation++; };
        }, () => [this.props.record.data[this.documentConfig.pdfField], this.props.record.resId]);
        useEffect(() => {
            const stage = this.stage.el;
            if (!stage) {
                return;
            }
            const observer = new ResizeObserver(() => {
                this.state.stageWidth = stage.clientWidth;
            });
            observer.observe(stage);
            this.state.stageWidth = stage.clientWidth;
            return () => observer.disconnect();
        }, () => [this.stage.el]);
        onWillUnmount(() => {
            this.generation++;
            this.pdfTask?.destroy();
            this.removeDragListeners();
        });
    }

    get documentConfig() {
        return DOCUMENTS[this.props.documentType];
    }

    get hasPdf() {
        return Boolean(this.props.record.data[this.documentConfig.pdfField]);
    }

    get selected() {
        return this.state.fields.find((field) => field.id === this.state.selectedId);
    }

    readLayout() {
        const value = this.props.record.data[this.props.name] || "";
        if (value === this.lastLayout) {
            return;
        }
        this.lastLayout = value;
        try {
            const layout = value ? JSON.parse(value) : { version: 1, fields: [] };
            if (layout.version !== 1 || !Array.isArray(layout.fields)) {
                throw new Error("Invalid layout");
            }
            this.state.fields = layout.fields;
            this.state.layoutError = "";
        } catch {
            this.state.layoutError = _t("The saved layout could not be loaded. Please contact your administrator; it has not been overwritten.");
        }
    }

    async commit() {
        const value = JSON.stringify({ version: 1, fields: this.state.fields });
        this.lastLayout = value;
        await this.props.record.update({ [this.props.name]: value });
    }

    async loadPdf() {
        const generation = ++this.generation;
        this.pdfTask?.destroy();
        this.pdfTask = null;
        this.state.error = "";
        if (!this.hasPdf) {
            this.state.loading = false;
            return;
        }
        this.state.loading = true;
        try {
            await loadJS("/web/static/lib/pdfjs/build/pdf.js");
            if (generation !== this.generation) {
                return;
            }
            const pdfjs = globalThis.pdfjsLib;
            pdfjs.GlobalWorkerOptions.workerSrc = "/web/static/lib/pdfjs/build/pdf.worker.js";
            const pdfField = this.documentConfig.pdfField;
            const binary = this.props.record.data[pdfField];
            const source = isBinarySize(binary)
                ? { url: `/web/content?model=event.event&id=${this.props.record.resId}&field=${pdfField}&unique=${Date.now()}` }
                : { data: Uint8Array.from(atob(binary), (char) => char.charCodeAt(0)) };
            this.pdfTask = pdfjs.getDocument({ ...source, isEvalSupported: false });
            // Do not leave a password dialog hanging for encrypted documents.
            this.pdfTask.onPassword = () => this.pdfTask?.destroy();
            const pdf = await this.pdfTask.promise;
            if (generation !== this.generation) {
                return;
            }
            if (pdf.numPages !== 1) {
                throw new Error("Single-page PDF required");
            }
            const page = await pdf.getPage(1);
            if (generation !== this.generation || !this.canvas.el) {
                return;
            }
            const natural = page.getViewport({ scale: 1 });
            this.state.pageWidth = natural.width;
            this.state.pageHeight = natural.height;
            const viewport = page.getViewport({ scale: Math.min(2, 2000 / natural.width) });
            // Render off-screen: replacing a PDF during rendering cannot cause
            // two PDF.js tasks to draw on the same canvas.
            const canvas = document.createElement("canvas");
            canvas.width = Math.ceil(viewport.width);
            canvas.height = Math.ceil(viewport.height);
            await page.render({ canvasContext: canvas.getContext("2d"), viewport }).promise;
            if (generation !== this.generation || !this.canvas.el) {
                return;
            }
            this.canvas.el.width = canvas.width;
            this.canvas.el.height = canvas.height;
            this.canvas.el.getContext("2d").drawImage(canvas, 0, 0);
        } catch {
            if (generation === this.generation) {
                this.state.error = _t("Cannot preview this PDF. Upload a single-page PDF without password protection (maximum 20 MB).");
            }
        } finally {
            if (generation === this.generation) {
                this.state.loading = false;
            }
        }
    }

    async addField(name) {
        if (this.props.readonly || this.state.layoutError || this.state.fields.length >= 100) {
            return;
        }
        const field = {
            id: `field_${Date.now()}_${Math.random().toString(36).slice(2)}`,
            template: `{{${name}}}`,
            kind: name === "instructor_signature" ? "image" : "text",
            x: 15, y: Math.min(75, 20 + this.state.fields.length * 8),
            width: 70, height: name === "topics" ? 20 : 8,
            font_size: name === "company" ? 24 : 14,
            align: "center", bold: name === "company", color: "#000000",
        };
        if (field.kind === "image") {
            Object.assign(field, { x: 15, y: 75, width: 30, height: 10 });
        }
        this.state.fields.push(field);
        this.state.selectedId = field.id;
        await this.commit();
    }

    async deleteSelected() {
        if (this.props.readonly || !this.selected) {
            return;
        }
        this.state.fields = this.state.fields.filter((field) => field.id !== this.state.selectedId);
        this.state.selectedId = null;
        await this.commit();
    }

    async updateSelected(key, event) {
        const field = this.selected;
        if (this.props.readonly || !field) {
            return;
        }
        let value = event.target.type === "checkbox" ? event.target.checked : event.target.value;
        if (["x", "y", "width", "height", "font_size"].includes(key)) {
            value = Number(value);
            if (!Number.isFinite(value)) {
                return;
            }
            const limits = {
                x: [0, 100 - field.width], y: [0, 100 - field.height],
                width: [1, 100 - field.x], height: [1, 100 - field.y], font_size: [4, 96],
            };
            value = clamp(value, ...limits[key]);
        }
        field[key] = value;
        await this.commit();
    }

    fieldStyle(field) {
        const fontSize = field.font_size * this.state.stageWidth / this.state.pageWidth;
        return `left:${field.x}%;top:${field.y}%;width:${field.width}%;height:${field.height}%;font-size:${fontSize}px;text-align:${field.align};font-weight:${field.bold ? 700 : 400};color:${field.color};`;
    }

    signatureSource(field) {
        return field.kind === "image" && this.state.showValues
            ? this.state.values.instructor_signature || "" : "";
    }

    displayText(field) {
        if (!this.state.showValues) {
            return field.template;
        }
        return field.template.replace(/\{\{\s*(\w+)\s*\}\}/g, (whole, name) => this.state.values[name] ?? whole);
    }

    async toggleValues() {
        if (!this.state.showValues && this.props.record.resId) {
            this.state.values = await this.orm.call("event.event", this.documentConfig.previewMethod, [[this.props.record.resId]]);
        }
        this.state.showValues = !this.state.showValues;
    }

    async testPrint() {
        // Save first: the report must use the same uploaded background and
        // field positions the user currently sees, not the previous layout.
        if (!await this.props.record.save()) {
            return;
        }
        await this.action.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: this.documentConfig.reportName,
            context: { active_ids: [this.props.record.resId], active_model: "event.event" },
        });
    }

    startDrag(event, field, resize = false) {
        event.stopPropagation();
        this.state.selectedId = field.id;
        if (this.props.readonly || event.button !== 0 || this.drag) {
            return;
        }
        event.preventDefault();
        const rect = this.stage.el.getBoundingClientRect();
        this.drag = {
            field, resize, pointerId: event.pointerId, rect,
            clientX: event.clientX, clientY: event.clientY,
            x: field.x, y: field.y, width: field.width, height: field.height,
        };
        this.moveListener = (e) => this.moveDrag(e);
        this.endListener = (e) => this.endDrag(e);
        window.addEventListener("pointermove", this.moveListener, { passive: false });
        window.addEventListener("pointerup", this.endListener);
        window.addEventListener("pointercancel", this.endListener);
    }

    moveDrag(event) {
        const drag = this.drag;
        if (!drag || event.pointerId !== drag.pointerId) {
            return;
        }
        event.preventDefault();
        const dx = (event.clientX - drag.clientX) / drag.rect.width * 100;
        const dy = (event.clientY - drag.clientY) / drag.rect.height * 100;
        if (drag.resize) {
            drag.field.width = clamp(drag.width + dx, 1, 100 - drag.x);
            drag.field.height = clamp(drag.height + dy, 1, 100 - drag.y);
        } else {
            drag.field.x = clamp(drag.x + dx, 0, 100 - drag.width);
            drag.field.y = clamp(drag.y + dy, 0, 100 - drag.height);
        }
    }

    async endDrag(event) {
        if (!this.drag || event.pointerId !== this.drag.pointerId) {
            return;
        }
        this.removeDragListeners();
        await this.commit();
    }

    removeDragListeners() {
        window.removeEventListener("pointermove", this.moveListener);
        window.removeEventListener("pointerup", this.endListener);
        window.removeEventListener("pointercancel", this.endListener);
        this.drag = null;
    }

    async onFieldKeydown(event, field) {
        if (this.props.readonly) {
            return;
        }
        const directions = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
        if (!directions[event.key]) {
            return;
        }
        event.preventDefault();
        const [dx, dy] = directions[event.key];
        const step = event.shiftKey ? 1 : 0.1;
        field.x = clamp(field.x + dx * step, 0, 100 - field.width);
        field.y = clamp(field.y + dy * step, 0, 100 - field.height);
        await this.commit();
    }
}

registry.category("fields").add("certificate_pdf_designer", {
    component: CertificatePdfDesigner,
    supportedTypes: ["text"],
    fieldDependencies: [{ name: "certificate_pdf", type: "binary" }],
});

registry.category("fields").add("signup_sheet_pdf_designer", {
    component: CertificatePdfDesigner,
    supportedTypes: ["text"],
    extractProps: () => ({ documentType: "signup_sheet" }),
    fieldDependencies: [{ name: "signup_sheet_pdf", type: "binary" }],
});
