#!/usr/bin/env python3
"""
data_analytics_report.py

Extracts numeric IVT-like values and other rows from a PDF report,
creates per-app and combined charts, and writes a multi-page PDF report.

Usage:
    python data_analytics_report.py

Dependencies:
    pip install pandas matplotlib PyPDF2
"""

from pathlib import Path
import re
from collections import defaultdict
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import PyPDF2
import argparse
import datetime

# ---------------------------
# Configuration / arguments
# ---------------------------
INPUT_PDF = Path("Data Analytics Assignment.pdf")   # change if needed
OUTPUT_PDF = Path("Data_Analytics_Report.pdf")      # generated report
VERBOSE = True

# ---------------------------
# Helper functions
# ---------------------------
def extract_pdf_text(pdf_path: Path) -> str:
    """Extracts text from all pages of the PDF and returns combined string."""
    reader = PyPDF2.PdfReader(str(pdf_path))
    pages_text = []
    for i, p in enumerate(reader.pages):
        try:
            pages_text.append(p.extract_text() or "")
        except Exception:
            pages_text.append("")
    return "\n".join(pages_text)

def split_app_blocks(text: str) -> list:
    """
    Splits the long PDF text into blocks using the heading 'Total Data' as delimiter.
    Each block usually corresponds to one application's section of the provided PDF.
    """
    parts = re.split(r'\n\s*Total Data\s*\n', text, flags=re.IGNORECASE)
    # first part is header/intro; subsequent parts are blocks
    if len(parts) <= 1:
        return [text]    # fallback: entire doc as single block
    return parts[1:]

def find_daily_section(block: str) -> str:
    """
    Returns the text between 'Daily Data' and 'Hourly Data' inside a block, if present.
    If not present, returns the substring after 'Daily Data' or the whole block fallback.
    """
    m = re.search(r'Daily Data\s*\n(.*?)\n\s*Hourly Data', block, re.S | re.I)
    if m:
        return m.group(1)
    m2 = re.search(r'Daily Data\s*\n(.*)', block, re.S | re.I)
    if m2:
        return m2.group(1)
    return ""

def parse_daily_lines_to_rows(daily_text: str) -> list:
    """
    Heuristically parse lines that may contain a date and numeric values (IVT).
    Strategy:
        - For ISO-date lines: ^YYYY-MM-DD (optionally time) ...
        - For lines like '11 Sep to 15 Sep' or '11 Sep to 15 Sep 1191603 ... 0.00427' detect date phrase and last numeric token
        - Use last numeric token in the line as the IVT-like metric if it's numeric.
    Returns list of tuples: (date_str, parsed_date_or_None, rest_text, ivt_value_or_None)
    """
    rows = []
    for ln in daily_text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        # Try ISO date format: 2025-09-12 0:00:00  ...
        iso = re.match(r'^(20\d{2}-\d{2}-\d{2})(?:\s+\d{1,2}:\d{2}:\d{2})?\b(.*)$', ln)
        if iso:
            date_str = iso.group(1)
            rest = iso.group(2).strip()
            tokens = re.split(r'\s+', rest) if rest else []
            ivt = _last_numeric_token(tokens)
            rows.append((date_str, _try_parse_date(date_str), rest, ivt))
            continue

        # Try 'DD Mon' or 'DD Mon to DD Mon' patterns at start
        m2 = re.match(r'^(\d{1,2}\s+\w+(?:\s+to\s+\d{1,2}\s+\w+)?)\s+(.*)$', ln, re.I)
        if m2:
            date_like = m2.group(1)
            rest = m2.group(2)
            tokens = re.split(r'\s+', rest)
            ivt = _last_numeric_token(tokens)
            # no reliable absolute year — keep date as string only (parsed as None)
            rows.append((date_like, None, rest, ivt))
            continue

        # If line starts with a word-date like '11 Sep to 15 Sep 1191603 1189884 ... 0.00427'
        # fallback: try to find first date-like substring anywhere
        mm = re.search(r'(20\d{2}-\d{2}-\d{2})', ln)
        if mm:
            date_str = mm.group(1)
            rest = ln.replace(date_str, '').strip()
            tokens = re.split(r'\s+', rest)
            ivt = _last_numeric_token(tokens)
            rows.append((date_str, _try_parse_date(date_str), rest, ivt))
            continue

        # Generic fallback: attempt to pick last numeric token on the line
        tokens = re.split(r'\s+', ln)
        ivt = _last_numeric_token(tokens)
        if ivt is not None:
            # no parseable date — store raw line as date_raw
            rows.append((ln[:40] + ("..." if len(ln)>40 else ""), None, ln, ivt))
    return rows

