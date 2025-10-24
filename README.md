# 🧠 Data Analytics Assignment Report

## 📘 Project Overview
This project automates the extraction and visualization of data from a **PDF report** containing ad traffic and IVT (Invalid Traffic) metrics.  
It uses Python to parse text, analyze trends, and generate a clean multi-page **PDF report** with charts and insights.

---

## ⚙️ Features
✅ Extracts raw text data from PDF files  
✅ Parses **Daily Data** and **IVT values** for each app section  
✅ Generates per-app IVT trend charts  
✅ Creates combined comparison graphs for all apps  
✅ Produces a professional multi-page report (with summary + recommendations)

---

## 🧩 Technologies Used
- **Python 3**
- **pandas** – for data manipulation  
- **matplotlib** – for plotting charts  
- **PyPDF2** – for text extraction from PDF  
- **PdfPages** – for generating multi-page PDF reports  

---

## 🧾 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/data-analytics-report.git
   cd data-analytics-report

2. Install dependencies

pip install pandas matplotlib PyPDF2


3. Add your input file Place your file (e.g. Data Analytics Assignment.pdf) in the project directory.




---

🚀 Usage

Run the Python script:

python data_analytics_report.py

By default, it will:

Read: Data Analytics Assignment.pdf

Generate: Data_Analytics_Report.pdf


You can also specify custom input/output files:

data_analysis.py -i input.pdf -o output_report.pdf


---

📊 Output

Data_Analytics_Report.pdf
Contains:

Title Page

Per-App IVT charts

Combined IVT Trends chart

Observations & Recommendations




---

📈 Example Insights

Detects days with high Invalid Traffic (IVT > 0.5)

Identifies apps with consistent 0 IVT (likely clean traffic)

Provides recommendations for anomaly detection and data verification



---

🧑‍💻 Author

Sudarshan Ganwani
