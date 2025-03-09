# CosmosAIGraph : FAQ

This page addresses some of the **Frequently Asked Questions**
about the CosmosAIGraph solution.

## List of Questions

- [Is CosmosAIGraph a supported Microsoft product?](#msft_product)
- [Is CosmosAIGraph the same as the Microsoft Research GraphRAG whitepaper?](#msr_graphrag)
- [Should I store my Docker images in DockerHub, too?](#dockerhub)
- [Do I have to use the Python programming language?](#why_python)
- [Does the in-memory graph scale to huge datasets?](#memory_scale)
- [Can the Graph be changed once it is loaded into memory?](#mutable_graph)
- [Do I have to use Azure Container Apps (ACA)?](#container_runtimes)
- [So, CosmosAIGraph is a "framework" like Spring Boot that I simply plug into?](#is_it_a_framework)
- [I'm just learning about Ontologies and OWL.  How should I create my graph schema?](#how_to_create_owl)
- [What are RDF Triples?](#what_are_triples)
- [Can I add additional data sources with the OmniRAG pattern, and how?](#omnirag_sources)
- [Do I have to use D3.js for web page graph visualizations?](#d3)
- [Should I store PDFs, images, and movies in Cosmos DB?](#binary_objects)
- [How should I load my data into Cosmos DB?](#how_to_populate_cosmos)
- [I don't understand the Bicep parameter names, can you explain?](#bicep_param_names)

---

## Answers

<a name="msft_product"></a>

**Q: Is CosmosAIGraph a supported Microsoft product?**

**A:** It is a reference implementation rather than a product.
Customers are free to use it as-is, or modify it for their needs.

The Cosmos DB Global Black Belt team created the solution and
support customers in its use.  We integrate customer feedback
and field experience into this evolving solution.

---

<a name="msr_graphrag"></a>

**Q: Is CosmosAIGraph the same as the Microsoft Research GraphRAG whitepaper?**

**A:** No.  This is a separate project, not related the MSR GraphRAG concept.
See https://www.microsoft.com/en-us/research/blog/graphrag-unlocking-llm-discovery-on-narrative-private-data/?msockid=1f6ce974c2e161512deefd31c3b760f3

The CosmosAIGraph solution differs in three significant ways:

- It implements the **OmniRAG** pattern, for n-number of RAG data sources.
- It uses **Microsoft Databases** (i.e. - Cosmos DB)
- It is supported by the Global Black Belt team during customer engagements.

---

<a name="dockerhub"></a>

**Q: Should I store my Docker images in DockerHub, too?**

**A:** No.  It is recommended that you use 
[Azure Container Registry (ACR)](https://learn.microsoft.com/en-us/azure/container-registry/) for your images for security purposes.

We use DockerHub for this public project, with public data, 
so that all customers can access it.

---

<a name="why_python"></a>

**Q: Do I have to use the Python programming language?**

**A:** For the Graph Microservice, yes, since the implementation
uses the [rdflib](https://pypi.org/project/rdflib/) Python library.

However, for the Web Application you can use any programming language
you'd like (i.e. - Java, C#, Node.js, etc.) as long as it can make
HTTP calls to the Graph Microservice.

Some customers only deploy the Graph Microservice and integrate
it, via HTTP calls, into their existing UI applications.

---

<a name="memory_scale"></a>

**Q: Does the in-memory graph scale to huge datasets?**

**A:** The idea is to store the bare minimum of data in the in-memory
graph that is sufficient for your graph query use-cases.  This is
usually a small subset of the attributes in your Cosmos DB documents.

We've tested an in-memory graph with over 20 million triples,
but much larger graphs are possible.

Azure Container Apps (ACA) workload profiles support up to 880 GB of memory, see https://learn.microsoft.com/en-us/azure/container-apps/workload-profiles-overview.  This enables huge in-memory graphs.  

Also, we recommend at least two instances of the graph service in ACA for high-availibility.  Example Bicep configuration shown below.

```
      scale: {
        maxReplicas: 2
        minReplicas: 2
      }
```

---

<a name="mutable_graph"></a>

**Q: Can the Graph be changed once it is loaded into memory?**

**A:** Yes, though the reference implementation doesn't demonstrate this.

One way to implement this is to use the Cosmos DB NoSQL API Change Feed
functionality to observe changes to the database, enqueue these, and
have the Graph Microservice(s) process these queued changes.

Alternatively, the Cosmos DB vCore API offers change-stream functionality
(currently in preview mode).

---

<a name="container_runtimes"></a>

**Q: Do I have to use Azure Container Apps (ACA)?**

**A:** No.  [Azure Kubernetes Service (AKS)](https://learn.microsoft.com/en-us/azure/aks/) is also recommended.

---

<a name="is_it_a_framework"></a>

**Q: So, CosmosAIGraph is a "framework" like Spring Boot that I simply plug into?**

**A:** No.  The CosmosAIGraph codebase is a reference implementation
rather than a framework.  It provides a working example and software patterns
that you may wish to use in your application.

It is expected that each customer will significantly modify the codebase
for their particular needs.

We recommend that customer skillsets include application programming
with Python, Web UI skills, and AI/LLM/Prompt skills.
While PySpark experience is useful, this solution is not based on Spark.

---

<a name="how_to_create_owl"></a>

**Q: I'm just learning about Ontologies and OWL.  How should I create my graph schema?**

**A:** There are several ways to do this, and in our opinion it's easier
to do than model relational databases.

One way is to simply create a Visio or similar diagram of the **vertices and edges**
of your graph, then use this visual model to manually author the corresponding
OWL XML syntax.  This is our recommended approach.

Please see the item below on **What are RDF Triples?**.  We use the terms 
vertices and edges here conceptually, but not for implementation.

Another way is to write a Python or other program to read and scan your input data,
usually before loading it into Cosmos DB.  The program identifies all of the entity
types, their attribute names and datatypes, and the relationships to other
entities.  This extracted "metadata" of your data can then be used to generate
your OWL file.  This approach has been successfully used with several customers.
As an additional bonus, the metadata can also be used to generate Python code,
such as the logic that reads Cosmos DB and populates the in-memory graph.

Yet another way is to leverage Generative AI to scan the data and generate
the OWL ontology.  This may be a more expensive and time-consuming process, 
however.

We recommend these two books on RDF, SPARQL, and OWL to accelerate your learning:
- https://www.oreilly.com/library/view/learning-sparql/9781449311285/
- https://www.oreilly.com/library/view/practical-rdf/0596002637/

---

<a name="what_are_triples"></a>

**Q: What are RDF Triples?**

**A:** RDF graph databases use "triples" of (subject, predicate, object) to implement the graph.

We used the terms **vertices and edges** above as concepts to help you visualize the graph,
but RDF graph databases don't actually use or implement vertices and edges.
Vertices and edges are concepts used in **LPG** graph databases, such as Neo4j
and Cosmos DB Gremlin.

**RDF instead uses "triples"** to implement the graph.
These consist of a tuple of **(subject, predicate, object)**.

For example, given these two conceptual triples:

```
Aleksey --> Works At --> Microsoft
Chris   --> Works At --> Microsoft
```

The RDF graph is then able to infer the relationship, or edge, between
Chris and Aleksey.  In our experience, this is a significant advantage 
of RDF over LPG, as **you don't need to explicitly create the edges**
in your graph.  We have seen many LPG graph project with sub-optimal
datasets as, over time, vertices get programatically deleted but their
corresponding edges often do not.  This leads to **orphan edges**
that can greatly reduce database performance.

The following are the actual triples in the reference implementation graph
relating to the **m26** python library.  Each line represents a triple.
The subjects, predicates, and objects are usually expressed as **URI**
values that correspond to your graph ontology, or **OWL** file.

Though these verbose values look inefficient, within the database they
become efficient data structures.

```
<http://cosmosdb.com/caig/pypi_m26> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://cosmosdb.com/caig#Lib> .
<http://cosmosdb.com/caig/pypi_m26> <http://cosmosdb.com/caig#lic> "mit" .
<http://cosmosdb.com/caig/christopher.joakim@gmail.com> <http://cosmosdb.com/caig#developer_of> <http://cosmosdb.com/caig/pypi_m26> .
<http://cosmosdb.com/caig/christopher_joakim> <http://cosmosdb.com/caig#developer_of> <http://cosmosdb.com/caig/pypi_m26> .
<http://cosmosdb.com/caig/pypi_m26> <http://cosmosdb.com/caig#developed_by> <http://cosmosdb.com/caig/christopher.joakim@gmail.com> .
<http://cosmosdb.com/caig/pypi_m26> <http://cosmosdb.com/caig#ln> "m26" .
<http://cosmosdb.com/caig/pypi_m26> <http://cosmosdb.com/caig#developed_by> <http://cosmosdb.com/caig/christopher_joakim> .
<http://cosmosdb.com/caig/pypi_m26> <http://cosmosdb.com/caig#kwds> "pace_per_mile runwalkcalculator seconds_per_mile agecalculator calculates" .
<http://cosmosdb.com/caig/pypi_m26> <http://cosmosdb.com/caig#lt> "pypi" .
```

[See Wikipedia for more information on Semantic Triples](https://en.wikipedia.org/wiki/Semantic_triple)

---

<a name="omnirag_sources"></a>

**Q: Can I add additional data sources with the OmniRAG pattern, and how?**

**A:** Yes.  You are free to customize the code per your needs.

We recommend sourcing the in-memory graph from Cosmos DB, but you 
are free to use other sources.

Class StrategyBuilder determines the "strategy" to use regarding
where to search for the appropriate RAG data given a user utterance.
This logic, as well as the corresponding LLM prompt, will need
to be modified.

---

<a name="d3"></a>

**Q: Do I have to use D3.js for web page graph visualizations?**

**A:** No.  You are free to use your preferred JavaScript visualization
library.  We chose D3.js because it is free, widely used, and is
generally of high quality.

---

<a name="binary_objects"></a>

**Q: Should I store PDFs, images, and movies in Cosmos DB?**

**A:** No.  Use Cosmos DB to store your documents as JSON objects.
Typical document size is 1-100kb, though larger documents are supported.
The word "document" is overloaded in IT.  In the context of Cosmos DB,
a "document" means "JSON object".

Binary content such as PDFs, images, and movies should be stored in
Azure Blob Storage or data lake, but their "metadata" (i.e - filename, type, location, description, summary, etc.) can be stored in Cosmos DB
as JSON objects.

---

<a name="how_to_populate_cosmos"></a>

**Q: How should I load my data into Cosmos DB?**

**A:** There are many ways to do this, including:

- Azure Data Factory
- Spark (in Azure Synapse or Microsoft Fabric) with Cosmos DB connector library
- Programming language SDK
- The Java and C# APIs for the Cosmos DB NoSQL API offer excellent "bulk loading" functionality.

---

<a name="bicep_param_names"></a>

**Q: I don't understand the Bicep parameter names, can you explain?**

**A:** The bicep parameter names are camel-cased versions of the environment variable names that are described in class ConfigService.  For example, the bicep name "graphSourceDb" maps to environment variable "CAIG_GRAPH_SOURCE_DB".

Please see main_common.py which implements the following command-line
functions which you can use to generate Bicep and Compose file
fragments from the list of your defined environment variables
in class ConfigService.

```
    python main_common.py gen_ps1_env_var_script
    python main_common.py gen_bicep_file_fragments
    python main_common.py gen_environment_variables_md
    python main_common.py gen_all
```

<!--copy-and-paste Q/A template

---

<a name="fragment_name"></a>

**Q:**

**A:**

-->

