import pandas as pd
from sklearn.linear_model import LogisticRegression

# 1. Load scaled mRMR features
train_df = pd.read_csv("X_train_scaled.csv")
X_train = train_df.drop(columns=['Target'])
y_train = train_df['Target']

print("--- Running Phase 2: LASSO Regularization ---")

# 2. Fit Multinomial LASSO Framework
lasso = LogisticRegression(
    penalty='l1',
    solver='saga',
    C=0.5,
    max_iter=5000,
    random_state=42,
    class_weight='balanced'
)
lasso.fit(X_train, y_train)

# 3. Structural Sparsity Check
print("\nLASSO Sparsity Output (Beta Coefficients per class):")
classes = ['Low Risk', 'Medium Risk', 'High Risk']
features_to_keep = []

for i, label in enumerate(classes):
    print(f"\n[{label} Beta Weights]")
    for feature, coef in zip(X_train.columns, lasso.coef_[i]):
        print(f"  {feature}: {coef:.4f} " + ("❌ DROPPED BY LASSO" if coef == 0 else "✅ ACTIVE"))
        if coef != 0 and feature not in features_to_keep:
            features_to_keep.append(feature)

# Save the explicitly non-zero features list for the next file
pd.Series(features_to_keep).to_csv("lasso_surviving_features.csv", index=False, header=False)
print(f"\nFeatures that survived LASSO pruning: {features_to_keep}")