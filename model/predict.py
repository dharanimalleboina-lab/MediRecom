# ============================================================
# FILE: model/predict.py
# PURPOSE: Load dataset and predict drugs for a condition
#          Includes allergy alerts and weighted scoring
# ============================================================

import pandas as pd
import joblib

# ── LOAD ENCODERS ────────────────────────────────────────────
import os
# For fuzzy matching
from difflib import get_close_matches
BASE_DIR          = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
condition_encoder = joblib.load(os.path.join(BASE_DIR, 'model', 'condition_encoder.pkl'))
drug_encoder      = joblib.load(os.path.join(BASE_DIR, 'model', 'drug_encoder.pkl'))
KNOWN_CONDITIONS  = condition_encoder.classes_.tolist()

# ── LOAD RAW DATA ────────────────────────────────────────────
print("Loading data...")
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
train_df = pd.read_csv(os.path.join(BASE_DIR, 'dataset', 'drugsComTrain_raw.csv'), low_memory=False)
test_df  = pd.read_csv(os.path.join(BASE_DIR, 'dataset', 'drugsComTest_raw.csv'),  low_memory=False)
df = pd.concat([train_df, test_df], ignore_index=True)
df = df[['condition', 'drugName', 'rating']].copy()
df.dropna(subset=['condition', 'drugName'], inplace=True)
df = df[~df['condition'].str.contains(r'\d', na=True)]
df['condition'] = df['condition'].str.strip().str.lower()
df['drugName']  = df['drugName'].str.strip().str.lower()
print(f"Data loaded: {len(df)} records")

# ── ALLERGY DATABASE ─────────────────────────────────────────
COMMON_ALLERGIES = {
    "penicillin"  : "May cause rash, hives, anaphylaxis",
    "sulfa"       : "May cause skin rash and kidney issues",
    "aspirin"     : "May cause stomach bleeding",
    "ibuprofen"   : "May cause stomach ulcers",
    "codeine"     : "May cause breathing problems",
    "morphine"    : "May cause severe breathing difficulty",
    "tetracycline": "May cause liver damage",
    "erythromycin": "May cause severe stomach upset",
    "metformin"   : "May cause lactic acidosis",
    "lisinopril"  : "May cause severe cough and angioedema",
    "sertraline"  : "May cause serotonin syndrome",
    "amoxicillin" : "May cause allergic reaction",
}

def get_recommendations(condition, user_allergies=None, top_n=5):
    condition = condition.strip().lower()

    # Check if condition exists
    if condition not in KNOWN_CONDITIONS:
    # Smart fuzzy matching
        close_matches = get_close_matches(
            condition, 
            KNOWN_CONDITIONS, 
            n=5, 
            cutoff=0.4
        )
    # Also search by partial word
        partial = [c for c in KNOWN_CONDITIONS 
                    if any(word in c for word in condition.split())]
    
    # Combine both
        suggestions = list(dict.fromkeys(close_matches + partial))[:5]
    
        return {
            "status"  : "error",
            "message" : f"'{condition}' not found. Did you mean one of these?",
            "similar" : suggestions
       }

    # Filter data for this condition
    cdf = df[df['condition'] == condition].copy()

    # Calculate stats per drug
    stats = cdf.groupby('drugName')['rating'].agg(['mean','count']).reset_index()
    stats.columns = ['drugName', 'avg_rating', 'review_count']

    # Weighted score = 60% rating + 40% review popularity
    max_reviews = stats['review_count'].max()
    stats['score'] = (
        (stats['avg_rating'] / 10) * 0.6 +
        (stats['review_count'] / max_reviews) * 0.4
    )

    # Sort by score descending
    stats = stats.sort_values('score', ascending=False).head(top_n)

    # Build allergy list
    all_allergies = []
    if user_allergies:
        all_allergies = [a.strip().lower() for a in user_allergies]

    # Build recommendations
    recommendations = []
    alerts = []

    for _, row in stats.iterrows():
        name    = row['drugName']
        rating  = round(row['avg_rating'], 1)
        reviews = int(row['review_count'])
        score   = round(row['score'] * 100, 1)

        # Check allergies
        is_allergic    = False
        allergy_reason = ""

        if name in all_allergies:
            is_allergic    = True
            allergy_reason = "You marked this as an allergy"

        for key, reason in COMMON_ALLERGIES.items():
            if key in name:
                is_allergic    = True
                allergy_reason = reason
                break

        drug_info = {
            "drug_name"    : name,
            "avg_rating"   : rating,
            "confidence"   : score,
            "review_count" : reviews,
            "is_safe"      : not is_allergic,
            "alert"        : allergy_reason if is_allergic else None
        }
        recommendations.append(drug_info)
        if is_allergic:
            alerts.append({"drug": name, "reason": allergy_reason})

    return {
        "status"          : "success",
        "condition"       : condition,
        "recommendations" : recommendations,
        "allergy_alerts"  : alerts,
        "total_alerts"    : len(alerts)
    }


def print_results(result):
    if result["status"] == "error":
        print(f"\n❌ {result['message']}")
        if result.get("similar"):
            print(f"💡 Did you mean: {', '.join(result['similar'])}")
        return

    print(f"\n{'='*50}")
    print(f"  💊 Recommendations for: {result['condition'].title()}")
    print(f"{'='*50}")

    if result["allergy_alerts"]:
        print(f"\n⚠️  ALLERGY ALERTS:")
        for a in result["allergy_alerts"]:
            print(f"   🔴 {a['drug'].title()} → {a['reason']}")

    print(f"\n📋 Top Recommendations:")
    for i, d in enumerate(result["recommendations"], 1):
        status = "🔴 ALLERGY" if not d["is_safe"] else "✅ Safe"
        print(f"\n  {i}. {d['drug_name'].title()}")
        print(f"     Rating     : {d['avg_rating']}/10")
        print(f"     Score      : {d['confidence']}%")
        print(f"     Reviews    : {d['review_count']}")
        print(f"     Status     : {status}")
        if d["alert"]:
            print(f"     ⚠️  Warning : {d['alert']}")

    print(f"\n{'='*50}\n")


# ── TESTS ────────────────────────────────────────────────────
if __name__ == "__main__":

    print("\n🧪 TEST 1: Depression (should show well-reviewed drugs first)")
    print_results(get_recommendations("depression"))

    print("\n🧪 TEST 2: Depression with sertraline allergy")
    print_results(get_recommendations("depression", user_allergies=["sertraline"]))

    print("\n🧪 TEST 3: ADHD")
    print_results(get_recommendations("adhd"))

    print("\n🧪 TEST 4: Unknown condition")
    print_results(get_recommendations("xyz disease"))
