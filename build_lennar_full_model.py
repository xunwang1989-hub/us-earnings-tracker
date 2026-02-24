import datetime
import zipfile
from xml.sax.saxutils import escape

# -------------------------------------------------
# Lennar model: historical FY2021-2025 + forecast FY2026-2030
# Simplified 3-statement model under Base/Bull/Bear scenarios
# Units: USD billions unless noted
# -------------------------------------------------

YEARS_H = [2021, 2022, 2023, 2024, 2025]
YEARS_F = [2026, 2027, 2028, 2029, 2030]
ALL_YEARS = YEARS_H + YEARS_F

revenue_h = [27.106, 33.671, 34.233, 35.435, 34.189]
gross_profit_h = [6.789, 8.787, 6.917, 6.442, 5.931]
ebit_h = [5.447, 5.306, 4.672, 4.819, 2.854]
debt_h = [1.373, 1.494, 2.756, 2.828, 5.522]
cash_h = [2.236, 2.543, 3.470, 4.663, 3.931]
equity_h = [16.889, 19.046, 20.593, 21.949, 22.752]
fcf_h = [4.367, 2.481, 2.414, 4.373, 0.788]
market_cap_h = [34.14, 25.77, 41.87, 37.08, 25.90]

STATIC_MARKET_CAP = 25.90
TAX_RATE_HIST = 0.24

SCENARIO_ASSUMPTIONS = {
    "Base": {
        "rev_growth": [0.03, 0.04, 0.04, 0.03, 0.03],
        "gross_margin": [0.178, 0.185, 0.190, 0.193, 0.195],
        "sga_pct": [0.093, 0.092, 0.091, 0.090, 0.090],
        "tax_rate": 0.24,
        "da_pct": 0.007,
        "capex_pct": 0.009,
        "nwc_pct_rev_delta": 0.06,
        "div_pct_nopat": 0.30,
        "buyback_pct_fcf": 0.20,
        "debt_change": [0.0, 0.0, 0.0, 0.0, 0.0],
    },
    "Bull": {
        "rev_growth": [0.06, 0.06, 0.05, 0.05, 0.04],
        "gross_margin": [0.185, 0.195, 0.205, 0.210, 0.215],
        "sga_pct": [0.090, 0.089, 0.088, 0.087, 0.087],
        "tax_rate": 0.24,
        "da_pct": 0.007,
        "capex_pct": 0.009,
        "nwc_pct_rev_delta": 0.06,
        "div_pct_nopat": 0.30,
        "buyback_pct_fcf": 0.25,
        "debt_change": [0.0, 0.0, 0.0, 0.0, 0.0],
    },
    "Bear": {
        "rev_growth": [-0.02, 0.01, 0.02, 0.02, 0.02],
        "gross_margin": [0.168, 0.170, 0.173, 0.175, 0.177],
        "sga_pct": [0.098, 0.097, 0.096, 0.095, 0.095],
        "tax_rate": 0.24,
        "da_pct": 0.007,
        "capex_pct": 0.009,
        "nwc_pct_rev_delta": 0.06,
        "div_pct_nopat": 0.25,
        "buyback_pct_fcf": 0.10,
        "debt_change": [0.0, 0.0, 0.0, 0.0, 0.0],
    },
}


def cagr(start, end, n_years):
    return (end / start) ** (1 / n_years) - 1


