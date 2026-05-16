from datetime import datetime
import yfinance as yf
import requests
import json
import os
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import LETTER
from sec_edgar_downloader import Downloader

def format_large_number(num):
    if not num:
        return "N/A"

    if num >= 1_000_000_000:
        return f"${num / 1_000_000_000:.1f}B"

    if num >= 1_000_000:
        return f"${num / 1_000_000:.1f}M"

    return str(num)

def safe_divide(numerator, denominator):
    if not numerator or not denominator:
        return "N/A"
    return round(numerator / denominator, 2)

peer_map = {
    "UNH": ["HUM", "CI", "ELV"],
    "HUM": ["UNH", "CI", "ELV"],
    "HCA": ["THC", "UHS", "CYH"],
    "THC": ["HCA", "UHS", "CYH"],
    "DVA": ["FMS", "USPH", "SEM"],
    "CI": ["UNH", "HUM", "ELV"],
    "ELV": ["UNH", "HUM", "CI"],
}

ticker = input("Enter a healthcare company ticker: ").upper()

stock = yf.Ticker(ticker)
info = stock.info
history = stock.history(period="6mo")
start_price = history["Close"].iloc[0]
end_price = history["Close"].iloc[-1]
high_price = history["Close"].max()
low_price = history["Close"].min()

six_month_return = ((end_price - start_price) / start_price) * 100
drawdown_from_high = ((end_price - high_price) / high_price) * 100

stock_performance = {
    "starting_price": f"${start_price:.2f}",
    "ending_price": f"${end_price:.2f}",
    "six_month_return": f"{six_month_return:.1f}%",
    "six_month_high": f"${high_price:.2f}",
    "six_month_low": f"${low_price:.2f}",
    "drawdown_from_high": f"{drawdown_from_high:.1f}%",
}
revenue = info.get("totalRevenue")
ebitda = info.get("ebitda")
enterprise_value = info.get("enterpriseValue")

ebitda_margin = safe_divide(ebitda, revenue)
ev_revenue = safe_divide(enterprise_value, revenue)
ev_ebitda = safe_divide(enterprise_value, ebitda)

company_data = {
    "ticker": ticker,
    "company_name": info.get("longName"),
    "sector": info.get("sector"),
    "industry": info.get("industry"),
    "market_cap": format_large_number(info.get("marketCap")),
"enterprise_value": format_large_number(info.get("enterpriseValue")),
"revenue": format_large_number(info.get("totalRevenue")),
"ebitda": format_large_number(info.get("ebitda")),
    "ebitda_margin": f"{ebitda_margin * 100:.1f}%" if ebitda_margin != "N/A" else "N/A",
"ev_revenue": f"{ev_revenue}x" if ev_revenue != "N/A" else "N/A",
"ev_ebitda": f"{ev_ebitda}x" if ev_ebitda != "N/A" else "N/A",
    "profit_margin": f"{info.get('profitMargins', 0) * 100:.1f}%",
    "pe_ratio": round(info.get("trailingPE"), 2) if info.get("trailingPE") else "N/A",
"current_price": f"${info.get('currentPrice'):.2f}" if info.get("currentPrice") else "N/A",
    "business_summary": info.get("longBusinessSummary"),
}

peers = peer_map.get(ticker, [])

peer_data = []

for peer in peers:
    peer_stock = yf.Ticker(peer)
    peer_info = peer_stock.info

    peer_revenue = peer_info.get("totalRevenue")
peer_ebitda = peer_info.get("ebitda")
peer_enterprise_value = peer_info.get("enterpriseValue")

peer_ebitda_margin = safe_divide(peer_ebitda, peer_revenue)
peer_ev_revenue = safe_divide(peer_enterprise_value, peer_revenue)
peer_ev_ebitda = safe_divide(peer_enterprise_value, peer_ebitda)

peer_data.append({
    "ticker": peer,
    "company_name": peer_info.get("longName"),
    "industry": peer_info.get("industry"),
    "market_cap": format_large_number(peer_info.get("marketCap")),
    "enterprise_value": format_large_number(peer_info.get("enterpriseValue")),
    "revenue": format_large_number(peer_revenue),
    "ebitda": format_large_number(peer_ebitda),
    "ebitda_margin": f"{peer_ebitda_margin * 100:.1f}%" if peer_ebitda_margin != "N/A" else "N/A",
    "ev_revenue": f"{peer_ev_revenue}x" if peer_ev_revenue != "N/A" else "N/A",
    "ev_ebitda": f"{peer_ev_ebitda}x" if peer_ev_ebitda != "N/A" else "N/A",
    "profit_margin": f"{peer_info.get('profitMargins', 0) * 100:.1f}%",
    "pe_ratio": round(peer_info.get("trailingPE"), 2) if peer_info.get("trailingPE") else "N/A",
})
dl = Downloader("sec_filings", "alex@example.com")

dl.get("10-K", ticker, limit=1)

print("Downloaded latest 10-K filing")
filing_text = ""

for root, dirs, files in os.walk("sec-edgar-filings"):
    for file in files:
        if file.endswith(".txt"):
            filing_path = os.path.join(root, file)

            with open(filing_path, "r", encoding="utf-8", errors="ignore") as f:
                filing_text = f.read()

            print(f"Read SEC filing from: {filing_path}")
            break

    if filing_text:
        break

risk_start = filing_text.find("Item 1A. Risk Factors")

if risk_start != -1:
    sec_excerpt = filing_text[risk_start:risk_start + 8000]
