# Experience Library

## Arizona List — Data Analyst Intern
Period: Jan 2026 – May 2026
Location: Phoenix, Arizona
Bullets source:
- Delivered a 10-section donor intelligence report querying the organization's PostgreSQL CRM — covering 7,769 unique donors, 53,020 transactions, and $6.4M+ in lifetime contributions across 22 years — giving leadership a comprehensive analytical baseline they had not previously had.
- Recovered 386 Leadership Council members (5% of the donor base) without a dedicated database field by cross-referencing three disconnected data sources; the process also revealed that 7,300+ regular donors had never been screened for LC potential, surfacing an untapped cultivation pipeline.
- Ran a 4-step contact funnel across 79,830 person records and isolated 16,440 (21%) reachable only by direct mail — the first time this segment had been quantified — while flagging ~2,900 additional contacts with neither a valid email nor a deliverable address, unreachable through any existing channel.
- Built a lapsed donor recovery model using consecutive-streak SQL logic that surfaced 352 qualified candidates averaging 7.4 years of giving history, a 5.3-year unbroken streak, and $3,044 in lifetime value; 209 (59%) had at least one $250+ giving year; tiered all 352 into 4 priority groups and flagged 85 Tier 1 targets for immediate re-engagement.
- Mapped $6.4M+ in giving across 925 ZIP codes and 15+ states; found DC and MA donors averaged $1,594 and $1,748 per donation — 12× and 13× the Arizona average of $130 — identifying a high-capacity national segment that warranted deeper investment.
- Packaged all analysis into repeatable workflows and delivered 3 exportable CSV outputs (352-row full lapsed list, 209-row high-value subset, 6-row postcard list) so the team could refresh every segment on new data each quarter without rebuilding from scratch.
- Built an end-to-end data pipeline using SQLAlchemy and pandas to extract 53,020 records from a PostgreSQL CRM, apply multi-step transformations including deduplication, type validation, and derived field calculation, and export clean outputs as structured CSVs consumed directly by outreach operations.
- Designed a 9-table relational schema from scratch to model the organization's CRM data, defining primary keys, foreign key constraints, and composite keys for many-to-many relationships; built a deduplication view that consolidated contributions across two overlapping source tables before any downstream processing ran.
- Enforced data quality across 79,830 records by validating primary key uniqueness, foreign key referential integrity (confirmed <0.04% orphaned rows), address field completeness, and email presence — establishing a reliable foundation for all downstream analysis.
- Wrote parameterized, reusable SQL scripts for recurring data delivery: a quarterly postcard outreach pipeline configurable by start date and a lapsed donor extraction rerunable on updated data, reducing repeated manual work to a single parameter change.
- Applied window functions and sequential gap-detection logic in SQL to compute consecutive giving streaks across 7,769 donors — enabling cohort segmentation that standard GROUP BY aggregations could not support.
Keywords: PostgreSQL, SQL, SQLAlchemy, Python, pandas, matplotlib, geopandas, geospatial analysis, geospatial mapping, donor analytics, lapsed donor segmentation, donor retention, cohort analysis, window functions, funnel analysis, multi-source reconciliation, time series analysis, nonprofit analytics, nonprofit CRM, outreach analysis, contact segmentation, data quality, repeatable query, export automation, stakeholder reporting, actionable insights

## University of Arizona Law Library — Library Assistant
Period: Jan 2025 – Dec 2025
Location: Tucson, Arizona
Bullets source:
- Maintained catalog records and service logs across three systems — ALMA, LibAnswers, and Nexis Uni — enforcing data entry accuracy and documentation consistency that supported retrieval reliability across thousands of legal resources.
- Retrieved case law, statutes, and academic references through targeted Nexis Uni searches, fulfilling time-sensitive faculty and student research requests with high-precision sourcing across legal and academic databases.
- Applied Library of Congress classification to organize and maintain large-scale legal collections, ensuring systematic cataloging and cross-subject retrieval accuracy across an extensive multi-volume catalog.
Keywords: data management, information retrieval, documentation, cataloging, record accuracy, classification, database management, research support, data entry, structured information management, legal research, ALMA, Nexis Uni

## University of Arizona College of Engineering — Graduate Research Assistant
Period: May 2025 – Aug 2025
Location: Tucson, Arizona
Bullets source:
- Generated 300+ synthetic laparoscopic surgery images by combining programmatic image processing with AI generation tools, directly expanding the training dataset for a medical computer vision model without requiring additional clinical data collection.
- Built a contamination injection pipeline that automatically overlaid surgical artefacts — blood, smoke, and lens blur — onto clean endoscopy images, enabling controlled simulation of real operating room conditions at scale.
- Delivered a reproducible augmentation framework covering multiple artefact types and severity levels, giving the research team a reusable data generation workflow applicable to future medical imaging datasets.
Keywords: computer vision, artificial intelligence, medical imaging, image dataset, synthetic data, image augmentation, pipeline development, model training support, AI workflow, image processing, data generation pipeline

## University of Arizona Cancer Center — Student Researcher
Period: Sep 2024 – Mar 2025
Location: Tucson, Arizona
Bullets source:
- Improved dataset classification efficiency by 10% by building a structured analytical pipeline — data cleaning, comparative visualization, K-means clustering, and subgroup outlier detection — to identify cancer cell samples with the strongest reversal effects across multiple experimental datasets.
- Segmented cancer cell reversal ratio values using K-means clustering to separate stable and significant-change groups, then applied outlier detection within the significant-change group to pinpoint top-performing samples that standard filtering alone would have missed.
- Standardized the full analysis workflow — cleaning, visualization, clustering, and candidate selection — into a reproducible pipeline, enabling the research team to apply the same methodology to new datasets without re-engineering the process for each run.
Keywords: data cleaning, data visualization, K-means clustering, outlier detection, reproducible pipeline, candidate selection, classification efficiency, statistical analysis, exploratory data analysis, Python, biological data, research workflow

## Usher Technologies Inc — Data Scientist Intern
Period: Jul 2023 – Nov 2023
Location: Manila, Philippines
Bullets source:
- Built a machine learning model that compared pre-earthquake sensor baselines against post-earthquake measurements to detect structural deviations, cutting manual building inspection effort by 15% following strong seismic events.
- Designed an anomaly detection workflow that flagged significant gaps between predicted and actual sensor values, enabling rapid identification of potentially damaged structures before on-site inspection teams were dispatched.
- Validated model outputs against field inspection records across multiple post-earthquake sites, confirming strong alignment between sensor-based assessments and real-world findings — demonstrating reliability sufficient for operational deployment.
Keywords: machine learning, anomaly detection, sensor data, predictive analytics, structural monitoring, Python, time series, deviation analysis, model validation, forecasting, disaster response, data-driven assessment
