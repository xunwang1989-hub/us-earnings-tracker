from math import pow

# Historical fiscal-year model (USD billions unless stated)
years = [2021, 2022, 2023, 2024, 2025]
revenue = [27.106, 33.671, 34.233, 35.435, 34.189]
gross_profit = [6.789, 8.787, 6.917, 6.442, 5.931]
ebit = [5.447, 5.306, 4.672, 4.819, 2.854]
debt = [1.373, 1.494, 2.756, 2.828, 5.522]
cash = [2.236, 2.543, 3.470, 4.663, 3.931]
equity = [16.889, 19.046, 20.593, 21.949, 22.752]
fcf = [4.367, 2.481, 2.414, 4.373, 0.788]
market_cap = [34.14, 25.77, 41.87, 37.08, 25.90]

tax_rate = 0.24

gross_margin = [gp / rev for gp, rev in zip(gross_profit, revenue)]
invested_capital = [d + e - c for d, e, c in zip(debt, equity, cash)]
roic = []
for i in range(len(years)):
    nopat = ebit[i] * (1 - tax_rate)
    base = invested_capital[i] if i == 0 else (invested_capital[i] + invested_capital[i - 1]) / 2
    roic.append(nopat / base)

fcf_yield = [f / m for f, m in zip(fcf, market_cap)]

revenue_cagr = pow(revenue[-1] / revenue[0], 1 / (len(years) - 1)) - 1

def pct(x):
    return f"{x * 100:.2f}%"

# Write model table
with open('lennar_5y_model.csv', 'w', encoding='utf-8') as f:
    f.write('year,revenue_b,gross_profit_b,gross_margin_pct,ebit_b,invested_capital_b,roic_pct,fcf_b,market_cap_b,fcf_yield_pct\n')
    for i in range(len(years)):
        f.write(
            f"{years[i]},{revenue[i]:.3f},{gross_profit[i]:.3f},{gross_margin[i]*100:.2f},{ebit[i]:.3f},"
            f"{invested_capital[i]:.3f},{roic[i]*100:.2f},{fcf[i]:.3f},{market_cap[i]:.2f},{fcf_yield[i]*100:.2f}\n"
        )

# Write summary text
with open('lennar_5y_summary.txt', 'w', encoding='utf-8') as f:
    f.write(f"Revenue CAGR (2021-2025): {pct(revenue_cagr)}\\n")
    f.write(f"Gross margin trend: {', '.join([f'{y}:{pct(v)}' for y, v in zip(years, gross_margin)])}\\n")
    f.write(f"ROIC trend (tax-adjusted, proxy): {', '.join([f'{y}:{pct(v)}' for y, v in zip(years, roic)])}\\n")
    f.write(f"FCF yield trend: {', '.join([f'{y}:{pct(v)}' for y, v in zip(years, fcf_yield)])}\\n")

# Tiny SVG line chart generator

def make_svg(filename, title, values, yfmt='{:.1f}'):
    width, height = 860, 360
    ml, mr, mt, mb = 70, 30, 45, 55
    pw, ph = width - ml - mr, height - mt - mb
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        vmax = vmin + 1

    def x(i):
        return ml + (pw * i / (len(values) - 1))

    def y(v):
        return mt + (vmax - v) * ph / (vmax - vmin)

    points = ' '.join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(values))

    yticks = []
    for j in range(5):
        tval = vmin + (vmax - vmin) * j / 4
        yy = y(tval)
        yticks.append((yy, tval))

    with open(filename, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">\n')
        f.write('<rect width="100%" height="100%" fill="#ffffff"/>\n')
        f.write(f'<text x="{ml}" y="26" font-size="18" font-family="Helvetica" fill="#111">{title}</text>\n')

        for yy, tval in yticks:
            f.write(f'<line x1="{ml}" y1="{yy:.1f}" x2="{width-mr}" y2="{yy:.1f}" stroke="#e5e7eb"/>\n')
            f.write(f'<text x="{ml-10}" y="{yy+4:.1f}" text-anchor="end" font-size="11" font-family="Helvetica" fill="#555">{yfmt.format(tval)}</text>\n')

        f.write(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{height-mb}" stroke="#333"/>\n')
        f.write(f'<line x1="{ml}" y1="{height-mb}" x2="{width-mr}" y2="{height-mb}" stroke="#333"/>\n')

        f.write(f'<polyline fill="none" stroke="#0f766e" stroke-width="3" points="{points}"/>\n')

        for i, v in enumerate(values):
            xx, yy = x(i), y(v)
            f.write(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="4" fill="#0f766e"/>\n')
            f.write(f'<text x="{xx:.1f}" y="{height-mb+20}" text-anchor="middle" font-size="11" font-family="Helvetica" fill="#333">{years[i]}</text>\n')
            f.write(f'<text x="{xx:.1f}" y="{yy-10:.1f}" text-anchor="middle" font-size="11" font-family="Helvetica" fill="#0f172a">{yfmt.format(v)}</text>\n')

        f.write('</svg>\n')

make_svg('chart_revenue.svg', 'Lennar Revenue (USD B)', revenue, yfmt='{:.1f}')
make_svg('chart_gross_margin.svg', 'Lennar Gross Margin (%)', [v * 100 for v in gross_margin], yfmt='{:.1f}%')
make_svg('chart_roic.svg', 'Lennar ROIC Proxy (%)', [v * 100 for v in roic], yfmt='{:.1f}%')
make_svg('chart_fcf_yield.svg', 'Lennar FCF Yield (%)', [v * 100 for v in fcf_yield], yfmt='{:.1f}%')

print('Created: lennar_5y_model.csv, lennar_5y_summary.txt, chart_*.svg')
print(f'Revenue CAGR (2021-2025): {revenue_cagr*100:.2f}%')
