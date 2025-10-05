from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="HabitatCanvas API",
    version="0.1.0",
    description="HabitatCanvas API - Generative Layout Studio for Space Habitats",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "HabitatCanvas API", "version": "0.1.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2025-10-05T10:00:00Z"}

@app.get("/api/v1/health")
async def health_check_v1():
    return {"status": "healthy", "timestamp": "2025-10-05T10:00:00Z"}

# Basic endpoints for frontend compatibility
@app.post("/api/v1/layouts/generate")
async def generate_layouts(request: dict):
    return [
        {
            "layoutId": "demo-layout-1",
            "envelopeId": "demo-envelope",
            "modules": [
                {
                    "module_id": "sleep-1",
                    "type": "sleep_quarter",
                    "position": [0, 0, 0],
                    "rotation_deg": 0,
                    "connections": []
                }
            ],
            "kpis": {
                "meanTransitTime": 45.2,
                "egressTime": 120.0,
                "massTotal": 15000.0,
                "powerBudget": 3500.0,
                "thermalMargin": 0.15,
                "lssMargin": 0.25,
                "stowageUtilization": 0.85
            },
            "explainability": "Demo layout with basic module placement"
        }
    ]

@app.get("/api/v1/layouts/")
async def get_layouts():
    return []

@app.get("/api/v1/layouts/{layout_id}")
async def get_layout(layout_id: str):
    if layout_id == "demo-layout-1":
        return {
            "layoutId": "demo-layout-1",
            "envelopeId": "demo-envelope",
            "modules": [
                {
                    "module_id": "sleep-1",
                    "type": "sleep_quarter",
                    "position": [0, 0, 0],
                    "rotation_deg": 0,
                    "connections": []
                }
            ],
            "kpis": {
                "meanTransitTime": 45.2,
                "egressTime": 120.0,
                "massTotal": 15000.0,
                "powerBudget": 3500.0,
                "thermalMargin": 0.15,
                "lssMargin": 0.25,
                "stowageUtilization": 0.85
            },
            "explainability": "Demo layout with basic module placement"
        }
    return {"error": "Layout not found"}, 404

@app.put("/api/v1/layouts/{layout_id}")
async def update_layout(layout_id: str, layout: dict):
    # For demo purposes, just return the updated layout
    return layout

@app.delete("/api/v1/layouts/{layout_id}")
async def delete_layout(layout_id: str):
    return {"message": "Layout deleted successfully"}

@app.get("/api/v1/envelopes/")
async def get_envelopes():
    return []

@app.get("/api/v1/module-library/")
async def get_modules():
    return [
        {
            "module_id": "sleep-1",
            "type": "sleep_quarter",
            "name": "Sleep Quarter",
            "bbox_m": {"x": 2.0, "y": 2.0, "z": 2.5},
            "mass_kg": 500.0,
            "power_w": 100.0,
            "stowage_m3": 1.5,
            "connectivity_ports": ["port1"],
            "adjacency_preferences": ["galley"],
            "adjacency_restrictions": ["mechanical"]
        }
    ]

if __name__ == "__main__":
    uvicorn.run(
        "simple_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )