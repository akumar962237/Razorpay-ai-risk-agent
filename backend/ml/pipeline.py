from pathlib import Path
import argparse, json, math
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, average_precision_score, confusion_matrix
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[2]
FEATURES = ["Time","Amount"] + [f"V{i}" for i in range(1,29)]

def validate(df):
    missing = [c for c in FEATURES + ["Class"] if c not in df.columns]
    if missing: raise ValueError(f"Missing required columns: {missing}")
    if df["Class"].isna().any(): raise ValueError("Class contains missing values")
    if not set(df["Class"].unique()).issubset({0,1}): raise ValueError("Class must be 0/1")
    return df[FEATURES + ["Class"]].copy()

def threshold_search(y, p, fp_cost=1.0, fn_cost=10.0):
    rows=[]
    for t in np.arange(0.05,0.951,0.01):
        pred=(p>=t).astype(int)
        cm=confusion_matrix(y,pred,labels=[0,1])
        tn,fp,fn,tp=cm.ravel()
        precision=precision_score(y,pred,zero_division=0)
        recall=recall_score(y,pred,zero_division=0)
        f1=f1_score(y,pred,zero_division=0)
        cost=fp*fp_cost+fn*fn_cost
        rows.append([t,precision,recall,f1,fp,fn,tp,tn,cost])
    out=pd.DataFrame(rows,columns=["threshold","precision","recall","f1","fp","fn","tp","tn","illustrative_cost"])
    # Prefer high recall, but enforce a minimum precision where possible.
    candidates=out[out.precision>=0.50]
    if len(candidates)==0: candidates=out
    best=candidates.sort_values(["illustrative_cost","f1"],ascending=[True,False]).iloc[0]
    return out,best

def main(path):
    df=validate(pd.read_csv(path)).sort_values("Time").reset_index(drop=True)
    n=len(df); cut=int(n*0.8); val_cut=int(cut*0.8)
    train=df.iloc[:val_cut]; val=df.iloc[val_cut:cut]; test=df.iloc[cut:]
    Xtr=train[FEATURES]; ytr=train.Class
    Xv=val[FEATURES]; yv=val.Class
    Xt=test[FEATURES]; yt=test.Class

    models={
      "logistic":Pipeline([("scale",StandardScaler()),("model",LogisticRegression(max_iter=2000,class_weight="balanced",C=0.5))]),
      "hist_gradient_boosting":HistGradientBoostingClassifier(max_iter=250,learning_rate=0.08,max_leaf_nodes=31,l2_regularization=1.0,random_state=42)
    }
    comparison=[]
    fitted={}
    for name,m in models.items():
        m.fit(Xtr,ytr)
        pv=m.predict_proba(Xv)[:,1]
        comparison.append({"model":name,"validation_pr_auc":float(average_precision_score(yv,pv))})
        fitted[name]=m
    best_name=max(comparison,key=lambda x:x["validation_pr_auc"])["model"]
    best_model=fitted[best_name]
    pv=best_model.predict_proba(Xv)[:,1]
    thresholds,best=threshold_search(yv,pv)
    # Refit selected model on train+validation only; test stays untouched.
    final= models[best_name]
    final.fit(pd.concat([Xtr,Xv]),pd.concat([ytr,yv]))
    pt=final.predict_proba(Xt)[:,1]
    threshold=float(best["threshold"])
    pred=(pt>=threshold).astype(int)
    cm=confusion_matrix(yt,pred,labels=[0,1]).tolist()
    metrics={
      "dataset_rows":n,"fraud_count":int(df.Class.sum()),"fraud_rate":float(df.Class.mean()),
      "train_rows":len(train),"validation_rows":len(val),"test_rows":len(test),
      "selected_model":best_name,"selected_threshold":threshold,
      "test_precision":float(precision_score(yt,pred,zero_division=0)),
      "test_recall":float(recall_score(yt,pred,zero_division=0)),
      "test_f1":float(f1_score(yt,pred,zero_division=0)),
      "test_pr_auc":float(average_precision_score(yt,pt)),
      "confusion_matrix":{"labels":["legitimate","fraud"],"matrix":cm},
      "illustrative_cost_assumption":{"false_positive":1,"false_negative":10},
      "validation_model_comparison":comparison
    }
    outdir=ROOT/"backend/reports"; outdir.mkdir(parents=True,exist_ok=True)
    modeldir=ROOT/"backend/models"; modeldir.mkdir(parents=True,exist_ok=True)
    joblib.dump({"model":final,"threshold":threshold,"features":FEATURES},modeldir/"final_model.joblib")
    (modeldir/"model_metadata.json").write_text(json.dumps({"source":"public ULB/MLG credit-card fraud benchmark","features":FEATURES,"selected_model":best_name,"threshold":threshold},indent=2))
    (outdir/"metrics.json").write_text(json.dumps(metrics,indent=2))
    (outdir/"confusion_matrix.json").write_text(json.dumps(metrics["confusion_matrix"],indent=2))
    thresholds.to_csv(outdir/"thresholds.csv",index=False)
    (outdir/"evaluation.md").write_text(
      "# Benchmark Evaluation\n\n"
      f"- Rows: {n:,}\n- Fraud cases: {int(df.Class.sum()):,}\n- Fraud rate: {df.Class.mean():.4%}\n"
      f"- Selected model: `{best_name}`\n- Threshold: `{threshold:.3f}`\n"
      f"- Test precision: **{metrics['test_precision']:.4f}**\n"
      f"- Test recall: **{metrics['test_recall']:.4f}**\n"
      f"- Test F1: **{metrics['test_f1']:.4f}**\n"
      f"- Test PR-AUC: **{metrics['test_pr_auc']:.4f}**\n\n"
      "The final test set was not used for threshold selection. The illustrative cost assigns 1 unit to a false positive and 10 to a false negative; this is a modeling assumption, not a Razorpay business cost estimate.\n"
    )
    processed=ROOT/"data/processed"; processed.mkdir(parents=True,exist_ok=True)
    df.sample(min(5000,len(df)),random_state=42).to_csv(processed/"benchmark_sample.csv",index=False)
    print(json.dumps(metrics,indent=2))

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",required=True)
    main(ap.parse_args().data)
