\# Database relationships



```mermaid

erDiagram

&#x20;   TENANTS ||--o{ DOCUMENTS : owns

&#x20;   DOCUMENTS ||--o{ CHUNKS : contains

&#x20;   TENANTS ||--o{ CONVERSATIONS : has



&#x20;   TENANTS {

&#x20;       bigint tenant\_id PK

&#x20;       text name UK

&#x20;       timestamptz created\_at

&#x20;   }



&#x20;   DOCUMENTS {

&#x20;       bigint document\_id PK

&#x20;       bigint tenant\_id FK

&#x20;       text title

&#x20;       text filename

&#x20;       text content\_type

&#x20;       bigint size\_bytes

&#x20;       text storage\_path

&#x20;       text content\_hash

&#x20;       timestamptz created\_at

&#x20;   }



&#x20;   CHUNKS {

&#x20;       bigint chunk\_id PK

&#x20;       bigint document\_id FK

&#x20;       bigint tenant\_id FK

&#x20;       integer chunk\_index

&#x20;       text content

&#x20;       vector embedding

&#x20;       timestamptz created\_at

&#x20;   }



&#x20;   CONVERSATIONS {

&#x20;       bigint conversation\_id PK

&#x20;       bigint tenant\_id FK

&#x20;       text title

&#x20;       jsonb messages

&#x20;       timestamptz created\_at

&#x20;       timestamptz updated\_at

&#x20;   }

```



`documents` also has a unique constraint on `(tenant\_id, content\_hash)`.

