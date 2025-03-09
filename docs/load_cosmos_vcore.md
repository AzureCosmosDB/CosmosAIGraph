# CosmosAIGraph : Load Azure Cosmos DB vCore

## Configuration

This page assumes that you have set the following environment variables:

```
CAIG_GRAPH_SOURCE_TYPE              <-- must be set to 'cosmos_vcore'
CAIG_AZURE_MONGO_VCORE_CONN_STR     <-- this value is unique to your Azure deployment

CAIG_GRAPH_SOURCE_DB                <-- defaults to 'caig'
CAIG_GRAPH_SOURCE_CONTAINER         <-- defaults to 'libraries'
CAIG_CONFIG_CONTAINER               <-- defaults to 'config'
CAIG_CONVERSATIONS_CONTAINER        <-- defaults to 'conversations'
CAIG_FEEDBACK_CONTAINER             <-- defaults to 'feedback'
```

## Create the Cosmos DB Mongo vCore Collections and Indexes

Navigate to the **impl\app** directory of this repo and execute
the following commands:

```
> .\venv.ps1                      <-- create the python virtual environment

> .\venv\Scripts\Activate.ps1     <-- activate the python virtual environment

> python main_vcore.py create_vcore_collections_and_indexes
```

### Manually create the Vector Search Index

See https://learn.microsoft.com/en-us/azure/cosmos-db/mongodb/vcore/vector-search
for the documentation on this index type.

In your mongo shell program excute the following command in your database.

```
use caig

db.runCommand({
  createIndexes: 'libraries',
  indexes: [
    {
      name: 'vectorSearchIndex',
      key: {
        "embedding": "cosmosSearch"
      },
      cosmosSearchOptions: {
        kind: 'vector-ivf',
        numLists: 20,
        similarity: 'COS',
        dimensions: 1536
      }
    }
  ]
});
```

### Verify the Indexes several Containers

First, get the list of containers.  These four container names should be present.

```
[mongos] caig> db.getCollectionNames()
[ 'libraries', 'cache', 'config', 'conversations' ]
```

Next, run the following **getIndexes()** command for each container to 
confirm that the necessary indexes have been created.  They should look
like the following.

```
db.cache.getIndexes()

[
  { v: 2, key: { _id: 1 }, name: '_id_' },
  { v: 2, key: { cache_key: 1 }, name: 'cache_key_1' }
]
```

```
db.config.getIndexes()

[
  { v: 2, key: { _id: 1 }, name: '_id_' },
  { v: 2, key: { id: 1 }, name: 'id_1' }
]
```

```
db.conversations.getIndexes()

[
  { v: 2, key: { _id: 1 }, name: '_id_' },
  { v: 2, key: { conversation_id: 1 }, name: 'conversation_id_1' },
  { v: 2, key: { created_date: 1 }, name: 'created_date_1' },
  { v: 2, key: { created_at: 1 }, name: 'created_at_1' }
]
```

```
db.libraries.getIndexes()

[
  { v: 2, key: { _id: 1 }, name: '_id_' },
  { v: 2, key: { id: 1 }, name: 'id_1' },
  { v: 2, key: { name: 1 }, name: 'name_1' },
  { v: 2, key: { libtype: 1 }, name: 'libtype_1' },
  {
    v: 2,
    key: { embedding: 'cosmosSearch' },
    name: 'vectorSearchIndex',
    cosmosSearchOptions: {
      kind: 'vector-ivf',
      numLists: 20,
      similarity: 'COS',
      dimensions: 1536
    }
  }
]
```

---

## Load the Library data into Cosmos DB Mongo vCore

Navigate to the **impl\app** directory of this repo and execute
the following commands:

```
> .\venv\Scripts\Activate.ps1     <-- activate the python virtual environment

> python main_vcore.py load_vcore_with_library_documents

> python main_vcore.py persist_entities
```

The **load_vcore_with_library_documents** function loads the **libraries**
container, while the **persist_entities** function loads one document
into the **config** container.

### Verifying the Data Load

In your mongosh program, execute the following commands:

#### Document Queries

```
db.libraries.findOne()
... you'll see a random document from the libraries container here ...

db.libraries.find({name: "flask"})
... see the flask document ...
```

The JSON output of the above flask query should look identical
to file impl/data/pypi/wrangled_libs/flask.json in this repo.

#### Document Counts

```
db.libraries.countDocuments()
10855

db.config.countDocuments()
1
```

10855 is the expected number of documents in the libraries
container, while one document is expected in the config container.

The number 10855 corresponds to the number of JSON documents in directory 
'impl/data/pypi/wrangled_libs/' in this repo.
