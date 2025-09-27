from fastapi import FastAPI, Response, Cookie
import uvicorn

app = FastAPI()

@app.post("/login")
def login(response: Response):
    response.set_cookie(
        key="token",
        value="abc123",
        httponly=True,
        secure=False,
        samesite="lax",
    )
    return {"message": "cookie set"}

@app.get("/me")
def me(token: str | None = Cookie(None)):
    return {"token": token}

uvicorn.run(app, host="localhost", port="8080", log_level="debug")