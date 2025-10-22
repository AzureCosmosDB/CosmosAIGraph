import logging
from typing import List
from urllib.parse import urlparse
import httpx
from xml.etree import ElementTree as ET

# Utility module for interacting with Azure Blob Storage
# Supports listing blobs in a container with a given prefix (virtual directory)
#
# Chris Joakim, Microsoft, 2025


class BlobStorageUtil:
    """Utility class for Azure Blob Storage operations"""

    @classmethod
    def parse_blob_url(cls, blob_url: str) -> tuple[str, str, str] | None:
        """
        Parse a blob storage URL and extract account URL, container name, and blob prefix.
        Example: https://account.blob.core.windows.net/container/path/to/
        Returns: (account_url, container_name, blob_prefix) or None
        """
        try:
            parsed = urlparse(blob_url)
            if not parsed.scheme or not parsed.netloc:
                return None

            # Account URL is scheme + netloc
            account_url = f"{parsed.scheme}://{parsed.netloc}"

            # Path starts with / and contains container/blob/prefix
            path = parsed.path.lstrip("/")
            if not path:
                return None

            parts = path.split("/", 1)
            container_name = parts[0]
            blob_prefix = parts[1] if len(parts) > 1 else ""

            return (account_url, container_name, blob_prefix)
        except Exception as e:
            logging.error(f"Error parsing blob URL {blob_url}: {str(e)}")
            return None

    @classmethod
    def is_blob_directory_url(cls, url: str) -> bool:
        """
        Check if a URL appears to be a blob directory URL (ends with /)
        or a single blob file URL.
        """
        if not url:
            return False

        # If it ends with a slash, treat it as a directory
        if url.endswith("/"):
            return True

        # If it doesn't have a file extension in the last segment, treat it as a directory
        last_segment = url.split("/")[-1]
        return "." not in last_segment

    @classmethod
    def list_blobs_in_directory(cls, blob_directory_url: str) -> List[str]:
        """
        List all blob URLs in a container with a given prefix (virtual directory).
        Filters for RDF file extensions: .ttl, .nt, .rdf, .owl

        Args:
            blob_directory_url: The base URL representing a "directory" in blob storage

        Returns:
            List of full blob URLs
        """
        blob_urls = []

        try:
            logging.warning(f"BlobStorageUtil: Listing blobs in directory: {blob_directory_url}")

            parsed = cls.parse_blob_url(blob_directory_url)
            if not parsed:
                logging.error("BlobStorageUtil: Failed to parse blob URL")
                return blob_urls

            account_url, container_name, blob_prefix = parsed

            logging.warning(f"BlobStorageUtil: Account URL: {account_url}")
            logging.warning(f"BlobStorageUtil: Container: {container_name}")
            logging.warning(f"BlobStorageUtil: Blob prefix: {blob_prefix}")

            # Use Azure Blob Storage REST API to list blobs
            # https://docs.microsoft.com/en-us/rest/api/storageservices/list-blobs
            list_url = f"{account_url}/{container_name}?restype=container&comp=list"
            if blob_prefix:
                list_url += f"&prefix={blob_prefix}"

            logging.warning(f"BlobStorageUtil: Fetching blob list from: {list_url}")

            with httpx.Client(timeout=60.0) as client:
                response = client.get(list_url)
                response.raise_for_status()

                # Parse XML response
                root = ET.fromstring(response.content)

                # Find all blob names in the XML
                # XML structure: <EnumerationResults><Blobs><Blob><Name>...</Name></Blob></Blobs></EnumerationResults>
                namespaces = {"": "http://schemas.microsoft.com/2003/10/Serialization/"}
                
                # Try with and without namespace
                blobs = root.findall(".//Blob/Name") or root.findall(".//{http://schemas.microsoft.com/2003/10/Serialization/}Blob/{http://schemas.microsoft.com/2003/10/Serialization/}Name")
                
                if not blobs:
                    # Try alternative structure
                    blobs = root.findall(".//Name")

                for blob_elem in blobs:
                    blob_name = blob_elem.text
                    if not blob_name:
                        continue

                    # Filter for RDF file extensions
                    if blob_name.endswith((".ttl", ".nt", ".rdf", ".owl")):
                        blob_url = f"{account_url}/{container_name}/{blob_name}"
                        blob_urls.append(blob_url)
                        logging.warning(f"BlobStorageUtil: Found RDF blob: {blob_name}")

                logging.warning(
                    f"BlobStorageUtil: Found {len(blob_urls)} RDF blobs in directory"
                )

        except httpx.HTTPError as e:
            logging.error(
                f"BlobStorageUtil: HTTP error listing blobs in directory {blob_directory_url}: {str(e)}"
            )
        except Exception as e:
            logging.error(
                f"BlobStorageUtil: Error listing blobs in directory {blob_directory_url}: {str(e)}"
            )
            logging.exception(e, stack_info=True, exc_info=True)

        return blob_urls
