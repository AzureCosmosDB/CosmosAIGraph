# CosmosAIGraph

**AI-Powered Graph and RAG implementation of OmniRAG pattern, utilizing Azure Cosmos DB and other sources**

- [Presentations](presentations/)
- [Reference Application Documentation](docs/readme.md)
- [Frequently Asked Questions (FAQ)](docs/faq.md)
- [Reference Dataset of Python libraries, pre-vectorized](data/pypi/wrangled_libs)

<pre>

</pre>

<p align="center">
  <img src="docs/img/deployment-architecture.png" width="100%">
</p>

---

## Change Log

- March 2025
  - Version 3.0 codebase
  - Now focused on Azure Cosmos DB for NoSQL
    - Eliminated vCore support
  - Now focused on Apache Jena implementation (Java) for the in-memory RDF graph
    - Eliminated rdflib support
  - New DockerHub images created
  - Presentations updated - see the v3 files
  - Docs are being updated, target completion date 3/31/2025

- January 2025
  - Added the **Java and Apache Jena** implementation of the in-memory graph
  - See https://jena.apache.org/index.html

- September 2024
  - Added support for the **Azure Cosmos DB for NoSQL** in addition to Azure Cosmos DB for MongoDB vCore

## Roadmap

- Add RBAC and Microsoft Entra ID/AAD authentication support for the **Azure Cosmos DB for NoSQL**
- Update AI model to gpt-4.5
- Generic graph examples with graph generation solution

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services.
Authorized use of Microsoft  trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must
not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
