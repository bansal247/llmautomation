"""
product_editor.py  –  Full-featured PyQt5 Product Editor
Requires: PyQt5   (pip install PyQt5)
Usage:    python product_editor.py
          python product_editor.py --db /path/to/products.db
"""

import sys
import json
import os
import argparse
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QScrollArea, QPushButton,
    QCheckBox, QFrame, QSizePolicy, QMessageBox, QGroupBox,
    QPlainTextEdit, QSplitter, QListWidget, QListWidgetItem,
    QShortcut, QDialog, QDialogButtonBox, QToolButton, QStatusBar,
    QAbstractItemView
)
from PyQt5.QtGui import (
    QPixmap, QFont, QColor, QKeySequence, QSyntaxHighlighter,
    QTextCharFormat, QTextCursor, QPainter
)
from PyQt5.QtCore import Qt, QSize, QTimer, QRegExp, pyqtSignal

# ── DB import ─────────────────────────────────────────────────────────────────
try:
    from .db import ProductsDB
except ImportError as e:
    print(f"Failed to import ProductsDB: {e}")
    raise


# ═════════════════════════════════════════════════════════════════════════════
#  Design tokens
# ═════════════════════════════════════════════════════════════════════════════
C = {
    "bg":           "#0D0D10",
    "surface":      "#16161C",
    "surface2":     "#1E1E26",
    "surface3":     "#26262F",
    "border":       "#2A2A36",
    "border2":      "#383848",
    "accent":       "#7C6AFF",
    "accent_hover": "#9181FF",
    "accent_dim":   "#38306B",
    "ok":           "#3ECF8E",
    "warn":         "#F7A84A",
    "danger":       "#FF5E5E",
    "primary":      "#E8E6F4",
    "secondary":    "#9E9CB8",
    "muted":        "#5E5C72",
    "json_key":     "#7C6AFF",
    "json_str":     "#3ECF8E",
    "json_num":     "#F7A84A",
    "json_kw":      "#FF5E5E",
}

# ── Global stylesheet ─────────────────────────────────────────────────────────
QSS = f"""
* {{
    font-family: 'Inter', 'Segoe UI', 'SF Pro Display', sans-serif;
    font-size: 13px;
    color: {C['primary']};
}}
QMainWindow, QDialog {{
    background: {C['bg']};
}}
QWidget {{
    background: transparent;
}}

/* ── Scroll ── */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: {C['surface']};
    width: 5px;
    border-radius: 2px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C['border2']};
    border-radius: 2px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background: {C['accent']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {C['surface']};
    height: 5px;
    border-radius: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {C['border2']};
    border-radius: 2px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Inputs ── */
QLineEdit, QPlainTextEdit, QTextEdit {{
    background: {C['surface2']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    color: {C['primary']};
    padding: 7px 10px;
    selection-background-color: {C['accent_dim']};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {C['accent']};
    background: {C['surface3']};
}}
QLineEdit:disabled, QPlainTextEdit:disabled {{
    color: {C['muted']};
}}

/* ── Checkbox ── */
QCheckBox {{
    color: {C['primary']};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 17px; height: 17px;
    border: 2px solid {C['border2']};
    border-radius: 4px;
    background: {C['surface2']};
}}
QCheckBox::indicator:checked {{
    background: {C['accent']};
    border-color: {C['accent']};
}}
QCheckBox::indicator:hover {{
    border-color: {C['accent']};
}}

/* ── GroupBox ── */
QGroupBox {{
    background: {C['surface']};
    border: 1px solid {C['border']};
    border-radius: 10px;
    margin-top: 12px;
    padding: 14px 12px 12px 12px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: {C['muted']};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}}

/* ── List (sidebar) ── */
QListWidget {{
    background: {C['surface']};
    border: none;
    border-right: 1px solid {C['border']};
    outline: none;
}}
QListWidget::item {{
    padding: 10px 14px;
    border-bottom: 1px solid {C['border']};
    color: {C['secondary']};
}}
QListWidget::item:selected {{
    background: {C['accent_dim']};
    color: {C['primary']};
    border-left: 3px solid {C['accent']};
}}
QListWidget::item:hover:!selected {{
    background: {C['surface2']};
    color: {C['primary']};
}}

/* ── Splitter ── */
QSplitter::handle {{
    background: {C['border']};
    width: 1px;
}}

/* ── Status bar ── */
QStatusBar {{
    background: {C['surface']};
    border-top: 1px solid {C['border']};
    color: {C['muted']};
    font-size: 11px;
    padding: 0 12px;
}}
QStatusBar::item {{ border: none; }}

/* ── Tooltip ── */
QToolTip {{
    background: {C['surface3']};
    color: {C['primary']};
    border: 1px solid {C['border2']};
    border-radius: 4px;
    padding: 4px 8px;
}}
"""

