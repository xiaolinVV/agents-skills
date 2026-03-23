#!/usr/bin/env python3
"""Build a deterministic quotation workbook without third-party dependencies.

Input: JSON payload described in references/output-contract.md
Output: .xlsx workbook with one client-facing sheet:
  - 报价表
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import unicodedata
import zipfile
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Sequence
from xml.sax.saxutils import escape

APP_NAME = "software-quote-builder"
STYLE_HEADER = 1
STYLE_BODY_TEXT = 2
STYLE_BODY_NUMBER = 3
STYLE_BODY_CURRENCY = 4
STYLE_SUMMARY_LABEL = 5
STYLE_SUMMARY_NUMBER = 6
STYLE_SUMMARY_CURRENCY = 7
STYLE_TITLE = 8
STYLE_META_LABEL = 9
STYLE_META_VALUE = 10
STYLE_META_CURRENCY = 11
STYLE_SECTION = 12
STYLE_NOTE = 13
STYLE_ALT_TEXT = 14
STYLE_ALT_NUMBER = 15
STYLE_ALT_CURRENCY = 16

DEFAULT_DATA_ROW_HEIGHT = 24
ROW_LINE_HEIGHT = 16
MAX_DATA_ROW_HEIGHT = 180
DEFAULT_SPECIAL_NOTES = [
    "仅为软件功能开发费用。",
    "默认包含自项目验收之日起一年的维护期。",
    "服务器及第三方服务相关费用由客户自行支付。",
]


@dataclass
class QuoteItem:
    seq: int
    module_l1: str
    module_l2: str
    feature: str
    description: str
    source_ref: str
    estimated_days: float
    note: str


@dataclass
class PricingResult:
    raw_days: float
    raw_amount: float
    final_days: float
    final_amount: float
    reason: str


@dataclass
class SheetSpec:
    name: str
    xml: str


def qround(value: float, step: float) -> float:
    if step <= 0:
        raise ValueError("rounding step must be positive")
    dec_value = Decimal(str(value))
    dec_step = Decimal(str(step))
    units = (dec_value / dec_step).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return float(units * dec_step)


def ceil_to_step(value: float, step: float) -> float:
    return math.ceil(value / step) * step


def floor_to_step(value: float, step: float) -> float:
    return math.floor(value / step) * step


def distribute_values(raw_values: Sequence[float], target_total: float, step: float) -> List[float]:
    if not raw_values:
        return []
    if target_total < 0:
        raise ValueError("target total cannot be negative")

    positive = [i for i, v in enumerate(raw_values) if v > 0]
    if not positive:
        return [0.0 for _ in raw_values]

    unit_count = int(round(target_total / step))
    if not math.isclose(unit_count * step, target_total, rel_tol=0, abs_tol=1e-9):
        raise ValueError("target total must align with rounding step")

    min_one = unit_count >= len(positive)
    base_units = [0] * len(raw_values)
    if min_one:
        for idx in positive:
            base_units[idx] = 1
    remaining_units = unit_count - sum(base_units)

    total_weight = sum(raw_values)
    if total_weight <= 0:
        return [0.0 for _ in raw_values]

    exact_extra = [raw / total_weight * remaining_units for raw in raw_values]
    extra_units = [math.floor(v) for v in exact_extra]
    fractions = [(idx, exact_extra[idx] - extra_units[idx]) for idx in range(len(raw_values))]
    fractions.sort(key=lambda pair: (pair[1], raw_values[pair[0]], -pair[0]), reverse=True)

    drift = remaining_units - sum(extra_units)
    for idx, _ in fractions[:drift]:
        extra_units[idx] += 1

    return [(base_units[i] + extra_units[i]) * step for i in range(len(raw_values))]


def normalize_items(payload: Dict[str, object]) -> List[QuoteItem]:
    raw_items = payload.get("items") or []
    items: List[QuoteItem] = []
    for idx, raw in enumerate(raw_items, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"item {idx} must be an object")
        items.append(
            QuoteItem(
                seq=int(raw.get("seq") or idx),
                module_l1=str(raw.get("module_l1") or "").strip(),
                module_l2=str(raw.get("module_l2") or "").strip(),
                feature=str(raw.get("feature") or "").strip(),
                description=str(raw.get("description") or "").strip(),
                source_ref=str(raw.get("source_ref") or "").strip(),
                estimated_days=float(raw.get("estimated_days") or 0),
                note=str(raw.get("note") or "").strip(),
            )
        )
    return items


def values_already_usable(values: Sequence[float], total: float, step: float) -> bool:
    if not math.isclose(sum(values), total, rel_tol=0, abs_tol=1e-9):
        return False
    for value in values:
        if value < 0:
            return False
        scaled = value / step
        if not math.isclose(scaled, round(scaled), rel_tol=0, abs_tol=1e-9):
            return False
    return True


def apply_budget_rules(payload: Dict[str, object], items: List[QuoteItem]) -> PricingResult:
    rate = float(payload.get("day_rate", 800) or 800)
    tol_pct = float(payload.get("tolerance_pct", 10) or 10)
    step = float(payload.get("rounding_unit", 1) or 1)
    target_amount = payload.get("target_amount")

    raw_days = sum(item.estimated_days for item in items)
    raw_amount = raw_days * rate

    if not items:
        return PricingResult(raw_days, raw_amount, 0.0, 0.0, "no_items")

    if target_amount in (None, ""):
        rounded_days = qround(raw_days, step)
        raw_values = [item.estimated_days for item in items]
        if values_already_usable(raw_values, rounded_days, step):
            return PricingResult(raw_days, raw_amount, rounded_days, rounded_days * rate, "rounded_without_target")
        adjusted = distribute_values(raw_values, rounded_days, step)
        for item, value in zip(items, adjusted):
            item.estimated_days = value
        return PricingResult(raw_days, raw_amount, rounded_days, rounded_days * rate, "rounded_without_target")

    target_amount = float(target_amount)
    lower_amount = target_amount * (1 - tol_pct / 100.0)
    upper_amount = target_amount * (1 + tol_pct / 100.0)

    min_days = ceil_to_step(lower_amount / rate, step)
    max_days = floor_to_step(upper_amount / rate, step)
    if min_days > max_days:
        day_guess = qround(target_amount / rate, step)
        min_days = max_days = day_guess

    rounded_raw_days = qround(raw_days, step)
    rounded_raw_amount = rounded_raw_days * rate

    if lower_amount <= rounded_raw_amount <= upper_amount:
        final_days = rounded_raw_days
        reason = "within_tolerance"
    elif raw_amount < lower_amount:
        final_days = min_days
        reason = "scaled_up_to_lower_bound"
    else:
        final_days = max_days
        reason = "scaled_down_to_upper_bound"

    raw_values = [item.estimated_days for item in items]
    if not values_already_usable(raw_values, final_days, step):
        adjusted = distribute_values(raw_values, final_days, step)
        for item, value in zip(items, adjusted):
            item.estimated_days = value

    final_days = sum(item.estimated_days for item in items)
    final_amount = final_days * rate

    if lower_amount <= final_amount <= upper_amount:
        return PricingResult(raw_days, raw_amount, final_days, final_amount, reason)

    return PricingResult(raw_days, raw_amount, final_days, final_amount, f"{reason}_nearest_feasible")


def project_title(payload: Dict[str, object]) -> str:
    name = str(payload.get("project_name") or "").strip()
    return f"{name}功能清单报价表" if name else "功能清单报价表"


def payload_bool(payload: Dict[str, object], key: str, default: bool = False) -> bool:
    value = payload.get(key, default)
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def normalized_notes_list(raw_notes: object) -> List[str]:
    if raw_notes is None:
        return []
    if isinstance(raw_notes, list):
        values = raw_notes
    else:
        values = [raw_notes]

    notes: List[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in notes:
            notes.append(text)
    return notes


def resolved_special_notes(payload: Dict[str, object]) -> List[str]:
    if not payload_bool(payload, "special_notes_enabled", default=False):
        return []

    merge_mode = str(payload.get("special_notes_merge") or "append").strip().lower()
    custom_notes = normalized_notes_list(payload.get("special_notes"))
    if merge_mode == "replace" and custom_notes:
        return custom_notes

    return normalized_notes_list(DEFAULT_SPECIAL_NOTES + custom_notes)


def display_width(text: str) -> int:
    width = 0
    for ch in text:
        if ch == "\t":
            width += 4
        elif ch in "\r\n":
            continue
        elif unicodedata.east_asian_width(ch) in {"F", "W"}:
            width += 2
        else:
            width += 1
    return width


def wrapped_line_count(text: str, column_width: int) -> int:
    if column_width <= 0:
        return 1
    if not text:
        return 1

    logical_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    total_lines = 0
    for logical_line in logical_lines:
        line_width = display_width(logical_line)
        total_lines += max(1, math.ceil(line_width / column_width))
    return max(total_lines, 1)


def row_height_for_cells(cells: Sequence[tuple[str, int]]) -> int:
    max_lines = 1
    for text, column_width in cells:
        max_lines = max(max_lines, wrapped_line_count(text, column_width))
    return min(MAX_DATA_ROW_HEIGHT, max(DEFAULT_DATA_ROW_HEIGHT, 8 + max_lines * ROW_LINE_HEIGHT))


def xml_text_cell(ref: str, value: str, style_id: int) -> str:
    if value is None:
        value = ""
    return (
        f'<c r="{ref}" s="{style_id}" t="inlineStr">'
        f'<is><t xml:space="preserve">{escape(str(value))}</t></is></c>'
    )


def xml_number_cell(ref: str, value: float, style_id: int) -> str:
    if int(value) == value:
        value_text = str(int(value))
    else:
        value_text = f"{value:.6f}".rstrip("0").rstrip(".")
    return f'<c r="{ref}" s="{style_id}"><v>{value_text}</v></c>'


def xml_formula_cell(ref: str, formula: str, cached_value: float, style_id: int) -> str:
    if int(cached_value) == cached_value:
        value_text = str(int(cached_value))
    else:
        value_text = f"{cached_value:.6f}".rstrip("0").rstrip(".")
    return f'<c r="{ref}" s="{style_id}"><f>{escape(formula)}</f><v>{value_text}</v></c>'


def col_letter(index: int) -> str:
    if index < 1:
        raise ValueError("column index must be >= 1")
    result = []
    while index:
        index, remainder = divmod(index - 1, 26)
        result.append(chr(65 + remainder))
    return "".join(reversed(result))


def make_row_xml(row_num: int, cells: Sequence[str], height: int | None = None) -> str:
    attrs = [f'r="{row_num}"']
    if height:
        attrs.append(f'ht="{height}"')
        attrs.append('customHeight="1"')
    return f'<row {" ".join(attrs)}>{"".join(cells)}</row>'


def append_special_notes_block(
    rows: List[str],
    merges: List[str],
    widths: Sequence[int],
    last_col: str,
    start_row: int,
    notes: Sequence[str],
) -> int:
    if not notes:
        return start_row

    merged_width = max(sum(widths), 20)
    section_row = start_row
    merges.append(f"A{section_row}:{last_col}{section_row}")
    rows.append(make_row_xml(section_row, [xml_text_cell(f"A{section_row}", "特殊说明", STYLE_SECTION)], height=24))

    for offset, note in enumerate(notes, start=1):
        row_num = section_row + offset
        note_text = f"{offset}. {note}"
        merges.append(f"A{row_num}:{last_col}{row_num}")
        note_height = row_height_for_cells([(note_text, merged_width)])
        rows.append(make_row_xml(row_num, [xml_text_cell(f"A{row_num}", note_text, STYLE_NOTE)], height=note_height))

    return section_row + len(notes) + 1


def quote_sheet_template(payload: Dict[str, object], items: List[QuoteItem], rate: float) -> SheetSpec:
    headers = [
        "序号",
        "一级模块",
        "二级模块",
        "功能点",
        "功能说明",
        "预估工时（人天）",
        "单价（元/人天）",
        "小计（元）",
        "备注",
    ]
    widths = [8, 16, 16, 24, 48, 16, 16, 18, 28]
    last_col = col_letter(len(headers))
    merges = [f"A1:{last_col}1"]
    rows: List[str] = []

    rows.append(make_row_xml(1, [xml_text_cell("A1", project_title(payload), STYLE_TITLE)], height=30))
    rows.append(make_row_xml(2, [xml_text_cell(f"{col_letter(i)}2", header, STYLE_HEADER) for i, header in enumerate(headers, start=1)], height=24))

    data_start_row = 3
    for offset, item in enumerate(items):
        row_num = data_start_row + offset
        note = item.note or item.source_ref
        alt = offset % 2 == 1
        text_style = STYLE_ALT_TEXT if alt else STYLE_BODY_TEXT
        number_style = STYLE_ALT_NUMBER if alt else STYLE_BODY_NUMBER
        currency_style = STYLE_ALT_CURRENCY if alt else STYLE_BODY_CURRENCY
        line_total = item.estimated_days * rate
        cells = [
            xml_number_cell(f"A{row_num}", item.seq, number_style),
            xml_text_cell(f"B{row_num}", item.module_l1, text_style),
            xml_text_cell(f"C{row_num}", item.module_l2, text_style),
            xml_text_cell(f"D{row_num}", item.feature, text_style),
            xml_text_cell(f"E{row_num}", item.description, text_style),
            xml_number_cell(f"F{row_num}", item.estimated_days, number_style),
            xml_number_cell(f"G{row_num}", rate, currency_style),
            xml_formula_cell(f"H{row_num}", f"F{row_num}*G{row_num}", line_total, currency_style),
            xml_text_cell(f"I{row_num}", note, text_style),
        ]
        wrapped_cells = [
            (item.module_l1, widths[1]),
            (item.module_l2, widths[2]),
            (item.feature, widths[3]),
            (item.description, widths[4]),
            (note, widths[8]),
        ]
        rows.append(make_row_xml(row_num, cells, height=row_height_for_cells(wrapped_cells)))

    sum_row = data_start_row + len(items)
    merges.append(f"A{sum_row}:E{sum_row}")
    if items:
        days_formula = f"SUM(F{data_start_row}:F{sum_row - 1})"
        amount_formula = f"SUM(H{data_start_row}:H{sum_row - 1})"
        days_value = sum(item.estimated_days for item in items)
        amount_value = days_value * rate
    else:
        days_formula = "0"
        amount_formula = "0"
        days_value = 0.0
        amount_value = 0.0
    summary_cells = [
        xml_text_cell(f"A{sum_row}", "合计", STYLE_SUMMARY_LABEL),
        xml_formula_cell(f"F{sum_row}", days_formula, days_value, STYLE_SUMMARY_NUMBER),
        xml_text_cell(f"G{sum_row}", "", STYLE_SUMMARY_LABEL),
        xml_formula_cell(f"H{sum_row}", amount_formula, amount_value, STYLE_SUMMARY_CURRENCY),
        xml_text_cell(f"I{sum_row}", "", STYLE_SUMMARY_LABEL),
    ]
    rows.append(make_row_xml(sum_row, summary_cells, height=24))
    append_special_notes_block(
        rows=rows,
        merges=merges,
        widths=widths,
        last_col=last_col,
        start_row=sum_row + 1,
        notes=resolved_special_notes(payload),
    )

    xml = worksheet_xml(
        rows,
        widths,
        freeze_row=2,
        freeze_col=0,
        merges=merges,
        auto_filter_ref=f"A2:{last_col}2",
        active_cell="A3",
    )
    return SheetSpec(name="报价表", xml=xml)


def quote_sheet_reuse(payload: Dict[str, object], items: List[QuoteItem], rate: float) -> SheetSpec:
    base_columns = payload.get("base_columns")
    base_rows = payload.get("base_rows")
    if not isinstance(base_columns, list) or not isinstance(base_rows, list):
        raise ValueError("reuse mode requires base_columns and base_rows")
    if len(base_rows) != len(items):
        raise ValueError("reuse mode requires len(base_rows) == len(items)")

    headers = [str(col) for col in base_columns] + ["预估工时（人天）", "单价（元/人天）", "小计（元）"]
    widths = [18] * len(headers)
    if len(widths) >= 3:
        widths[-3:] = [16, 16, 18]
    last_col = col_letter(len(headers))
    merges = [f"A1:{last_col}1"]
    rows: List[str] = []

    rows.append(make_row_xml(1, [xml_text_cell("A1", project_title(payload), STYLE_TITLE)], height=30))
    rows.append(make_row_xml(2, [xml_text_cell(f"{col_letter(i)}2", header, STYLE_HEADER) for i, header in enumerate(headers, start=1)], height=24))

    quote_days_col = len(base_columns) + 1
    quote_rate_col = len(base_columns) + 2
    quote_total_col = len(base_columns) + 3
    data_start_row = 3

    for offset, (base_row, item) in enumerate(zip(base_rows, items)):
        if not isinstance(base_row, list):
            raise ValueError("each base_rows entry must be a list")
        row_num = data_start_row + offset
        alt = offset % 2 == 1
        text_style = STYLE_ALT_TEXT if alt else STYLE_BODY_TEXT
        number_style = STYLE_ALT_NUMBER if alt else STYLE_BODY_NUMBER
        currency_style = STYLE_ALT_CURRENCY if alt else STYLE_BODY_CURRENCY

        cells: List[str] = []
        wrapped_cells: List[tuple[str, int]] = []
        for col_num, value in enumerate(base_row, start=1):
            ref = f"{col_letter(col_num)}{row_num}"
            if isinstance(value, (int, float)):
                cells.append(xml_number_cell(ref, float(value), number_style))
            else:
                text_value = str(value)
                wrapped_cells.append((text_value, widths[col_num - 1]))
                cells.append(xml_text_cell(ref, text_value, text_style))

        line_total = item.estimated_days * rate
        cells.extend(
            [
                xml_number_cell(f"{col_letter(quote_days_col)}{row_num}", item.estimated_days, number_style),
                xml_number_cell(f"{col_letter(quote_rate_col)}{row_num}", rate, currency_style),
                xml_formula_cell(
                    f"{col_letter(quote_total_col)}{row_num}",
                    f"{col_letter(quote_days_col)}{row_num}*{col_letter(quote_rate_col)}{row_num}",
                    line_total,
                    currency_style,
                ),
            ]
        )
        rows.append(make_row_xml(row_num, cells, height=row_height_for_cells(wrapped_cells)))

    sum_row = data_start_row + len(base_rows)
    label_end_col = max(1, quote_days_col - 1)
    if label_end_col > 1:
        merges.append(f"A{sum_row}:{col_letter(label_end_col)}{sum_row}")

    if base_rows:
        days_col = col_letter(quote_days_col)
        rate_col = col_letter(quote_rate_col)
        total_col = col_letter(quote_total_col)
        days_formula = f"SUM({days_col}{data_start_row}:{days_col}{sum_row - 1})"
        amount_formula = f"SUM({total_col}{data_start_row}:{total_col}{sum_row - 1})"
        days_value = sum(item.estimated_days for item in items)
        amount_value = days_value * rate
    else:
        days_col = col_letter(quote_days_col)
        rate_col = col_letter(quote_rate_col)
        total_col = col_letter(quote_total_col)
        days_formula = "0"
        amount_formula = "0"
        days_value = 0.0
        amount_value = 0.0

    summary_cells = [xml_text_cell(f"A{sum_row}", "合计", STYLE_SUMMARY_LABEL)]
    summary_cells.append(xml_formula_cell(f"{days_col}{sum_row}", days_formula, days_value, STYLE_SUMMARY_NUMBER))
    summary_cells.append(xml_text_cell(f"{rate_col}{sum_row}", "", STYLE_SUMMARY_LABEL))
    summary_cells.append(xml_formula_cell(f"{total_col}{sum_row}", amount_formula, amount_value, STYLE_SUMMARY_CURRENCY))
    rows.append(make_row_xml(sum_row, summary_cells, height=24))
    append_special_notes_block(
        rows=rows,
        merges=merges,
        widths=widths,
        last_col=last_col,
        start_row=sum_row + 1,
        notes=resolved_special_notes(payload),
    )

    xml = worksheet_xml(
        rows,
        widths,
        freeze_row=2,
        freeze_col=0,
        merges=merges,
        auto_filter_ref=f"A2:{last_col}2",
        active_cell="A3",
    )
    return SheetSpec(name="报价表", xml=xml)


def worksheet_xml(
    rows: Sequence[str],
    widths: Sequence[int],
    freeze_row: int,
    freeze_col: int,
    merges: Sequence[str] | None = None,
    auto_filter_ref: str | None = None,
    active_cell: str | None = None,
) -> str:
    max_col = len(widths) or 1
    max_row = len(rows) or 1
    dim = f"A1:{col_letter(max_col)}{max_row}"
    pane = ""
    selected = active_cell or (f"A{freeze_row + 1}" if freeze_row else "A1")
    selection = f'<selection pane="bottomLeft" activeCell="{selected}" sqref="{selected}"/>' if (freeze_row or freeze_col) else f'<selection activeCell="{selected}" sqref="{selected}"/>'
    if freeze_row or freeze_col:
        x_split = str(freeze_col) if freeze_col else "0"
        y_split = str(freeze_row) if freeze_row else "0"
        top_left = f"{col_letter(freeze_col + 1)}{freeze_row + 1}"
        pane = (
            f'<pane xSplit="{x_split}" ySplit="{y_split}" topLeftCell="{top_left}" '
            'activePane="bottomLeft" state="frozen"/>'
        )

    cols_xml = "".join(
        f'<col min="{idx}" max="{idx}" width="{width}" customWidth="1"/>'
        for idx, width in enumerate(widths, start=1)
    )
    merge_xml = ""
    if merges:
        merge_xml = f'<mergeCells count="{len(merges)}">' + "".join(f'<mergeCell ref="{ref}"/>' for ref in merges) + "</mergeCells>"
    auto_filter_xml = f'<autoFilter ref="{auto_filter_ref}"/>' if auto_filter_ref else ""

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="{dim}"/>'
        f'<sheetViews><sheetView workbookViewId="0" showGridLines="0">{pane}{selection}</sheetView></sheetViews>'
        '<sheetFormatPr defaultRowHeight="20"/>'
        f'<cols>{cols_xml}</cols>'
        f'<sheetData>{"".join(rows)}</sheetData>'
        f'{auto_filter_xml}{merge_xml}'
        '<pageMargins left="0.3" right="0.3" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
        '</worksheet>'
    )


def workbook_xml(sheet_names: Sequence[str]) -> str:
    sheets = "".join(
        f'<sheet name="{escape(name)}" sheetId="{idx}" r:id="rId{idx}"/>'
        for idx, name in enumerate(sheet_names, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<bookViews><workbookView xWindow="240" yWindow="120" windowWidth="18000" windowHeight="9800"/></bookViews>'
        f'<sheets>{sheets}</sheets>'
        '<calcPr calcId="171027" fullCalcOnLoad="1" forceFullCalc="1"/>'
        '</workbook>'
    )


def workbook_rels(sheet_count: int) -> str:
    rels = [
        f'<Relationship Id="rId{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{idx}.xml"/>'
        for idx in range(1, sheet_count + 1)
    ]
    rels.append('<Relationship Id="rId99" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{"".join(rels)}</Relationships>'
    )


def root_rels() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        '</Relationships>'
    )


def content_types(sheet_count: int) -> str:
    overrides = [
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    overrides.extend(
        f'<Override PartName="/xl/worksheets/sheet{idx}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for idx in range(1, sheet_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f'{"".join(overrides)}</Types>'
    )


def styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<numFmts count="1"><numFmt numFmtId="164" formatCode="¥#,##0"/></numFmts>'
        '<fonts count="4">'
        '<font><sz val="11"/><color rgb="FF000000"/><name val="Calibri"/><family val="2"/></font>'
        '<font><b/><sz val="11"/><color rgb="FF000000"/><name val="Calibri"/><family val="2"/></font>'
        '<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/><family val="2"/></font>'
        '<font><b/><sz val="16"/><color rgb="FFFFFFFF"/><name val="Calibri"/><family val="2"/></font>'
        '</fonts>'
        '<fills count="6">'
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFD9EAF7"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFF7FBFF"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFF3F6FA"/><bgColor indexed="64"/></patternFill></fill>'
        '</fills>'
        '<borders count="2">'
        '<border><left/><right/><top/><bottom/><diagonal/></border>'
        '<border><left style="thin"><color rgb="FFD0D7DE"/></left><right style="thin"><color rgb="FFD0D7DE"/></right><top style="thin"><color rgb="FFD0D7DE"/></top><bottom style="thin"><color rgb="FFD0D7DE"/></bottom><diagonal/></border>'
        '</borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="17">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="2" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
        '<xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="2" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="2" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
        '<xf numFmtId="164" fontId="2" fillId="2" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="3" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="1" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="5" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="164" fontId="1" fillId="5" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="2" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="5" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
        '<xf numFmtId="164" fontId="0" fillId="4" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
        '</cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )


def app_xml(sheet_names: Sequence[str]) -> str:
    titles = "".join(f"<vt:lpstr>{escape(name)}</vt:lpstr>" for name in sheet_names)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        f'<Application>{APP_NAME}</Application><TitlesOfParts><vt:vector size="{len(sheet_names)}" baseType="lpstr">{titles}</vt:vector></TitlesOfParts>'
        '</Properties>'
    )


def core_xml() -> str:
    stamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f'<dc:creator>{APP_NAME}</dc:creator><cp:lastModifiedBy>{APP_NAME}</cp:lastModifiedBy>'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{stamp}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{stamp}</dcterms:modified>'
        '</cp:coreProperties>'
    )


def write_workbook(output_path: Path, sheets: Sequence[SheetSpec]) -> None:
    sheet_names = [sheet.name for sheet in sheets]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types(len(sheets)))
        zf.writestr("_rels/.rels", root_rels())
        zf.writestr("docProps/app.xml", app_xml(sheet_names))
        zf.writestr("docProps/core.xml", core_xml())
        zf.writestr("xl/workbook.xml", workbook_xml(sheet_names))
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels(len(sheets)))
        zf.writestr("xl/styles.xml", styles_xml())
        for idx, sheet in enumerate(sheets, start=1):
            zf.writestr(f"xl/worksheets/sheet{idx}.xml", sheet.xml)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a software quotation workbook from JSON.")
    parser.add_argument("input_json", help="Path to quote-project.json")
    parser.add_argument("output_xlsx", help="Path to output workbook")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    items = normalize_items(payload)
    pricing = apply_budget_rules(payload, items)
    rate = float(payload.get("day_rate", 800) or 800)
    mode = str(payload.get("mode") or ("reuse" if payload.get("base_rows") else "template")).lower()
    payload["mode"] = mode

    if mode == "reuse":
        quote_sheet = quote_sheet_reuse(payload, items, rate)
    else:
        quote_sheet = quote_sheet_template(payload, items, rate)

    write_workbook(Path(args.output_xlsx), [quote_sheet])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
