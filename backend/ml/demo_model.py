from pathlib import Path
import json
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

ROOT=Path(__file__).resolve().parents[2]
rng=np.random.default_rng(42); n=10000
X=rng.normal(size=(n,30)); y=(X[:,0]+0.8*X[:,1]+0.5*X[:,2]>2.2).astype(int)
m=RandomForestClassifier(n_estimators=150,class_weight="balanced",random_state=42)
m.fit(X,y)
p=ROOT/"backend/models"; p.mkdir(parents=True,exist_ok=True)
joblib.dump({"model":m,"threshold":0.5,"features":["Time","Amount"]+[f"V{i}" for i in range(1,29)]},p/"demo_model.joblib")
(p/"demo_metadata.json").write_text(json.dumps({"mode":"DEMO ONLY","warning":"Not benchmark performance"},indent=2))
print("Demo model generated.")
