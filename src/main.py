from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import os
import uvicorn
from dotenv import load_dotenv
from src.orchestrator import orchestrator

load_dotenv()

app = FastAPI()

class QueryRequest(BaseModel):
    query: str
    propertyId: Optional[str] = None

@app.post("/query")
async def handle_query(request: QueryRequest):
    try:
        response = orchestrator.route_request(request.query, request.propertyId)
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
