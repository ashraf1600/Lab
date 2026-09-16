import io
import json
import torch
from torchvision import models, transforms
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Private ViT Vision Model Service", version="1.0.0")

# Load Vision Transformer (ViT-B/16)
print("[*] Loading Vision Transformer (ViT-B/16) weights...")
weights = models.ViT_B_16_Weights.DEFAULT
model = models.vit_b_16(weights=weights)
model.eval()
preprocess = weights.transforms()
categories = weights.meta["categories"]
print("[*] ViT-B/16 Model loaded and ready!")

@app.get("/")
def root():
    return {
        "service": "VPC-Isolated ViT Inference Service",
        "model": "Vision Transformer (vit_b_16)",
        "network": "Private Subnet (Transit Gateway)",
        "status": "ready"
    }

@app.get("/health")
def health():
    return {"status": "healthy", "model_ready": True}

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (JPEG, PNG, etc.)")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        
        # Preprocess
        batch = preprocess(image).unsqueeze(0)
        
        # Inference
        with torch.no_grad():
            prediction = model(batch).squeeze(0).softmax(0)
            
        # Top 5 predictions
        top5_prob, top5_catid = torch.topk(prediction, 5)
        
        results = []
        for i in range(top5_prob.size(0)):
            results.append({
                "rank": i + 1,
                "label": categories[top5_catid[i]],
                "confidence": round(float(top5_prob[i]), 4)
            })
            
        return {
            "success": True,
            "filename": file.filename,
            "top_prediction": results[0]["label"],
            "confidence": results[0]["confidence"],
            "top_5": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