else:
    sec_excerpt = filing_text[:5000]
current_date = datetime.now().strftime("%B %d, %Y")
prompt = f"""
You are a healthcare investment banking analyst.

Using the company data and peer company data below, write a short preliminary diligence summary. 

Use the formatted financial metrics exactly as provided. Do not convert percentages or rewrite raw numbers.

Use clean markdown formatting with tables where requested. Keep the report professional, concise, and analyst-style.

Company data:
{json.dumps(company_data, indent=2)}

Peer company data:
{json.dumps(peer_data, indent=2)}

Stock performance data:
{json.dumps(stock_performance, indent=2)}

SEC filing excerpt:
{sec_excerpt}

Format:
# Executive Summary
Give 3 concise bullets:
- investment/strategic positives
- key risks
- main diligence focus

# Company Overview

# Financial Summary
Create a markdown table with:
Metric | Value

# Peer Comparison
Create a markdown table comparing the company to peers using:
Company | Revenue | EBITDA Margin | EV/Revenue | EV/EBITDA | P/E

# Stock Performance Commentary
Briefly interpret recent stock performance, including six-month return and drawdown from high.

# Competitive Positioning

# Why This Company May Be Attractive

# Key Risks

# Diligence Questions
List 5 questions.
"""
plt.figure(figsize=(10, 5))

plt.plot(history.index, history["Close"])

plt.title(f"{ticker} Stock Price - Last 6 Months")
plt.xlabel("Date")
plt.ylabel("Stock Price")

chart_filename = f"outputs/{ticker}_stock_chart.png"

plt.savefig(chart_filename)

print(f"Stock chart saved as {chart_filename}")
response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "llama3.2",
        "prompt": prompt,
        "stream": False
    }
)

ai_response = response.json()["response"]

print(ai_response)

filename = f"outputs/{ticker}_diligence_report.md"

report_content = f"""
# AI Healthcare Diligence Report

**Company:** {company_data['company_name']}  
**Ticker:** {ticker}  
**Report Date:** {current_date}  
**Prepared By:** AI Diligence Agent  

---

{ai_response}

---

## Disclaimer
This report is AI-generated using public market data and SEC filings for educational and research purposes only.
"""

with open(filename, "w") as file:
    file.write(report_content)

print(f"Memo saved as {filename}")
pdf_filename = f"outputs/{ticker}_diligence_report.pdf"

doc = SimpleDocTemplate(pdf_filename, pagesize=LETTER)
styles = getSampleStyleSheet()
story = []

story.append(Paragraph(f"AI Healthcare Diligence Report: {ticker}", styles["Title"]))
story.append(Spacer(1, 12))

story.append(Paragraph(f"Company: {company_data['company_name']}", styles["Normal"]))
story.append(Paragraph(f"Ticker: {ticker}", styles["Normal"]))
story.append(Paragraph(f"Report Date: {current_date}", styles["Normal"]))
story.append(Paragraph("Prepared By: AI Diligence Agent", styles["Normal"]))
story.append(Spacer(1, 12))

story.append(Image(chart_filename, width=450, height=225))
story.append(Spacer(1, 12))

financial_table_data = [
    ["Metric", "Value"],
    ["Revenue", company_data["revenue"]],
    ["EBITDA", company_data["ebitda"]],
    ["EBITDA Margin", company_data["ebitda_margin"]],
    ["EV/Revenue", company_data["ev_revenue"]],
    ["EV/EBITDA", company_data["ev_ebitda"]],
    ["P/E Ratio", company_data["pe_ratio"]],
]

financial_table = Table(financial_table_data, colWidths=[200, 200])
financial_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("PADDING", (0, 0), (-1, -1), 6),
]))

story.append(Paragraph("Financial Summary", styles["Heading2"]))
story.append(financial_table)
story.append(Spacer(1, 12))

peer_table_data = [["Company", "Revenue", "EBITDA Margin", "EV/Revenue", "EV/EBITDA", "P/E"]]

peer_table_data.append([
    company_data["company_name"],
    company_data["revenue"],
    company_data["ebitda_margin"],
    company_data["ev_revenue"],
    company_data["ev_ebitda"],
    company_data["pe_ratio"],
])

for peer in peer_data:
    peer_table_data.append([
        peer["company_name"],
        peer["revenue"],
        peer["ebitda_margin"],
        peer["ev_revenue"],
        peer["ev_ebitda"],
        peer["pe_ratio"],
    ])

peer_table = Table(peer_table_data, colWidths=[140, 70, 80, 70, 70, 50])
peer_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8),
    ("PADDING", (0, 0), (-1, -1), 4),
]))

story.append(Paragraph("Peer Comparison", styles["Heading2"]))
story.append(peer_table)
story.append(Spacer(1, 12))

for line in ai_response.split("\n"):
    clean_line = line.strip()

skip_lines = [
    "## Financial Summary",
    "# Financial Summary",
    "Financial Summary",
    "**Financial Summary**",

    "## Peer Comparison",
    "# Peer Comparison",
    "Peer Comparison",
    "**Peer Comparison**",
]

for line in ai_response.split("\n"):
    clean_line = line.strip()

    if (
        clean_line
        and "|" not in clean_line
        and "---" not in clean_line
        and clean_line not in skip_lines
    ):
        story.append(Paragraph(clean_line, styles["Normal"]))
        story.append(Spacer(1, 6))

doc.build(story)

print(f"PDF saved as {pdf_filename}")