# Deployment

PostgreSQL stores business data and pgvector embeddings. Uploaded source files
are stored in the app-upload-data Docker volume. Redis uses append-only file
persistence for document processing messages.
