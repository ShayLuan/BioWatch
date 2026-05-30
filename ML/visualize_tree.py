import pandas as pd
import matplotlib.pyplot as plt
from sklearn.tree import DecisionTreeClassifier, plot_tree

# 1. Load Matrix
df = pd.read_csv("final_training_set.csv")
X = df[['Temperature_C', 'Turbidity_Max_48h', 'Flow_CFS', 'Temp_Rolling_Mean_48h']]
y = df['AMR_Risk_Class']

# 2. Fit a shallow, highly explainable decision tree
tree = DecisionTreeClassifier(max_depth=3, class_weight='balanced', random_state=42)
tree.fit(X, y)

# 3. Plot the explicit branching logic
plt.figure(figsize=(14, 8), dpi=300)
plot_tree(
    tree,
    feature_names=X.columns,
    class_names=['Low Risk', 'Medium Risk', 'High Risk'],
    filled=True,
    rounded=True,
    fontsize=10
)
plt.title("Environmental Tipping Points Driving AMR Risk Tiers", fontsize=14, fontweight='bold')
plt.savefig("environmental_proof_tree.png", bbox_inches='tight')
print("\nSuccess! Saved explicit decision flow logic to 'environmental_proof_tree.png'")