def build_historical_records():
    records = []
    for i, y in enumerate(YEARS_H):
        revenue = revenue_h[i]
        gross_profit = gross_profit_h[i]
        cogs = revenue - gross_profit
        sga = gross_profit - ebit_h[i]
        ebit = ebit_h[i]
        tax = ebit * TAX_RATE_HIST
        nopat = ebit * (1 - TAX_RATE_HIST)

        cash = cash_h[i]
        debt = debt_h[i]
        equity = equity_h[i]
        op_assets = debt + equity - cash
        total_assets = cash + op_assets
        other_liab = total_assets - debt - equity  # should be ~0 by construction

        if i == 0:
            delta_cash = None
            cff = None
        else:
            delta_cash = cash_h[i] - cash_h[i - 1]
            cff = delta_cash - fcf_h[i]  # historical financing plug

        cfo = fcf_h[i]  # historical proxy
        cfi = 0.0       # historical proxy
        fcf = fcf_h[i]

        records.append({
            "year": y,
            "revenue": revenue,
            "cogs": cogs,
            "gross_profit": gross_profit,
            "gross_margin": gross_profit / revenue,
            "sga": sga,
            "ebit": ebit,
            "tax": tax,
            "net_income": nopat,
            "da": None,
            "capex": None,
            "delta_nwc": None,
            "cfo": cfo,
            "cfi": cfi,
            "dividends": None,
            "buybacks": None,
            "debt_change": None,
            "cff": cff,
            "delta_cash": delta_cash,
            "fcf": fcf,
            "cash": cash,
            "debt": debt,
            "equity": equity,
            "op_assets": op_assets,
            "other_liab": other_liab,
            "total_assets": total_assets,
            "invested_capital": op_assets,
            "roic": None,
            "fcf_yield": fcf / market_cap_h[i],
            "market_cap": market_cap_h[i],
        })
    return records


def build_forecast_records(assump, hist_records):
    records = []
    prev = hist_records[-1]

    prev_revenue = prev["revenue"]
    prev_cash = prev["cash"]
    prev_debt = prev["debt"]
    prev_equity = prev["equity"]
    prev_op_assets = prev["op_assets"]

    for i, y in enumerate(YEARS_F):
        growth = assump["rev_growth"][i]
        revenue = prev_revenue * (1 + growth)
        gross_margin = assump["gross_margin"][i]
        sga_pct = assump["sga_pct"][i]

        gross_profit = revenue * gross_margin
        cogs = revenue - gross_profit
        sga = revenue * sga_pct
        ebit = gross_profit - sga

        tax = ebit * assump["tax_rate"]
        net_income = ebit * (1 - assump["tax_rate"])

        da = revenue * assump["da_pct"]
        capex = revenue * assump["capex_pct"]
        delta_nwc = (revenue - prev_revenue) * assump["nwc_pct_rev_delta"]

        cfo = net_income + da - delta_nwc
        cfi = -capex
        fcf = cfo + cfi

        dividends = max(net_income, 0.0) * assump["div_pct_nopat"]
        buybacks = max(fcf, 0.0) * assump["buyback_pct_fcf"]
        debt_change = assump["debt_change"][i]
        cff = debt_change - dividends - buybacks
        delta_cash = cfo + cfi + cff

        cash = prev_cash + delta_cash
        debt = prev_debt + debt_change
        equity = prev_equity + net_income - dividends - buybacks

        op_assets = prev_op_assets + capex - da + delta_nwc
        invested_capital = op_assets
        avg_ic = (prev_op_assets + op_assets) / 2
        roic = net_income / avg_ic if avg_ic else 0.0

        total_assets = cash + op_assets
        other_liab = total_assets - debt - equity

        records.append({
            "year": y,
            "revenue": revenue,
            "cogs": cogs,
            "gross_profit": gross_profit,
            "gross_margin": gross_margin,
            "sga": sga,
            "ebit": ebit,
            "tax": tax,
            "net_income": net_income,
            "da": da,
            "capex": capex,
            "delta_nwc": delta_nwc,
            "cfo": cfo,
            "cfi": cfi,
            "dividends": dividends,
            "buybacks": buybacks,
            "debt_change": debt_change,
            "cff": cff,
            "delta_cash": delta_cash,
            "fcf": fcf,
            "cash": cash,
            "debt": debt,
            "equity": equity,
            "op_assets": op_assets,
            "other_liab": other_liab,
            "total_assets": total_assets,
            "invested_capital": invested_capital,
            "roic": roic,
            "fcf_yield": fcf / STATIC_MARKET_CAP,
            "market_cap": STATIC_MARKET_CAP,
        })

        prev_revenue = revenue
        prev_cash = cash
        prev_debt = debt
        prev_equity = equity
        prev_op_assets = op_assets

    return records


