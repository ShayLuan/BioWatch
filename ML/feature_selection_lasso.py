import os
import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression

_HERE = os.path.dirname(os.path.abspath(__file__))

# 1. Load scaled mRMR features
train_df = pd.read_csv(os.path.join(_HERE, "X_train_scaled.csv"))
X_train = train_df.drop(columns=['Target'])
y_train = train_df['Target']

print("--- Running Phase 2: LASSO Regularization ---")

# 2. Fit Multinomial LASSO Framework
lasso = LogisticRegression(
    penalty='elasticnet',
    solver='saga',
    l1_ratio=1,
    C=0.5,
    max_iter=5000,
    random_state=42,
    class_weight='balanced'
)
lasso.fit(X_train, y_train)

# 3. Structural Sparsity Check
print("\nLASSO Sparsity Output (Beta Coefficients per class):")
features_to_keep = []

for i, label in enumerate(lasso.classes_):
    print(f"\n[{label} Beta Weights]")
    for feature, coef in zip(X_train.columns, lasso.coef_[i]):
        print(f"  {feature}: {coef:.4f} " + ("[DROPPED]" if coef == 0 else "[ACTIVE]"))
        if coef != 0 and feature not in features_to_keep:
            features_to_keep.append(feature)

# Save the explicitly non-zero features list
pd.Series(features_to_keep).to_csv(
    os.path.join(_HERE, "lasso_surviving_features.csv"), index=False, header=False
)
print(f"\nFeatures that survived LASSO pruning: {features_to_keep}")

# 4. Persist the trained model so ml_service.py can load it at inference time
joblib.dump(lasso, os.path.join(_HERE, "lasso_model.pkl"))
print("Saved lasso_model.pkl")
