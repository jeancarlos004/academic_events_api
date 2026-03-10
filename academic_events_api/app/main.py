import os
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Cargar .env si existe (backend/.env)
# Línea actual (busca dos niveles arriba)
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path)
    except Exception:
        # Si python-dotenv no está instalado, seguimos sin .env
        pass

app = FastAPI(title="Academic Events Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Opción A (recomendada): Groq API (estable, sin Colab ni ngrok)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

# Opción B: Colab/ngrok (si decides usarlo)
# También puedes setearlo por .env con COLAB_CHAT_URL=...
COLAB_CHAT_URL = os.getenv("COLAB_CHAT_URL", "").strip()


@app.get("/")
def root():
    return {"message": "Backend funcionando correctamente"}


@app.get("/health")
def health():
    """Estado del backend y disponibilidad de Groq/Colab."""
    status = {"backend": "ok", "groq_configured": bool(GROQ_API_KEY)}

    if not COLAB_CHAT_URL:
        status["colab"] = {"status": "not_configured"}
        return status

    # Health de Colab (si existe endpoint /health); si no existe, lo marcamos como desconocido.
    try:
        r = requests.get(
            COLAB_CHAT_URL.replace("/chat", "/health"),
            headers={"ngrok-skip-browser-warning": "true"},
            timeout=5,
        )
        if r.status_code == 200:
            try:
                status["colab"] = r.json()
            except Exception:
                status["colab"] = {"status": "ok", "note": "health no-JSON"}
        else:
            status["colab"] = {"status": "error", "http_status": r.status_code}
    except Exception as e:
        status["colab"] = {"status": "unreachable", "error": str(e)}

    return status


def _chat_with_groq(message: str) -> str:
    from groq import (
        Groq,
        APITimeoutError,
        APIConnectionError,
        AuthenticationError,
        RateLimitError,
        APIStatusError,
        GroqError,
    )

    try:
        client = Groq(api_key=GROQ_API_KEY, timeout=20.0)
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente especializado en la plataforma de gestión de eventos académicos "
                        "institucionales. Responde en español, claro y práctico."
                    ),
                },
                {"role": "user", "content": message},
            ],
            max_tokens=250,
            temperature=0.6,
            top_p=0.9,
        )
        return (resp.choices[0].message.content or "").strip()
    except AuthenticationError:
        raise HTTPException(status_code=502, detail="GROQ_API_KEY inválida o no autorizada.")
    except RateLimitError:
        raise HTTPException(status_code=429, detail="Límite de Groq alcanzado. Intenta más tarde.")
    except APITimeoutError:
        raise HTTPException(status_code=504, detail="Groq tardó demasiado. Intenta con un mensaje más corto.")
    except APIConnectionError:
        raise HTTPException(status_code=503, detail="No se pudo conectar a Groq (red/firewall).")
    except APIStatusError as e:
        raise HTTPException(status_code=502, detail=f"Groq devolvió error HTTP: {str(e)}")
    except GroqError as e:
        raise HTTPException(status_code=502, detail=f"Error Groq: {str(e)}")


@app.post("/chat")
def chat(body: dict):
    message = body.get("message", "").strip()

    if not message:
        raise HTTPException(status_code=400, detail="Mensaje vacío")
    if len(message) > 1000:
        raise HTTPException(status_code=400, detail="Mensaje demasiado largo")

    # 1) Si hay GROQ_API_KEY, usamos Groq (recomendado)
    if GROQ_API_KEY:
        response = _chat_with_groq(message)
        return {"response": response}

    # 2) Si no hay Groq configurado, intentamos Colab/ngrok
    if not COLAB_CHAT_URL:
        raise HTTPException(
            status_code=503,
            detail="No hay proveedor AI configurado. Configura GROQ_API_KEY o COLAB_CHAT_URL en el .env del backend.",
        )

    try:
        r = requests.post(
            COLAB_CHAT_URL,
            json={"message": message},
            headers={"ngrok-skip-browser-warning": "true"},
            timeout=30,
        )
        r.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="No se puede conectar al servicio AI (Colab/ngrok). Verifica que el Notebook esté corriendo.",
        )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="El servicio AI (Colab/ngrok) tardó demasiado. Intenta con un mensaje más corto.",
        )
    except requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Error del servicio AI (Colab/ngrok): {str(e)}")

    try:
        result = r.json()
    except Exception:
        raise HTTPException(
            status_code=502,
            detail=f"Respuesta inválida del servicio AI (Colab/ngrok) (status {r.status_code})",
        )

    return {"response": result.get("response", "")}


# Exportar la app principal para evitar confusión de entrypoints.
# Si arrancas uvicorn apuntando a academic_events_api.app.main:app, igual tendrás /api/v1 y todos los routers.
from academic_events_api.main import app as app  # noqa: E402,F401