def build_all_scenarios():
    hist = build_historical_records()
    scen = {}
    for s, a in SCENARIO_ASSUMPTIONS.items():
        scen[s] = hist + build_forecast_records(a, hist)

    # fill historical ROIC once using op_assets average
    for s in scen:
        recs = scen[s]
        for i, r in enumerate(recs):
            if r["year"] in YEARS_H:
                if i == 0:
                    base = r["invested_capital"]
                else:
                    base = (r["invested_capital"] + recs[i - 1]["invested_capital"]) / 2
                r["roic"] = (r["net_income"] / base) if base else 0.0
    return scen


# -----------------------------
# Tiny XLSX writer
# -----------------------------
def col_name(idx):
    s = ""
    while idx > 0:
        idx, r = divmod(idx - 1, 26)
        s = chr(65 + r) + s
    return s


def xml_cell(ref, val):
    if isinstance(val, (int, float)):
        return f'<c r="{ref}"><v>{val}</v></c>'
    if val is None:
        return f'<c r="{ref}"/>'
    return f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(val))}</t></is></c>'


def sheet_xml(rows):
    max_col = max((len(r) for r in rows), default=1)
    dim = f"A1:{col_name(max_col)}{len(rows)}"
    out = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        f'<dimension ref="{dim}"/>',
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>',
        '<sheetFormatPr defaultRowHeight="15"/>',
        '<sheetData>',
    ]
    for r_i, row in enumerate(rows, start=1):
        out.append(f'<row r="{r_i}">')
        for c_i, val in enumerate(row, start=1):
            out.append(xml_cell(f"{col_name(c_i)}{r_i}", val))
        out.append('</row>')
    out.extend(['</sheetData>', '</worksheet>'])
    return "".join(out)


def write_xlsx(path, sheets):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        overrides = [
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
        ]
        for i in range(len(sheets)):
            overrides.append(
                f'<Override PartName="/xl/worksheets/sheet{i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            )
        content_types = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            + "".join(overrides)
            + '</Types>'
        )
        z.writestr("[Content_Types].xml", content_types)

        root_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            '</Relationships>'
        )
        z.writestr("_rels/.rels", root_rels)

        wb_sheets = []
        for i, (name, _) in enumerate(sheets, start=1):
            wb_sheets.append(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>')
        workbook = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<bookViews><workbookView/></bookViews>'
            f'<sheets>{"".join(wb_sheets)}</sheets>'
            '<calcPr fullCalcOnLoad="1"/>'
            '</workbook>'
        )
        z.writestr("xl/workbook.xml", workbook)

        wb_rels = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
        ]
        for i in range(len(sheets)):
            wb_rels.append(
                f'<Relationship Id="rId{i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i+1}.xml"/>'
            )
        wb_rels.append(
            f'<Relationship Id="rId{len(sheets)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        )
        wb_rels.append("</Relationships>")
        z.writestr("xl/_rels/workbook.xml.rels", "".join(wb_rels))

        styles = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            '</styleSheet>'
        )
        z.writestr("xl/styles.xml", styles)

        for i, (_, rows) in enumerate(sheets, start=1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", sheet_xml(rows))

        now = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        core = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dc:creator>Codex</dc:creator><cp:lastModifiedBy>Codex</cp:lastModifiedBy>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
            '</cp:coreProperties>'
        )
        z.writestr("docProps/core.xml", core)

        app = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            '<Application>Microsoft Excel</Application></Properties>'
        )
        z.writestr("docProps/app.xml", app)


# -----------------------------
# Presentation rows
# -----------------------------
def rows_assumptions():
    rows = [["Lennar 2021-2030 Model Assumptions", "Units: USD billions unless stated"], []]
    rows.append(["Scenario", "Metric"] + YEARS_F)
    for s in ["Base", "Bull", "Bear"]:
        a = SCENARIO_ASSUMPTIONS[s]
        rows.append([s, "Revenue growth %"] + [x * 100 for x in a["rev_growth"]])
        rows.append([s, "Gross margin %"] + [x * 100 for x in a["gross_margin"]])
        rows.append([s, "SG&A % revenue"] + [x * 100 for x in a["sga_pct"]])
        rows.append([s, "Tax rate %"] + [a["tax_rate"] * 100] * 5)
        rows.append([s, "D&A % revenue"] + [a["da_pct"] * 100] * 5)
        rows.append([s, "Capex % revenue"] + [a["capex_pct"] * 100] * 5)
        rows.append([s, "NWC / Delta Revenue %"] + [a["nwc_pct_rev_delta"] * 100] * 5)
        rows.append([s, "Dividend payout % NOPAT"] + [a["div_pct_nopat"] * 100] * 5)
        rows.append([s, "Buyback % of FCF"] + [a["buyback_pct_fcf"] * 100] * 5)
        rows.append([])
    rows.append(["Static market cap for forecast FCF yield", STATIC_MARKET_CAP])
    return rows


