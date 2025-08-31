## Project Dependencies

```mermaid
graph TD
    %% Shared utilities
    subgraph Utils
        General
        FileUtils["File Utils"]
    end

    %% Core modules
    Filters --> SourceType
    Source --> Filters
    Source --> SourceType
    DB --> Source
    DB --> Utils

    %% Higher-level modules
    FilterManager --> DB
    FilterManager --> Source
    FilterManager --> Utils

    LMM --> DB
    LMM --> Source
    LMM --> Utils

    FAISS --> DB
    FAISS --> Source
    FAISS --> Utils

    %% Main application
    Main --> Filters
    Main --> Source
    Main --> DB
    Main --> FilterManager
    Main --> LMM
    Main --> FAISS
    Main --> Utils

    %% External interfaces
    FrontendAPIHandler --> Main
    QA --> Filters
    QA --> Source
    QA --> DB
    QA --> FilterManager
    QA --> LMM
    QA --> FAISS
    QA --> Utils