BTN_PRIMARY = f"""
QPushButton {{
    background: {C['accent']};
    color: #fff;
    border: none;
    border-radius: 7px;
    padding: 9px 28px;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 0.01em;
}}
QPushButton:hover  {{ background: {C['accent_hover']}; }}
QPushButton:pressed {{ background: {C['accent_dim']}; }}
QPushButton:disabled {{ background: {C['border']}; color: {C['muted']}; }}
"""

BTN_GHOST = f"""
QPushButton {{
    background: transparent;
    color: {C['secondary']};
    border: 1px solid {C['border2']};
    border-radius: 7px;
    padding: 9px 20px;
    font-size: 13px;
}}
QPushButton:hover  {{ color: {C['primary']}; border-color: {C['secondary']}; }}
QPushButton:pressed {{ background: {C['surface2']}; }}
QPushButton:disabled {{ color: {C['muted']}; border-color: {C['border']}; }}
"""

BTN_DANGER = f"""
QPushButton {{
    background: transparent;
    color: {C['danger']};
    border: 1px solid {C['danger']};
    border-radius: 7px;
    padding: 9px 20px;
    font-size: 13px;
}}
QPushButton:hover  {{ background: rgba(255,94,94,0.12); }}
QPushButton:pressed {{ background: rgba(255,94,94,0.2); }}
"""

BTN_ICON = f"""
QToolButton {{
    background: transparent;
    border: none;
    color: {C['muted']};
    font-size: 14px;
    padding: 4px;
    border-radius: 4px;
}}
QToolButton:hover {{ color: {C['primary']}; background: {C['surface2']}; }}
"""

NAV_BTN = f"""
QPushButton {{
    background: {C['surface2']};
    color: {C['secondary']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
}}
QPushButton:hover {{ color: {C['primary']}; border-color: {C['accent']}; }}
QPushButton:disabled {{ color: {C['border']}; border-color: {C['border']}; }}
"""


