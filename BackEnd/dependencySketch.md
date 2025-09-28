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
        Entity
        NER
    end
    
    %% General
    subgraph General
        Paths
        System_Functions
    end

    %% Enums
    subgraph Enums
        TimePeriod
        EntityOrNERType
    end

    %% Core modules
    Source --> Enums
    Source --> General
    Answer --> Enums
    Answer --> General
    Entity --> Enums
    NER --> Enums

    DB --> DataObjects
    DB --> Utils
    
    Utils --> DataObjects

    %% Higher-level modules
    EntityNerManager --> DB
    EntityNerManager --> DataObjects
    EntityNerManager --> Utils

    LMM --> DB
    LMM --> DataObjects
    LMM --> Utils

    FAISS --> DB
    FAISS --> DataObjects
    FAISS --> Utils

    %% Main application
    Main --> DataObjects
    Main --> DB
    Main --> EntityNerManager
    Main --> LMM
    Main --> FAISS
    Main --> Utils

    DB_Populator --> DataObjects
    DB_Populator --> DB
    DB_Populator --> EntityNerManager
    DB_Populator --> LMM
    DB_Populator --> FAISS
    DB_Populator --> Utils

    %% External interfaces
    FrontendAPIHandler --> Main
    QA --> Main

  