def rows_metric_table(title, records):
    rows = [[title], ["Year", "Revenue", "Gross Margin %", "EBIT", "ROIC %", "FCF", "FCF Yield %"]]
    for r in records:
        rows.append([
            r["year"], r["revenue"], r["gross_margin"] * 100, r["ebit"],
            (r["roic"] * 100 if r["roic"] is not None else None), r["fcf"], r["fcf_yield"] * 100,
        ])
    return rows


def rows_income_statement(scenario, records):
    rows = [[f"Income Statement - {scenario} (2021-2030)", "USD billions"], ["Line Item"] + ALL_YEARS]
    line_items = [
        ("Revenue", "revenue"),
        ("COGS", "cogs"),
        ("Gross Profit", "gross_profit"),
        ("Gross Margin %", "gross_margin"),
        ("SG&A", "sga"),
        ("EBIT", "ebit"),
        ("Tax Expense (modeled)", "tax"),
        ("Net Income (NOPAT proxy)", "net_income"),
    ]
    for label, key in line_items:
        vals = []
        for r in records:
            v = r[key]
            if key.endswith("margin"):
                v = None if v is None else v * 100
            vals.append(v)
        rows.append([label] + vals)
    return rows


def rows_balance_sheet(scenario, records):
    rows = [[f"Balance Sheet - {scenario} (2021-2030)", "USD billions"], ["Line Item"] + ALL_YEARS]
    line_items = [
        ("Cash", "cash"),
        ("Operating Assets (proxy)", "op_assets"),
        ("Total Assets", "total_assets"),
        ("Debt", "debt"),
        ("Other Liabilities (plug)", "other_liab"),
        ("Equity", "equity"),
        ("Liabilities + Equity", None),
    ]
    for label, key in line_items:
        vals = []
        for r in records:
            if label == "Liabilities + Equity":
                vals.append(r["debt"] + r["other_liab"] + r["equity"])
            else:
                vals.append(r[key])
        rows.append([label] + vals)
    return rows


def rows_cashflow(scenario, records):
    rows = [[f"Cash Flow Statement - {scenario} (2021-2030)", "USD billions"], ["Line Item"] + ALL_YEARS]
    line_items = [
        ("Net Income", "net_income"),
        ("D&A", "da"),
        ("Delta NWC", "delta_nwc"),
        ("Cash Flow from Operations", "cfo"),
        ("Capital Expenditure", "capex"),
        ("Cash Flow from Investing", "cfi"),
        ("Dividends", "dividends"),
        ("Buybacks", "buybacks"),
        ("Debt Change", "debt_change"),
        ("Cash Flow from Financing", "cff"),
        ("Net Change in Cash", "delta_cash"),
        ("Free Cash Flow", "fcf"),
    ]
    for label, key in line_items:
        vals = []
        for r in records:
            v = r[key]
            if label == "Capital Expenditure" and v is not None:
                v = -v
            vals.append(v)
        rows.append([label] + vals)
    return rows