# ═════════════════════════════════════════════════════════════════════════════
#  JSON syntax highlighter
# ═════════════════════════════════════════════════════════════════════════════
class JsonHighlighter(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        def fmt(color, bold=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Bold)
            return f

        self._rules = [
            (QRegExp(r'"[^"\\]*(?:\\.[^"\\]*)*"\s*:'), fmt(C['json_key'], bold=True)),
            (QRegExp(r':\s*"[^"\\]*(?:\\.[^"\\]*)*"'),  fmt(C['json_str'])),
            (QRegExp(r':\s*-?\d+(\.\d+)?'),             fmt(C['json_num'])),
            (QRegExp(r'\b(true|false|null)\b'),          fmt(C['json_kw'])),
        ]

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            idx = pattern.indexIn(text)
            while idx >= 0:
                length = pattern.matchedLength()
                self.setFormat(idx, length, fmt)
                idx = pattern.indexIn(text, idx + length)


# ═════════════════════════════════════════════════════════════════════════════
#  Image zoom dialog
# ═════════════════════════════════════════════════════════════════════════════
class ImageZoomDialog(QDialog):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Preview")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        self.setStyleSheet(f"background:{C['bg']};")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)

        lbl = QLabel()
        lbl.setAlignment(Qt.AlignCenter)
        if path and os.path.exists(path):
            pix = QPixmap(path)
            screen = QApplication.primaryScreen().availableGeometry()
            max_w = int(screen.width() * 0.75)
            max_h = int(screen.height() * 0.75)
            pix = pix.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl.setPixmap(pix)
            self.resize(pix.width() + 32, pix.height() + 80)
        else:
            lbl.setText("Image not found")
            lbl.setStyleSheet(f"color:{C['muted']};")

        path_lbl = QLabel(path or "—")
        path_lbl.setStyleSheet(f"color:{C['muted']}; font-size:10px;")
        path_lbl.setWordWrap(True)
        path_lbl.setAlignment(Qt.AlignCenter)

        close = QPushButton("Close")
        close.setStyleSheet(BTN_GHOST)
        close.clicked.connect(self.accept)

        lay.addWidget(lbl)
        lay.addWidget(path_lbl)
        lay.addWidget(close, alignment=Qt.AlignCenter)

        QShortcut(QKeySequence("Escape"), self, self.accept)


# ═════════════════════════════════════════════════════════════════════════════
#  Reusable widgets
# ═════════════════════════════════════════════════════════════════════════════
def mk_label(text, color=None, size=11, bold=False, wrap=False):
    lbl = QLabel(text)
    css = (f"color:{color or C['secondary']}; font-size:{size}px;"
           f" font-weight:{'700' if bold else '400'}; background:transparent;")
    lbl.setStyleSheet(css)
    if wrap:
        lbl.setWordWrap(True)
    return lbl


def mk_divider(vertical=False):
    line = QFrame()
    line.setFrameShape(QFrame.VLine if vertical else QFrame.HLine)
    line.setStyleSheet(f"color:{C['border']}; background:{C['border']};")
    line.setFixedHeight(1) if not vertical else line.setFixedWidth(1)
    return line


def mk_badge(text, color):
    lbl = QLabel(f"  {text}  ")
    lbl.setStyleSheet(
        f"background:rgba(0,0,0,0); color:{color}; border:1px solid {color};"
        f"border-radius:10px; font-size:10px; font-weight:600; padding:1px 2px;"
    )
    return lbl


class ClickableImageLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setCursor(Qt.PointingHandCursor)
        self.setAlignment(Qt.AlignCenter)
        self.setToolTip("Click to enlarge")

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()


class ImageCard(QWidget):
    def __init__(self, caption, parent=None):
        super().__init__(parent)
        self._path = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        # image area
        self.img = ClickableImageLabel()
        self.img.setStyleSheet(
            f"background:{C['surface2']}; border:1px solid {C['border']};"
            f"border-radius:8px; min-height:140px; color:{C['muted']}; font-size:12px;"
        )
        self.img.setMinimumHeight(140)
        self.img.clicked.connect(self._zoom)

        self.cap_lbl = mk_label(caption, color=C['muted'], size=10)
        self.cap_lbl.setAlignment(Qt.AlignCenter)
        self.path_lbl = mk_label("", color=C['muted'], size=9, wrap=True)
        self.path_lbl.setAlignment(Qt.AlignCenter)

        lay.addWidget(self.img)
        lay.addWidget(self.cap_lbl)
        lay.addWidget(self.path_lbl)

    def set_image(self, path, max_w=320, max_h=220):
        self._path = path
        if path and os.path.exists(path):
            pix = QPixmap(path)
            if not pix.isNull():
                pix = pix.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.img.setPixmap(pix)
                self.img.setToolTip(f"Click to enlarge · {path}")
                self.path_lbl.setText(os.path.basename(path))
                return
        self.img.setPixmap(QPixmap())
        self.img.setText("No image")
        self.path_lbl.setText(path or "")

    def _zoom(self):
        if self._path:
            dlg = ImageZoomDialog(self._path, self)
            dlg.exec_()


class LabeledField(QWidget):
    """Label + input widget with optional char counter."""

    def __init__(self, label_text, widget, char_limit=None, json_highlight=False):
        super().__init__()
        self.char_limit = char_limit
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)

        # header row
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        lbl = mk_label(label_text, size=11)
        hdr.addWidget(lbl)
        hdr.addStretch()

        if char_limit:
            self.counter = mk_label(f"0 / {char_limit}", color=C['muted'], size=10)
            hdr.addWidget(self.counter)
        else:
            self.counter = None

        lay.addLayout(hdr)
        lay.addWidget(widget)
        self.widget = widget

        if json_highlight and isinstance(widget, QPlainTextEdit):
            JsonHighlighter(widget.document())

        # connect counter
        if char_limit:
            if isinstance(widget, QPlainTextEdit):
                widget.textChanged.connect(self._update_counter)
            elif isinstance(widget, QLineEdit):
                widget.textChanged.connect(self._update_counter)

    def _update_counter(self):
        if isinstance(self.widget, QPlainTextEdit):
            n = len(self.widget.toPlainText())
        else:
            n = len(self.widget.text())
        self.counter.setText(f"{n} / {self.char_limit}")
        over = n > self.char_limit
        self.counter.setStyleSheet(
            f"color:{C['danger'] if over else C['muted']}; font-size:10px; background:transparent;"
        )


