---
title: Guardia Backend API
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# Guardia Backend API (FastAPI + Groq AI + PostgreSQL)

Plateforme de télésurveillance médicale enrichie par Groq AI.

## Variables d'environnement pour Hugging Face Space Settings > Variables and secrets

1. `GROQ_API_KEY`: Votre clé d'API Groq (obtenue sur https://console.groq.com)
2. `GROQ_ENABLED`: `true`
3. `JWT_SECRET`: `guardia_secret_key_production_2026` (ou votre clé sécurisée)
4. (Optionnel) `DATABASE_URL`: Votre URL PostgreSQL externe (si vide, PostgreSQL intégré démarre automatiquement)
5. `CORS_ORIGINS`: `https://guardia-psi.vercel.app`

## URL de votre API en production
Une fois déployé, votre backend est accessible à :
`https://<votre-space-name>.hf.space`

Renseignez cette URL sur Vercel :
`VITE_API_URL=https://<votre-space-name>.hf.space`
