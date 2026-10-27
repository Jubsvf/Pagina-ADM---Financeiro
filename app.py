"""
Ponto de entrada padrão para a aplicação (compatível com Vercel Serverless e WSGI local).
Importa a aplicação Flask configurada em server.py.
"""
from server import app

if __name__ == "__main__":
    app.run()