def rows_outputs(all_scenarios):
    base = all_scenarios["Base"]
    bull = all_scenarios["Bull"]
    bear = all_scenarios["Bear"]

    rev_cagr_hist = cagr(base[0]["revenue"], base[4]["revenue"], 4)
    rev_cagr_base = cagr(base[4]["revenue"], base[-1]["revenue"], 5)
    rev_cagr_bull = cagr(bull[4]["revenue"], bull[-1]["revenue"], 5)
    rev_cagr_bear = cagr(bear[4]["revenue"], bear[-1]["revenue"], 5)

    rows = [["Model Outputs"], [], ["Metric", "Historical", "Base", "Bull", "Bear"]]
    rows.append(["Revenue CAGR %", rev_cagr_hist * 100, rev_cagr_base * 100, rev_cagr_bull * 100, rev_cagr_bear * 100])
    rows.append(["Gross Margin FY2030 %", base[4]["gross_margin"] * 100, base[-1]["gross_margin"] * 100, bull[-1]["gross_margin"] * 100, bear[-1]["gross_margin"] * 100])
    rows.append(["ROIC FY2030 %", base[4]["roic"] * 100, base[-1]["roic"] * 100, bull[-1]["roic"] * 100, bear[-1]["roic"] * 100])
    rows.append(["FCF Yield FY2030 %", base[4]["fcf_yield"] * 100, base[-1]["fcf_yield"] * 100, bull[-1]["fcf_yield"] * 100, bear[-1]["fcf_yield"] * 100])
    rows.append([])
    rows.append(["Note", "Historical 3-statement is simplified where line-item detail is unavailable; forecast years are fully linked to model assumptions."])
    return rows