# ═════════════════════════════════════════════════════════════════════════════
#  Sidebar list item
# ═════════════════════════════════════════════════════════════════════════════
class SidebarItem(QListWidgetItem):
    def __init__(self, product):
        sku  = product.get("sku") or product.get("id", "?")
        title = product.get("title") or "Untitled"
        super().__init__(f"#{sku}  {title[:28]}{'…' if len(title) > 28 else ''}")
        self.product_id = product["id"]
        ready = product.get("ready_for_upload")
        self.setToolTip(f"SKU {sku} · {'Ready' if ready else 'Pending'}\n{title}")
        if ready:
            self.setForeground(QColor(C['ok']))


# ═════════════════════════════════════════════════════════════════════════════
#  Main editor panel (scrollable)
# ═════════════════════════════════════════════════════════════════════════════
class EditorPanel(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(scroll)

        inner = QWidget()
        scroll.setWidget(inner)
        self.lay = QVBoxLayout(inner)
        self.lay.setContentsMargins(20, 20, 20, 24)
        self.lay.setSpacing(14)

        self._build()

    def _build(self):
        L = self.lay

        # ── SKU / title header ─────────────────────────────────────────────
        hdr = QHBoxLayout()
        self.sku_lbl = mk_label("—", color=C['accent'], size=22, bold=True)
        self.shopify_badge = mk_badge("Shopify", C['ok'])
        self.shopify_badge.hide()
        self.ready_badge   = mk_badge("Ready",   C['accent'])
        self.ready_badge.hide()
        hdr.addWidget(self.sku_lbl)
        hdr.addWidget(self.shopify_badge)
        hdr.addWidget(self.ready_badge)
        hdr.addStretch()
        L.addLayout(hdr)

        # ── two-column body ────────────────────────────────────────────────
        body = QHBoxLayout()
        body.setSpacing(14)
        L.addLayout(body)

        left  = QVBoxLayout(); left.setSpacing(14)
        right = QVBoxLayout(); right.setSpacing(14)
        body.addLayout(left, 55)
        body.addLayout(right, 45)

        # ══ LEFT ══════════════════════════════════════════════════════════
        # Core content
        core = QGroupBox("Core Content")
        cl = QVBoxLayout(core); cl.setSpacing(10)

        self.f_title    = QLineEdit()
        self.f_subtitle = QLineEdit()
        self.f_desc_open = QPlainTextEdit(); self.f_desc_open.setFixedHeight(80)
        self.f_desc_bul  = QPlainTextEdit(); self.f_desc_bul.setFixedHeight(100)

        cl.addWidget(LabeledField("Title *", self.f_title))
        cl.addWidget(LabeledField("Subtitle", self.f_subtitle))
        cl.addWidget(LabeledField("Description — Opening", self.f_desc_open))
        cl.addWidget(LabeledField("Description — Bullets  (JSON array)", self.f_desc_bul,
                                  json_highlight=True))
        left.addWidget(core)

        # SEO
        seo = QGroupBox("SEO")
        sl = QVBoxLayout(seo); sl.setSpacing(10)

        self.f_meta_title = QLineEdit()
        self.f_meta_desc  = QPlainTextEdit(); self.f_meta_desc.setFixedHeight(72)
        self.f_alt_text   = QLineEdit()

        sl.addWidget(LabeledField("Meta Title", self.f_meta_title, char_limit=60))
        sl.addWidget(LabeledField("Meta Description", self.f_meta_desc, char_limit=160))
        sl.addWidget(LabeledField("Alt Text", self.f_alt_text, char_limit=120))
        left.addWidget(seo)

        # Product details
        det = QGroupBox("Product Details")
        dl = QVBoxLayout(det); dl.setSpacing(10)

        self.f_product_type = QLineEdit()
        self.f_price        = QLineEdit()
        self.f_variants     = QPlainTextEdit(); self.f_variants.setFixedHeight(80)
        self.f_product_tags = QPlainTextEdit(); self.f_product_tags.setFixedHeight(80)
        self.f_set_includes = QPlainTextEdit(); self.f_set_includes.setFixedHeight(80)

        row_pt = QHBoxLayout()
        row_pt.addWidget(LabeledField("Product Type", self.f_product_type))
        row_pt.addWidget(LabeledField("Price (£)", self.f_price))
        dl.addLayout(row_pt)
        dl.addWidget(LabeledField("Variants  (JSON array)", self.f_variants, json_highlight=True))
        dl.addWidget(LabeledField("Product Tags  (JSON array)", self.f_product_tags, json_highlight=True))
        dl.addWidget(LabeledField("Set Includes  (JSON array)", self.f_set_includes, json_highlight=True))
        left.addWidget(det)

        # ══ RIGHT ═════════════════════════════════════════════════════════
        # Images
        img_grp = QGroupBox("Images  (click to enlarge)")
        ig = QHBoxLayout(img_grp); ig.setSpacing(12)
        self.img_orig = ImageCard("Original")
        self.img_gen  = ImageCard("Generated")
        ig.addWidget(self.img_orig)
        ig.addWidget(self.img_gen)
        right.addWidget(img_grp)

        # Flags
        flag_grp = QGroupBox("Flags")
        fg = QVBoxLayout(flag_grp); fg.setSpacing(10)
        self.cb_ready      = QCheckBox("Ready for Upload")
        self.cb_regenerate = QCheckBox("Regenerate Image")

        for cb in (self.cb_ready, self.cb_regenerate):
            fg.addWidget(cb)

        fg.addWidget(mk_divider())

        # shopify read-only info
        self.lbl_shopify_pid = mk_label("Shopify Product ID: —", size=11)
        self.lbl_shopify_iid = mk_label("Shopify Image ID: —",   size=11)
        self.lbl_created     = mk_label("Created: —",             size=11)
        self.lbl_updated     = mk_label("Updated: —",             size=11)
        for w in (self.lbl_shopify_pid, self.lbl_shopify_iid,
                  self.lbl_created, self.lbl_updated):
            fg.addWidget(w)

        right.addWidget(flag_grp)
        right.addStretch()

        L.addStretch()

    # ── populate ─────────────────────────────────────────────────────────────
    def load(self, p: dict):
        sku = p.get("sku") or p.get("id", "—")
        self.sku_lbl.setText(f"SKU  #{sku}")

        uploaded = bool(p.get("uploaded_to_shopify"))
        ready    = bool(p.get("ready_for_upload"))
        self.shopify_badge.setVisible(uploaded)
        self.ready_badge.setVisible(ready)

        def sv(w, val):
            v = str(val) if val is not None else ""
            if isinstance(w, QPlainTextEdit):
                w.setPlainText(v)
            else:
                w.setText(v)

        sv(self.f_title,        p.get("title", ""))
        sv(self.f_subtitle,     p.get("subtitle", ""))
        sv(self.f_desc_open,    p.get("description", {}).get("opening", ""))
        sv(self.f_desc_bul,     json.dumps(p.get("description", {}).get("bullets", []), indent=2))
        sv(self.f_meta_title,   p.get("meta_title", ""))
        sv(self.f_meta_desc,    p.get("meta_description", ""))
        sv(self.f_alt_text,     p.get("alt_text", ""))
        sv(self.f_product_type, p.get("product_type", ""))
        sv(self.f_price,        "" if p.get("price") is None else p["price"])
        sv(self.f_variants,     json.dumps(p.get("variants", []),     indent=2))
        sv(self.f_product_tags, json.dumps(p.get("product_tags", []), indent=2))
        sv(self.f_set_includes, json.dumps(p.get("set_includes", []), indent=2))

        self.cb_ready.setChecked(ready)
        self.cb_regenerate.setChecked(bool(p.get("regenerate_image")))

        self.img_orig.set_image(p.get("original_image_path", ""))
        self.img_gen.set_image(p.get("generated_image_path", ""))

        self.lbl_shopify_pid.setText(f"Shopify Product ID: {p.get('shopify_product_id') or '—'}")
        self.lbl_shopify_iid.setText(f"Shopify Image ID:   {p.get('shopify_image_id') or '—'}")
        self.lbl_created.setText(f"Created:  {p.get('created_at') or '—'}")
        self.lbl_updated.setText(f"Updated:  {p.get('updated_at') or '—'}")

    # ── collect ───────────────────────────────────────────────────────────────
    def collect(self):
        """Return (updates_dict, error_message | None)."""
        def gv(w):
            if isinstance(w, QPlainTextEdit):
                return w.toPlainText().strip()
            return w.text().strip()

        def pj(w, name):
            raw = gv(w)
            if not raw:
                return [], None
            try:
                v = json.loads(raw)
                if not isinstance(v, list):
                    return None, f"'{name}' must be a JSON array, got {type(v).__name__}."
                return v, None
            except json.JSONDecodeError as e:
                return None, f"'{name}' — invalid JSON:\n{e}"

        bullets,  e1 = pj(self.f_desc_bul,  "Description Bullets")
        variants,  e2 = pj(self.f_variants,   "Variants")
        tags,      e3 = pj(self.f_product_tags,"Product Tags")
        set_inc,   e4 = pj(self.f_set_includes,"Set Includes")

        errors = [e for e in (e1, e2, e3, e4) if e]
        if errors:
            return None, "\n\n".join(errors)

        price_raw = gv(self.f_price)
        try:
            price = float(price_raw) if price_raw else None
        except ValueError:
            return None, "Price must be a number."

        title = gv(self.f_title)
        if not title:
            return None, "Title is required."

        return {
            "title":               title,
            "subtitle":            gv(self.f_subtitle) or None,
            "description_opening": gv(self.f_desc_open) or None,
            "description_bullets": bullets,
            "meta_title":          gv(self.f_meta_title) or None,
            "meta_description":    gv(self.f_meta_desc) or None,
            "alt_text":            gv(self.f_alt_text) or None,
            "product_type":        gv(self.f_product_type) or None,
            "price":               price,
            "variants":            variants,
            "product_tags":        tags,
            "set_includes":        set_inc,
            "ready_for_upload":    1 if self.cb_ready.isChecked() else 0,
            "regenerate_image":    1 if self.cb_regenerate.isChecked() else 0,
        }, None


# ═════════════════════════════════════════════════════════════════════════════
#  Main window
# ═════════════════════════════════════════════════════════════════════════════
class ProductEditorWindow(QMainWindow):
    def __init__(self, db_path=None):
        super().__init__()
        self.db = ProductsDB(db_path) if db_path else ProductsDB()
        self.products: list[dict] = []
        self.current_idx: int = 0

        self.setWindowTitle("Product Editor")
        self.setMinimumSize(1100, 700)
        self.resize(1340, 860)
        self.setStyleSheet(QSS)

        self._build_ui()
        self._load_all_products()
        self._setup_shortcuts()

    # ── layout ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── top bar ──
        top = QWidget()
        top.setFixedHeight(52)
        top.setStyleSheet(f"background:{C['surface']}; border-bottom:1px solid {C['border']};")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(20, 0, 20, 0)

        brand = mk_label("⬡  Product Editor", color=C['primary'], size=15, bold=True)

        self.counter_lbl = mk_label("", size=11)

        self.nav_prev = QPushButton("← Prev")
        self.nav_next = QPushButton("Next →")
        for b in (self.nav_prev, self.nav_next):
            b.setStyleSheet(NAV_BTN); b.setFixedHeight(30)
        self.nav_prev.clicked.connect(self._prev)
        self.nav_next.clicked.connect(self._next)

        self.reload_btn = QToolButton(); self.reload_btn.setText("↺")
        self.reload_btn.setStyleSheet(BTN_ICON)
        self.reload_btn.setToolTip("Reload all products from DB  (F5)")
        self.reload_btn.clicked.connect(self._load_all_products)

        tl.addWidget(brand)
        tl.addStretch()
        tl.addWidget(self.counter_lbl)
        tl.addSpacing(16)
        tl.addWidget(self.nav_prev)
        tl.addWidget(self.nav_next)
        tl.addSpacing(8)
        tl.addWidget(self.reload_btn)
        root.addWidget(top)

        # ── splitter: sidebar | editor ──
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)
        root.addWidget(self.splitter, 1)

        # sidebar
        side = QWidget()
        side.setStyleSheet(f"background:{C['surface']};")
        side.setMinimumWidth(180)
        side_l = QVBoxLayout(side)
        side_l.setContentsMargins(0, 0, 0, 0)
        side_l.setSpacing(0)

        side_hdr = QWidget()
        side_hdr.setFixedHeight(38)
        side_hdr.setStyleSheet(f"background:{C['surface2']}; border-bottom:1px solid {C['border']};")
        sh_l = QHBoxLayout(side_hdr); sh_l.setContentsMargins(12, 0, 12, 0)
        self.pending_lbl = mk_label("Pending", size=11, bold=True)
        sh_l.addWidget(self.pending_lbl)
        sh_l.addStretch()
        side_l.addWidget(side_hdr)

        self.sidebar = QListWidget()
        self.sidebar.setSelectionMode(QAbstractItemView.SingleSelection)
        self.sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sidebar.currentRowChanged.connect(self._sidebar_changed)
        side_l.addWidget(self.sidebar)

        self.splitter.addWidget(side)

        # editor
        self.editor = EditorPanel()
        self.splitter.addWidget(self.editor)
        self.splitter.setSizes([220, 900])

        # ── action bar ──
        action = QWidget()
        action.setFixedHeight(60)
        action.setStyleSheet(f"background:{C['surface']}; border-top:1px solid {C['border']};")
        al = QHBoxLayout(action)
        al.setContentsMargins(20, 0, 20, 0)
        al.setSpacing(10)

        self.feedback_lbl = mk_label("", size=12)

        self.mark_ready_btn = QPushButton("Mark Ready ✓")
        self.mark_ready_btn.setStyleSheet(BTN_GHOST)
        self.mark_ready_btn.setFixedHeight(38)
        self.mark_ready_btn.setToolTip("Toggle ready_for_upload without editing other fields  (R)")
        self.mark_ready_btn.clicked.connect(self._toggle_ready)

        self.skip_btn = QPushButton("Skip  →")
        self.skip_btn.setStyleSheet(BTN_GHOST)
        self.skip_btn.setFixedHeight(38)
        self.skip_btn.setToolTip("Move to next product without saving  (S)")
        self.skip_btn.clicked.connect(self._skip)

        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setStyleSheet(BTN_PRIMARY)
        self.save_btn.setFixedHeight(38)
        self.save_btn.setToolTip("Save all edits to DB  (Ctrl+S)")
        self.save_btn.clicked.connect(self._save)

        al.addWidget(self.feedback_lbl)
        al.addStretch()
        al.addWidget(self.mark_ready_btn)
        al.addWidget(self.skip_btn)
        al.addWidget(self.save_btn)
        root.addWidget(action)

        # status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

    # ── shortcuts ─────────────────────────────────────────────────────────────
    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+S"), self, self._save)
        QShortcut(QKeySequence("Ctrl+Right"), self, self._next)
        QShortcut(QKeySequence("Ctrl+Left"),  self, self._prev)
        QShortcut(QKeySequence("S"), self, self._skip)
        QShortcut(QKeySequence("R"), self, self._toggle_ready)
        QShortcut(QKeySequence("F5"), self, self._load_all_products)

    # ── data ──────────────────────────────────────────────────────────────────
    def _load_all_products(self):
        self.products = self.db.get_pending_products()
        self.sidebar.blockSignals(True)
        self.sidebar.clear()
        for p in self.products:
            self.sidebar.addItem(SidebarItem(p))
        self.sidebar.blockSignals(False)

        n = len(self.products)
        self.pending_lbl.setText(f"Pending  ({n})")
        self.status.showMessage(f"Loaded {n} pending products")

        if self.products:
            self.current_idx = 0
            self.sidebar.setCurrentRow(0)
            self._refresh_view()
        else:
            self.editor.sku_lbl.setText("No pending products")
            self._set_feedback("No products found", C['muted'])

    def _refresh_view(self):
        if not self.products:
            return
        n = len(self.products)
        self.counter_lbl.setText(f"{self.current_idx + 1} / {n}")
        self.nav_prev.setEnabled(self.current_idx > 0)
        self.nav_next.setEnabled(self.current_idx < n - 1)
        self.editor.load(self.products[self.current_idx])

        # sync sidebar without triggering signal
        self.sidebar.blockSignals(True)
        self.sidebar.setCurrentRow(self.current_idx)
        self.sidebar.blockSignals(False)

    def _sidebar_changed(self, row):
        if 0 <= row < len(self.products):
            self.current_idx = row
            self._refresh_view()
            self._clear_feedback()

    # ── navigation ────────────────────────────────────────────────────────────
    def _prev(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self._refresh_view()
            self._clear_feedback()

    def _next(self):
        if self.current_idx < len(self.products) - 1:
            self.current_idx += 1
            self._refresh_view()
            self._clear_feedback()

    def _skip(self):
        self._set_feedback("Skipped", C['muted'])
        if self.current_idx < len(self.products) - 1:
            self.current_idx += 1
            self._refresh_view()
        else:
            self.status.showMessage("Already at last product")

    # ── actions ───────────────────────────────────────────────────────────────
    def _save(self):
        if not self.products:
            return
        p = self.products[self.current_idx]
        updates, err = self.editor.collect()
        if err:
            QMessageBox.warning(self, "Validation Error", err)
            return

        try:
            self.db.update_product(p["id"], updates)
        except Exception as exc:
            QMessageBox.critical(self, "DB Error", str(exc))
            return

        # update local cache
        p.update(updates)
        p.setdefault("description", {})
        p["description"]["opening"] = updates["description_opening"]
        p["description"]["bullets"] = updates["description_bullets"]

        # refresh sidebar item colour
        item = self.sidebar.item(self.current_idx)
        if item:
            if updates.get("ready_for_upload"):
                item.setForeground(QColor(C['ok']))
            else:
                item.setForeground(QColor(C['secondary']))

        self._set_feedback("✓  Saved", C['ok'])
        self.status.showMessage(f"Saved SKU #{p.get('sku') or p['id']}")

        # auto-advance after short delay
        QTimer.singleShot(400, self._advance_after_save)

    def _advance_after_save(self):
        if self.current_idx < len(self.products) - 1:
            self.current_idx += 1
            self._refresh_view()

    def _toggle_ready(self):
        if not self.products:
            return
        p = self.products[self.current_idx]
        new_val = not bool(p.get("ready_for_upload"))
        try:
            self.db.mark_ready_for_upload(p["id"], new_val)
        except Exception as exc:
            QMessageBox.critical(self, "DB Error", str(exc))
            return

        p["ready_for_upload"] = 1 if new_val else 0
        # update checkbox without reloading full form
        self.editor.cb_ready.setChecked(new_val)
        self.editor.ready_badge.setVisible(new_val)

        item = self.sidebar.item(self.current_idx)
        if item:
            item.setForeground(QColor(C['ok'] if new_val else C['secondary']))

        msg = "Ready for upload ✓" if new_val else "Marked as pending"
        self._set_feedback(msg, C['ok'] if new_val else C['warn'])
        self.status.showMessage(msg)

    # ── feedback ──────────────────────────────────────────────────────────────
    def _set_feedback(self, msg, color):
        self.feedback_lbl.setText(msg)
        self.feedback_lbl.setStyleSheet(
            f"color:{color}; font-size:12px; font-weight:600; background:transparent;"
        )
        QTimer.singleShot(4000, self._clear_feedback)

    def _clear_feedback(self):
        self.feedback_lbl.setText("")


# ═════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Product Editor UI")
    parser.add_argument("--db", default=None, help="Path to products.db")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = ProductEditorWindow(db_path=args.db)
    win.show()
    sys.exit(app.exec_())