# Statut autoevaluation

Ce document reprend les indicateurs de la fiche `input/autoevaluation.pdf` et
liste les preuves presentes dans le depot.

| Indicateur | Statut | Preuve |
| --- | --- | --- |
| Graph LangGraph correctement structure | Implemente | `backend/app/services/coach_service.py`, `backend/tests/test_coach_service.py` |
| Agent traite une FEN et determine la source appropriee | Implemente | `/api/v1/coach`, champ `selected_tools`, `backend/app/main.py` |
| Bonnes pratiques Python | Implemente | services separes, dataclasses, tests unitaires dans `backend/tests/` |
| Logique metier separee de la logique API | Implemente | `backend/app/services/*`, routeurs dans `backend/app/main.py` |
| Donnees Wikichess preprocesses et chunkees | Implemente | `backend/scripts/preprocess_wikichess.py`, `backend/app/data/opening_chunks.json` |
| Embeddings generes et stockes dans Milvus | Implemente | `EmbeddingService`, `embedding_model`, `backend/scripts/load_openings.py` |
| Recherche vectorielle pertinente pour les ouvertures | Implemente | `/api/v1/vector-search`, tests `backend/tests/test_vector_service.py` |
| Base vectorielle connectee au workflow LangGraph | Implemente | noeud `load_context` dans `ChessCoachWorkflow` |
| Pertinence des reponses agent | Implemente | Synthese deterministe dans `/api/v1/coach`, affichage Angular |
| Integration Lichess | Implemente | `/api/v1/moves`, noeud `load_theory` |
| Integration Stockfish | Implemente | `/api/v1/evaluate`, noeud `evaluate_position` |
| API YouTube | Implemente | `/api/v1/videos`, `OpeningVideoWorkflow` |
| Agent choisit des outils pertinents | Implemente | `selected_tools`, tests de workflow coach |
| Timeouts et erreurs d'API geres | Implemente | `warnings` coach, exceptions services, tests d'erreur |
| Docker Compose fonctionnel | Implemente | `docker-compose.yml` |
| Tous les services demarrent | Implemente | `docker compose up -d --build`, `docker compose ps` |
| Communication entre services | Implemente | proxy nginx, variables Docker, smoke checks README |
| Volumes persistants configures | Implemente | volumes MongoDB, Milvus, MinIO, etcd dans `docker-compose.yml` |
| Variables d'environnement integrees | Implemente | `.env.example`, `docker-compose.yml` |
| Application accessible depuis l'exterieur | Implemente | ports exposes `4200`, `8000`, `27017`, `19530` |
| Echiquier Angular integre | Implemente | `frontend/src/app/app.component.html`, `ngx-chess-board` |
| Positions FEN synchronisees | Implemente | `getFEN()` dans `AppComponent` |
| Recommandations agent pertinentes dans l'UI | Implemente | bloc `Conseil de l'agent`, bouton `Demander conseil` |
| Etats de chargement et erreurs geres | Implemente | `loadingCoach`, `coachError`, warnings |
| Experience utilisateur satisfaisante | Implemente | UI Angular avec analyse, ressources, videos et conseil |
| Benefices du systeme identifies | Implemente | `docs/system-note.md` |
| Limites techniques et business evaluees | Implemente | `docs/system-note.md` |
| Architecture coherente et realisable | Implemente | schema Mermaid dans `docs/system-note.md` |
| Estimations de couts pertinentes | Implemente | section faisabilite dans `docs/system-note.md` |
| Alternatives et roadmap identifiees | Implemente | recommandations dans `docs/system-note.md` |
| Capacite de presenter et demontrer les livrables | Implemente | `docs/demo-scenario.md`, collection Postman |

Le step 7, dedie au systeme avance d'analyse video sans implementation, est
documente separement dans `docs/video-analysis-system-note.md`: architecture
MCP, pipeline OpenCV/modele vision, faisabilite, couts build/opex, risques,
alternatives et roadmap.

Point de vigilance pour la soutenance: l'embedding par defaut est volontairement
leger pour garder le POC local rapide. La roadmap documente le remplacement par
un modele transformer multilingue si la qualite semantique devient prioritaire.
