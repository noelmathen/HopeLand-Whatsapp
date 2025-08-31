# app.py
from hopeland_bot import create_app

app = create_app()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", "3000"))
    app.run(host="0.0.0.0", port=port)
