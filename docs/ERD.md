\# Database relationships



Think of each tenant as a customer or organization.



\- One tenant can have many documents.

\- One document can be split into many chunks.

\- One tenant can have many conversations.

\- Each document belongs to one tenant.

\- Each chunk belongs to one document and one tenant.

\- Each conversation belongs to one tenant.



```mermaid

erDiagram

&#x20;   TENANTS ||--o{ DOCUMENTS : owns

&#x20;   DOCUMENTS ||--o{ CHUNKS : contains

&#x20;   TENANTS ||--o{ CONVERSATIONS : has