def _last_numeric_token(tokens):
    """Return last numeric token from tokens list as float, else None."""
    for t in reversed(tokens):
        if re.match(r'^-?\d+(\.\d+)?$', t):
            try:
                return float(t)
            except:
                continue
    return None

def _try_parse_date(s):
    """Try parse ISO or common date formats to a pandas.Timestamp, else None."""
    try:
        return pd.to_datetime(s, dayfirst=False, errors='coerce')
    except:
        return pd.NaT

# ---------------------------
# Main report generation
# ---------------------------
def generate_report(input_pdf: Path, output_pdf: Path, verbose: bool = True):
    if not input_pdf.exists():
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")

    text = extract_pdf_text(input_pdf)
    blocks = split_app_blocks(text)
    if verbose:
        print(f"Found {len(blocks)} app blocks (by 'Total Data' split).")

    app_data = []   # list of dicts: {'index': i, 'block': block, 'rows': rows, 'df': df}

    for i, block in enumerate(blocks, start=1):
        daily_text = find_daily_section(block)
        if not daily_text:
            # fallback: try to find any lines that look like daily rows within the block
            daily_text = block[:5000]  # just parse the head
        rows = parse_daily_lines_to_rows(daily_text)
        df = pd.DataFrame(rows, columns=['date_raw','date_parsed','rest','IVT'])
        # keep only rows that have IVT numeric parsed
        df['IVT'] = pd.to_numeric(df['IVT'], errors='coerce')
        app_data.append({'index': i, 'block': block, 'rows': rows, 'df': df})
        if verbose:
            print(f"App #{i} — parsed rows: {len(df)}  (rows with IVT: {df['IVT'].count()})")

    # Create PDF report with charts
    with PdfPages(str(output_pdf)) as pdf:
        # Title page
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.text(0.5, 0.8, "Data Analytics Assignment — Automated Report", ha='center', va='center', fontsize=18, weight='bold')
        fig.text(0.5, 0.73, f"Source: {input_pdf.name}", ha='center', va='center', fontsize=9)
        fig.text(0.1, 0.6, "Contents:", fontsize=12, weight='bold')
        fig.text(0.12, 0.56, "1. Per-app IVT charts\n2. Combined IVT trends across apps\n3. Observations & Recommendations", fontsize=10)
        fig.text(0.1, 0.28, f"Generated: {datetime.datetime.now().isoformat()}", fontsize=8)
        plt.axis('off')
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

        combined_date_frames = []
        plotted_any = False

        for ad in app_data:
            df = ad['df'].dropna(subset=['IVT']).copy()
            if df.empty:
                continue
            plotted_any = True

            # prefer parsed dates if available, else use row index
            if df['date_parsed'].notna().sum() > 0:
                df_sorted = df.sort_values('date_parsed')
                x = df_sorted['date_parsed']
                x_label = 'Date'
            else:
                df_sorted = df.reset_index(drop=True)
                x = df_sorted.index
                x_label = 'Row index'

            y = df_sorted['IVT'].astype(float)

            # plot per-app
            fig, ax = plt.subplots(figsize=(8.27, 5))
            ax.plot(x, y, marker='o', linewidth=1)
            ax.set_title(f'App #{ad["index"]} — Extracted Daily IVT', fontsize=12)
            ax.set_xlabel(x_label)
            ax.set_ylabel('IVT (extracted numeric)')
            ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.6)
            if x_label == 'Date':
                fig.autofmt_xdate()
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

            # if date-parsable, prepare for combined chart
            if df_sorted['date_parsed'].notna().sum() > 0:
                tmp = df_sorted[['date_parsed','IVT']].dropna().copy()
                tmp = tmp.groupby('date_parsed', as_index=False)['IVT'].mean()
                tmp = tmp.rename(columns={'IVT': f'IVT_app_{ad["index"]}'})
                tmp = tmp.set_index('date_parsed')
                combined_date_frames.append(tmp)

        # Combined chart if at least two apps had date series
        if combined_date_frames:
            merged = pd.concat(combined_date_frames, axis=1).sort_index()
            fig, ax = plt.subplots(figsize=(8.27, 5))
            merged.plot(ax=ax, marker='o', linewidth=1)
            ax.set_title('Combined IVT trends (per app)', fontsize=12)
            ax.set_xlabel('Date')
            ax.set_ylabel('IVT (extracted)')
            ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.6)
            fig.autofmt_xdate()
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

        # Observations page (text summary)
        lines = []
        lines.append("Automated Observations & Summary")
        lines.append("================================\n")
        if not plotted_any:
            lines.append("No numeric IVT values were reliably parsed from this PDF using heuristics.")
            lines.append("Please provide the raw CSV/Excel for accurate structured analysis.")
        else:
            for ad in app_data:
                df = ad['df'].dropna(subset=['IVT']).copy()
                if df.empty:
                    continue
                ivt = df['IVT'].astype(float)
                lines.append(f"App #{ad['index']}:")
                lines.append(f"  • Parsed rows: {len(df)}")
                lines.append(f"  • IVT mean: {ivt.mean():.6f}")
                lines.append(f"  • IVT median: {ivt.median():.6f}")
                lines.append(f"  • IVT min/max: {ivt.min():.6f} / {ivt.max():.6f}")
                if (ivt > 0.5).any():
                    lines.append("  • Note: Some IVT values > 0.5 (possible high invalid-traffic days).")
                if (ivt == 0).all():
                    lines.append("  • Note: All extracted IVT values are zero for parsed rows.")
                lines.append("")

            lines.append("General recommendations:")
            lines.append("  - Provide the raw structured data (CSV/Excel) for exact parsing and deeper analysis.")
            lines.append("  - Monitor idfa_ua_ratio and idfa_ip_ratio alongside IVT. High idfa_ua_ratio -> spoofing; high idfa_ip_ratio -> proxy/datacenter usage.")
            lines.append("  - Add anomaly detection on requests_per_idfa (flag spikes > 2x baseline).")
            lines.append("  - For days with high IVT, sample user-agents and IP ranges to identify patterns.")
            lines.append("")
            lines.append("Limitations: This is an automated heuristic parse of a PDF with inconsistent formatting. Use original structured files for higher-confidence analytics.")

        # Render text page(s) into PDF (split if long)
        chunk_size = 45
        for i in range(0, len(lines), chunk_size):
            slice_lines = lines[i:i+chunk_size]
            fig = plt.figure(figsize=(8.27, 11.69))
            fig.text(0.01, 0.99, "\n".join(slice_lines), va='top', fontsize=9, family='monospace')
            plt.axis('off')
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

    if verbose:
        print(f"Saved report to: {output_pdf}")

# ---------------------------
# CLI runner
# ---------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Data Analytics PDF report from provided PDF")
    parser.add_argument("--input", "-i", default=str(INPUT_PDF), help="Input PDF path")
    parser.add_argument("--output", "-o", default=str(OUTPUT_PDF), help="Output PDF path")
    parser.add_argument("--quiet", action="store_true", help="Reduce verbosity")
    args = parser.parse_args()

    generate_report(Path(args.input), Path(args.output), verbose=not args.quiet)
