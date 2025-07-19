from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .auth.router import router as auth_router
from .stalls.router import router as stalls_router
from .menus.router import router as menus_router
from .reviews.router import router as reviews_router
from .config import settings

app = FastAPI(
    title="Food Stall Finder API",
    description="API for finding and managing food stalls",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(stalls_router, prefix="/stalls", tags=["Food Stalls"])
app.include_router(menus_router, prefix="/menus", tags=["Menu Items"])
app.include_router(reviews_router, prefix="/reviews", tags=["Reviews"])

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to Food Stall Finder API"}

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)