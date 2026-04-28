# Project Library

## Pandemic Visualization & Analysis by R
- Developed an R-based analytics project to compare spread patterns, mortality trends, and geographic distribution across three infectious diseases.
- Cleaned and integrated WHO datasets, then built stream graphs and Shiny-based geospatial visualizations using ggplot2 for clearer cross-disease and cross-region analysis.
- Scraped early COVID-19 news-frequency data in R and compared media attention trends with reported case growth.
- Identified differences in disease trajectories across time and geography, and observed periods where news coverage and outbreak dynamics did not move in sync.
Keywords: data visualization, R, ggplot2, Shiny, web scraping, public health analytics, comparative analysis, geospatial analysis, dashboarding, reporting

## Airbnb Relational Database Design — MySQL
- Designed a normalized MySQL database for Airbnb-style marketplace operations to support analysis of bookings, listings, hosts, and guests.
- Translated an ER model into a 20-table relational schema with primary and foreign keys to maintain integrity across interconnected entities.
- Developed 10 business-oriented SQL analysis scenarios focused on revenue, operational risk, and marketplace performance.
- Wrote multi-table SQL queries using joins, subqueries, set operations, and aggregations to answer reporting and decision-support questions.
Keywords: MySQL, SQL, relational database, ER model, schema design, normalization, business queries, joins, subqueries, aggregation, data modeling

## Cloud-Based E-Commerce Customer Analytics
- Built a cloud-based customer analytics pipeline in Snowflake, Python, and SQLAlchemy using the Brazilian Olist e-commerce dataset, integrating 8 interconnected tables across orders, customers, products, sellers, payments, reviews, and geolocation.
- Cleaned and merged multi-table transactional data into a unified analytical dataset, removing duplicates, handling null values, and preserving join integrity for downstream unsupervised learning.
- Engineered temporal, ratio-based, customer-level, and order-level features, including delivery time, estimated delay, approval delay, freight-to-price ratio, average order value, number of orders, review score, and product diversity.
- Applied RFM analysis to segment 96,461 customers, quantify recency/frequency/monetary behavior, and identify common customer patterns, including a large recent-but-low-frequency/low-monetary segment and high-value customers with stronger retention potential.
- Prepared clustering inputs with StandardScaler for numerical features and OneHotEncoder for categorical features, then used the elbow method to select 4 clusters for K-Means segmentation.
- Identified four distinct customer profiles, including Budget-Conscious & Prompt Delivery, Satisfied Medium Spenders, High-Value, Delayed Delivery, and High Average Order Value customers; findings showed that the high-value delayed-delivery segment had the longest delivery times and lowest review scores, indicating a clear operational improvement opportunity.
- Produced exploratory visualizations showing heavily positive-skewed review scores, right-skewed average order values, dominant credit-card usage, and strong order concentration in São Paulo and several major Brazilian states.
Keywords: Snowflake, Python, SQL, SQLAlchemy, cloud analytics, customer segmentation, RFM analysis, K-Means clustering, feature engineering, e-commerce analytics, analytical pipeline, cloud data workflow

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
Keywords: multi-label classification, NLP, Python, Hugging Face, Transformers, Keras, TensorFlow, text classification, neural network, deep learning, model training, classification pipeline

## Commonsense Reasoning with Pre-trained Language Models
- Developed a binary classification pipeline for ComVE Subtask A using RoBERTa-based sequence classification.
- Built a multiple-choice reasoning workflow for Subtask B using transformer-based multiple-choice modeling.
- Implemented a sequence-to-sequence generation pipeline for Subtask C using BART to generate plausible commonsense explanations.
- Used Hugging Face datasets and tokenizers to preprocess inputs across sentence-pair, multi-option, and text-generation formats.
- Configured reproducible training workflows with deterministic seeds and Trainer / Seq2SeqTrainer APIs.
Keywords: NLP, transformer models, Hugging Face, RoBERTa, BART, sequence classification, multiple-choice classification, text generation, LLM, language modeling, reasoning pipeline
