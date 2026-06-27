
# ============================================================
# FILE: model/train_model.py
# PURPOSE: Load dataset, clean it, train ML model, save it
# ============================================================

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score
import joblib
import os

# STEP 1: LOAD DATA
print("Loading dataset...")
train_df = pd.read_csv('dataset/drugsComTrain_raw.csv')
test_df  = pd.read_csv('dataset/drugsComTest_raw.csv')
df = pd.concat([train_df, test_df], ignore_index=True)
print(f"Total records loaded: {len(df)}")

# STEP 2: KEEP ONLY NEEDED COLUMNS
df = df[['condition', 'drugName', 'rating']].copy()
df.dropna(subset=['condition', 'drugName'], inplace=True)
df = df[~df['condition'].str.contains(r'\d', na=True)]
df['condition'] = df['condition'].str.strip().str.lower()
df['drugName']  = df['drugName'].str.strip().str.lower()
print(f"Records after cleaning: {len(df)}")

# STEP 3: KEEP TOP 50 CONDITIONS
top_conditions = df['condition'].value_counts().head(50).index.tolist()
df = df[df['condition'].isin(top_conditions)].copy()
print(f"Records after top-50 filter: {len(df)}")

# STEP 4: KEEP TOP 10 DRUGS PER CONDITION
print("Filtering top drugs per condition...")
result_frames = []
for cond in top_conditions:
    subset = df[df['condition'] == cond].copy()
    top10  = subset.groupby('drugName')['rating'].mean().nlargest(10).index.tolist()
    result_frames.append(subset[subset['drugName'].isin(top10)])

df = pd.concat(result_frames, ignore_index=True)
print(f"Records after drug filter: {len(df)}")
print(f"Columns now: {df.columns.tolist()}")

# STEP 5: ENCODE
print("Encoding...")
condition_encoder = LabelEncoder()
drug_encoder      = LabelEncoder()
df['condition_encoded'] = condition_encoder.fit_transform(df['condition'])
df['drug_encoded']      = drug_encoder.fit_transform(df['drugName'])

# STEP 6: SPLIT
X = df[['condition_encoded', 'rating']]
y = df['drug_encoded']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"Train: {len(X_train)} | Test: {len(X_test)}")

# STEP 7: TRAIN
print("Training model... please wait...")
model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)

# STEP 8: EVALUATE
accuracy = accuracy_score(y_test, model.predict(X_test))
print(f"Accuracy: {accuracy * 100:.2f}%")

# STEP 9: SAVE
os.makedirs('model', exist_ok=True)
joblib.dump(model,             'model/drug_model.pkl')
joblib.dump(condition_encoder, 'model/condition_encoder.pkl')
joblib.dump(drug_encoder,      'model/drug_encoder.pkl')
df.to_csv('model/cleaned_data.csv', index=False)
print("All files saved successfully!")
print("Training complete!")
