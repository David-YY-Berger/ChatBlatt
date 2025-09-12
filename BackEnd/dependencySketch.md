## Project Dependencies

```mermaid
graph TD
    %% Shared utilities
    subgraph Utils
        FileUtils["File Utils"]
    end

    %% DataObjects
    subgraph DataObjects
        Answer
        Source
    end
    
    %% General
    subgraph General
        Paths
        System_Functions
    end

    %% Core modules
    Filters --> SourceType
    Source --> Filters
    Source --> SourceType
    Source --> General
    Answer --> Filters
    Answer --> SourceType
    Answer --> General

    DB --> DataObjects
    DB --> Utils

    %% Higher-level modules
    FilterManager --> DB
    FilterManager --> DataObjects
    FilterManager --> Utils

    LMM --> DB
    LMM --> DataObjects
    LMM --> Utils

    FAISS --> DB
    FAISS --> DataObjects
    FAISS --> Utils

    %% Main application
    Main --> Filters
    Main --> DataObjects
    Main --> DB
    Main --> FilterManager
    Main --> LMM
    Main --> FAISS
    Main --> Utils

    DB_Populator --> Filters
    DB_Populator --> DataObjects
    DB_Populator --> DB
    DB_Populator --> FilterManager
    DB_Populator --> LMM
    DB_Populator --> FAISS
    DB_Populator --> Utils

    %% External interfaces
    FrontendAPIHandler --> Main
    QA --> Main

    %% Explicit dependency: Utils depends on DataObjects
    Utils --> DataObjects

    