def make_svg(filename, title, labels, values, yfmt="{:.1f}"):
    width, height = 900, 380
    ml, mr, mt, mb = 80, 30, 45, 60
    pw, ph = width - ml - mr, height - mt - mb
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        vmax = vmin + 1
    pad = (vmax - vmin) * 0.1
    vmin -= pad
    vmax += pad

    def x(i):
        return ml + (pw * i / (len(values) - 1))

    def y(v):
        return mt + (vmax - v) * ph / (vmax - vmin)

    points = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(values))

    with open(filename, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">\n')
        f.write('<rect width="100%" height="100%" fill="#ffffff"/>\n')
        f.write(f'<text x="{ml}" y="26" font-size="19" font-family="Helvetica" fill="#111">{escape(title)}</text>\n')
        for j in range(6):
            tval = vmin + (vmax - vmin) * j / 5
            yy = y(tval)
            f.write(f'<line x1="{ml}" y1="{yy:.1f}" x2="{width-mr}" y2="{yy:.1f}" stroke="#e5e7eb"/>\n')
            f.write(f'<text x="{ml-10}" y="{yy+4:.1f}" text-anchor="end" font-size="11" font-family="Helvetica" fill="#555">{yfmt.format(tval)}</text>\n')
        f.write(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{height-mb}" stroke="#333"/>\n')
        f.write(f'<line x1="{ml}" y1="{height-mb}" x2="{width-mr}" y2="{height-mb}" stroke="#333"/>\n')
        f.write(f'<polyline fill="none" stroke="#0f766e" stroke-width="3" points="{points}"/>\n')
        for i, v in enumerate(values):
            xx, yy = x(i), y(v)
            f.write(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="4" fill="#0f766e"/>\n')
            f.write(f'<text x="{xx:.1f}" y="{height-mb+22}" text-anchor="middle" font-size="11" font-family="Helvetica" fill="#333">{labels[i]}</text>\n')
            f.write(f'<text x="{xx:.1f}" y="{yy-10:.1f}" text-anchor="middle" font-size="10" font-family="Helvetica" fill="#0f172a">{yfmt.format(v)}</text>\n')
        f.write('</svg>\n')


def main():
    all_scenarios = build_all_scenarios()

    sheets = [
        ("Assumptions", rows_assumptions()),
        ("Metrics_Base", rows_metric_table("Base Metrics (2021-2030)", all_scenarios["Base"])),
        ("Metrics_Bull", rows_metric_table("Bull Metrics (2021-2030)", all_scenarios["Bull"])),
        ("Metrics_Bear", rows_metric_table("Bear Metrics (2021-2030)", all_scenarios["Bear"])),
        ("IS_Base", rows_income_statement("Base", all_scenarios["Base"])),
        ("BS_Base", rows_balance_sheet("Base", all_scenarios["Base"])),
        ("CF_Base", rows_cashflow("Base", all_scenarios["Base"])),
        ("IS_Bull", rows_income_statement("Bull", all_scenarios["Bull"])),
        ("BS_Bull", rows_balance_sheet("Bull", all_scenarios["Bull"])),
        ("CF_Bull", rows_cashflow("Bull", all_scenarios["Bull"])),
        ("IS_Bear", rows_income_statement("Bear", all_scenarios["Bear"])),
        ("BS_Bear", rows_balance_sheet("Bear", all_scenarios["Bear"])),
        ("CF_Bear", rows_cashflow("Bear", all_scenarios["Bear"])),
        ("Outputs", rows_outputs(all_scenarios)),
    ]

    xlsx_path = "lennar_full_model_2021_2030.xlsx"
    write_xlsx(xlsx_path, sheets)

    # long export for auditability
    def fmt(v):
        if v is None:
            return ""
        return f"{v:.3f}"
    def fmt_pct(v):
        if v is None:
            return ""
        return f"{v*100:.2f}"

    with open("lennar_full_model_long.csv", "w", encoding="utf-8") as f:
        f.write(
            "scenario,year,revenue,cogs,gross_profit,gross_margin_pct,sga,ebit,tax,net_income,da,capex,delta_nwc,cfo,cfi,dividends,buybacks,debt_change,cff,delta_cash,fcf,cash,debt,equity,op_assets,other_liab,total_assets,roic_pct,fcf_yield_pct\n"
        )
        for s in ["Base", "Bull", "Bear"]:
            for r in all_scenarios[s]:
                f.write(
                    f"{s},{r['year']},{fmt(r['revenue'])},{fmt(r['cogs'])},{fmt(r['gross_profit'])},{r['gross_margin']*100:.2f},{fmt(r['sga'])},{fmt(r['ebit'])},{fmt(r['tax'])},{fmt(r['net_income'])},{fmt(r['da'])},{fmt(r['capex'])},{fmt(r['delta_nwc'])},{fmt(r['cfo'])},{fmt(r['cfi'])},{fmt(r['dividends'])},{fmt(r['buybacks'])},{fmt(r['debt_change'])},{fmt(r['cff'])},{fmt(r['delta_cash'])},{fmt(r['fcf'])},{fmt(r['cash'])},{fmt(r['debt'])},{fmt(r['equity'])},{fmt(r['op_assets'])},{fmt(r['other_liab'])},{fmt(r['total_assets'])},{fmt_pct(r['roic'])},{r['fcf_yield']*100:.2f}\n"
                )

    base = all_scenarios["Base"]
    labels = [r["year"] for r in base]
    make_svg("chart_revenue_2021_2030_base.svg", "Lennar Revenue (Base 2021-2030)", labels, [r["revenue"] for r in base], yfmt="{:.1f}")
    make_svg("chart_gross_margin_2021_2030_base.svg", "Lennar Gross Margin % (Base 2021-2030)", labels, [r["gross_margin"] * 100 for r in base], yfmt="{:.1f}%")
    make_svg("chart_roic_2021_2030_base.svg", "Lennar ROIC % (Base 2021-2030)", labels, [r["roic"] * 100 for r in base], yfmt="{:.1f}%")
    make_svg("chart_fcf_yield_2021_2030_base.svg", "Lennar FCF Yield % (Base 2021-2030)", labels, [r["fcf_yield"] * 100 for r in base], yfmt="{:.1f}%")

    with open("lennar_model_readme.txt", "w", encoding="utf-8") as f:
        f.write("Lennar model workbook generated: 2021-2030 with Base/Bull/Bear scenarios and 3-statement tabs.\n")
        f.write("Historical years (2021-2025) use available reported data + simplified proxy lines where detailed disclosure is not loaded into this model file.\n")
        f.write("Forecast years (2026-2030) are fully assumption-driven and linked across IS/BS/CF.\n")

    print("Generated:")
    print("- lennar_full_model_2021_2030.xlsx")
    print("- lennar_full_model_long.csv")
    print("- chart_revenue_2021_2030_base.svg")
    print("- chart_gross_margin_2021_2030_base.svg")
    print("- chart_roic_2021_2030_base.svg")
    print("- chart_fcf_yield_2021_2030_base.svg")


if __name__ == "__main__":
    main()
