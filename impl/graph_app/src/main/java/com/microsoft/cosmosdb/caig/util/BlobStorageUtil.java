package com.microsoft.cosmosdb.caig.util;

import com.azure.storage.blob.BlobClient;
import com.azure.storage.blob.BlobContainerClient;
import com.azure.storage.blob.BlobServiceClient;
import com.azure.storage.blob.BlobServiceClientBuilder;
import com.azure.storage.blob.models.BlobItem;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.ByteArrayOutputStream;
import java.util.ArrayList;
import java.util.List;

/**
 * Utility class for interacting with Azure Blob Storage.
 * Supports listing blobs in a container with a given prefix (virtual directory).
 *
 * Chris Joakim, Microsoft, 2025
 */
public class BlobStorageUtil {

    private static Logger logger = LoggerFactory.getLogger(BlobStorageUtil.class);

    /**
     * Parse a blob storage URL and extract container name and blob prefix.
     * Example: https://account.blob.core.windows.net/container/path/to/
     * Returns: [containerName, blobPrefix]
     */
    public static String[] parseBlobUrl(String blobUrl) {
        try {
            // Remove protocol
            String urlWithoutProtocol = blobUrl.replaceFirst("^https?://", "");
            
            // Split by first slash to separate account from path
            int firstSlash = urlWithoutProtocol.indexOf('/');
            if (firstSlash == -1) {
                logger.error("Invalid blob URL format: " + blobUrl);
                return null;
            }
            
            String pathPart = urlWithoutProtocol.substring(firstSlash + 1);
            
            // Split path into container and blob prefix
            int secondSlash = pathPart.indexOf('/');
            if (secondSlash == -1) {
                // Just a container, no prefix
                return new String[]{pathPart, ""};
            }
            
            String containerName = pathPart.substring(0, secondSlash);
            String blobPrefix = pathPart.substring(secondSlash + 1);
            
            return new String[]{containerName, blobPrefix};
        } catch (Exception e) {
            logger.error("Error parsing blob URL: " + blobUrl, e);
            return null;
        }
    }

    /**
     * Extract the storage account URL from a blob URL.
     * Example: https://account.blob.core.windows.net/container/path
     * Returns: https://account.blob.core.windows.net
     */
    public static String getStorageAccountUrl(String blobUrl) {
        try {
            if (blobUrl.startsWith("http://")) {
                int thirdSlash = blobUrl.indexOf('/', 7);
                return thirdSlash > 0 ? blobUrl.substring(0, thirdSlash) : blobUrl;
            } else if (blobUrl.startsWith("https://")) {
                int thirdSlash = blobUrl.indexOf('/', 8);
                return thirdSlash > 0 ? blobUrl.substring(0, thirdSlash) : blobUrl;
            }
            return null;
        } catch (Exception e) {
            logger.error("Error extracting storage account URL: " + blobUrl, e);
            return null;
        }
    }

    /**
     * List all blob URLs in a container with a given prefix (virtual directory).
     * Filters for RDF file extensions: .ttl, .nt, .rdf, .owl
     * 
     * @param blobDirectoryUrl The base URL representing a "directory" in blob storage
     * @return List of full blob URLs
     */
    public static List<String> listBlobsInDirectory(String blobDirectoryUrl) {
        List<String> blobUrls = new ArrayList<>();
        
        try {
            logger.warn("Listing blobs in directory: " + blobDirectoryUrl);
            
            String[] parsed = parseBlobUrl(blobDirectoryUrl);
            if (parsed == null) {
                logger.error("Failed to parse blob URL");
                return blobUrls;
            }
            
            String containerName = parsed[0];
            String blobPrefix = parsed[1];
            String accountUrl = getStorageAccountUrl(blobDirectoryUrl);
            
            logger.warn("Storage account URL: " + accountUrl);
            logger.warn("Container: " + containerName);
            logger.warn("Blob prefix: " + blobPrefix);
            
            // Create blob service client (anonymous access for public containers)
            BlobServiceClient blobServiceClient = new BlobServiceClientBuilder()
                .endpoint(accountUrl)
                .buildClient();
            
            BlobContainerClient containerClient = blobServiceClient.getBlobContainerClient(containerName);
            
            // List blobs with the given prefix
            for (BlobItem blobItem : containerClient.listBlobsByHierarchy(blobPrefix)) {
                String blobName = blobItem.getName();
                
                // Filter for RDF file extensions
                if (blobName.endsWith(".ttl") || blobName.endsWith(".nt") || 
                    blobName.endsWith(".rdf") || blobName.endsWith(".owl")) {
                    
                    String blobUrl = String.format("%s/%s/%s", accountUrl, containerName, blobName);
                    blobUrls.add(blobUrl);
                    logger.warn("Found RDF blob: " + blobName);
                }
            }
            
            logger.warn("Found " + blobUrls.size() + " RDF blobs in directory");
            
        } catch (Exception e) {
            logger.error("Error listing blobs in directory: " + blobDirectoryUrl, e);
        }
        
        return blobUrls;
    }

    /**
     * Check if a URL appears to be a blob directory URL (ends with /)
     * or a single blob file URL.
     */
    public static boolean isBlobDirectoryUrl(String url) {
        if (url == null || url.isEmpty()) {
            return false;
        }
        
        // If it ends with a slash, treat it as a directory
        if (url.endsWith("/")) {
            return true;
        }
        
        // If it doesn't have a file extension, treat it as a directory
        String lastSegment = url.substring(url.lastIndexOf('/') + 1);
        return !lastSegment.contains(".");
    }
}
