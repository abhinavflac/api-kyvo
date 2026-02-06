from fastapi import FastAPI
from pydantic import BaseModel
from app.kyvo_engine import KyvoEngine
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://kyvo-web.vercel.app",
        "http://localhost:4173"
        ],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = KyvoEngine()


class QueryRequest(BaseModel):
    query: str



@app.post("/recommend")
def recommend(req: QueryRequest):
    try:
        return engine.run(req.query)
    except Exception as e:
        import traceback
        return {
            "error": "Internal Server Error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }

# @app.get("/api/suggestions")
# def get_suggestions():
#     return {
#         "items": [
#             '7200-B-XL-JP',
#             '7201-B-XL-JP',
#             '7202-B-XL-JP',
#             'Angular contact ball bearing',
#             'Angular contact bearing 40° contact angle',
#             'High speed bearing for spindle',
#             'Bearing with 10mm bore',
#             'Bearing with 12mm bore',
#             'Bearing with 15mm bore',
#             'Bearing with 30mm outer diameter',
#             'Bearing with 32mm outer diameter',
#             'Bearing with 35mm outer diameter',
#             'SKF angular contact bearing',
#             'Schaeffler angular contact bearing',
#             'NSK angular contact bearing',
#             'FAG angular contact bearing',
#             'High limiting speed grease bearing',
#             'Compare dynamic load ratings',
#             'Bearing for low friction application',
#             'Bearing for compact assemblies',
#         ]
#     }


@app.get("/api/api-health")
def health_check():
    return {"status": "ok"}

@app.get("/results")
def get_results():
    return {"results":" Sample results from KyvoEngine"}

@app.get("/")
def read_root():
    return {"Hello": "World"}