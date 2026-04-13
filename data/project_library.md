# Project Library

## Pandemic Visualization & Analysis by R
- Cleaned, preprocessed, and aggregated WHO pandemic datasets for comparative analysis.
- Built stream graphs to visualize trends in total cases and mortality over time across three diseases.
- Created interactive geographic heatmaps using ggplot2 and Shiny to show pandemic intensity and regional distribution.
- Applied web scraping in R to collect early-stage COVID-19 news frequency data for media-versus-infection trend analysis.
- Compared COVID-19 news volume with new case counts, identifying an observed negative correlation.
Keywords: data visualization, R, ggplot2, Shiny, web scraping, public health analytics, comparative analysis, geospatial analysis

## Airbnb Relational Database Design — MySQL
- Built an ER model for Airbnb marketplace operations and translated it into a normalized MySQL database schema.
- Implemented 20 SQL tables with primary and foreign keys to preserve relational integrity.
- Defined 10 business-oriented analytical scenarios and wrote SQL queries to generate revenue, risk, and performance insights.
- Developed multi-table SQL logic using INNER JOIN and LEFT OUTER JOIN.
- Used single-row and multiple-row subqueries, aggregation, UNION, NOT IN, and NOT EXISTS to answer business questions.
Keywords: MySQL, SQL, relational database, ER model, schema design, normalization, business queries, joins, subqueries, aggregation, data modeling

## Cloud-Based E-Commerce Customer Analytics
- Created an OLIST database in Snowflake and worked with eight interconnected e-commerce tables.
- Connected Snowflake to Jupyter Notebook using SQLAlchemy and Python to fetch, clean, and merge data.
- Performed data cleaning by removing duplicates and handling missing values.
- Engineered features including delivery time, estimated delay, approval delay, and freight-to-price ratio.
- Built customer-level and order-level aggregated features.
- Applied RFM analysis and K-Means clustering to identify four customer segments.
Keywords: Snowflake, Python, SQL, SQLAlchemy, cloud analytics, customer segmentation, RFM analysis, K-Means clustering, feature engineering, e-commerce analytics

## Online Retail Association Rule
- Cleaned transaction data by removing missing values, canceled invoices, non-numeric stock codes, and invalid quantity records.
- Filtered the dataset to focus on France.
- Grouped transaction data by invoice and product description and transformed it into a binary basket matrix.
- Applied the Apriori algorithm using mlxtend to identify frequent itemsets.
- Generated association rules and evaluated product relationships using support, confidence, and lift.
Keywords: association rule mining, Apriori, market basket analysis, retail analytics, recommendation systems, cross-sell analysis, support, confidence, lift

## Multi-Label Text Classification with DistilRoBERTa Tokenization
- Used the DistilRoBERTa tokenizer from Hugging Face to tokenize text inputs with truncation and padding.
- Converted tokenized inputs into many-hot bag-of-words vectors.
- Loaded training and validation data from CSV files using the datasets library and transformed label columns into multi-label targets.
- Built a feedforward neural network in Keras with dense layers, batch normalization, dropout, and L2 regularization.
- Trained the model with Adam optimization and monitored accuracy, precision, recall, and micro-F1.
Keywords: multi-label classification, NLP, Python, Hugging Face, Transformers, Keras, TensorFlow, text classification, neural network

## Commonsense Reasoning with Pre-trained Language Models
- Developed a binary classification pipeline for ComVE Subtask A using RoBERTa-based sequence classification.
- Built a multiple-choice reasoning workflow for Subtask B using transformer-based multiple-choice modeling.
- Implemented a sequence-to-sequence generation pipeline for Subtask C using BART to generate plausible commonsense explanations.
- Used Hugging Face datasets and tokenizers to preprocess inputs across sentence-pair, multi-option, and text-generation formats.
- Configured reproducible training workflows with deterministic seeds and Trainer / Seq2SeqTrainer APIs.
Keywords: NLP, transformer models, Hugging Face, RoBERTa, BART, sequence classification, multiple-choice classification, text generation
