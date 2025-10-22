package com.microsoft.cosmosdb.caig.util;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Scanner;

/**
 * Instances of this class are used to perform all local disk IO and HTTP-based
 * resource loading for this application.
 *
 * Chris Joakim, Microsoft, 2025
 */

public class FileUtil {

    private static Logger logger = LoggerFactory.getLogger(FileUtil.class);


    public FileUtil() {

        super();
    }

    /**
     * Read content from either a local file path or an HTTPS URL.
     * This method supports both development (local files) and production (blob storage) scenarios.
     */
    public String readUnicode(String pathOrUrl) {

        if (pathOrUrl == null || pathOrUrl.trim().isEmpty()) {
            logger.error("readUnicode: pathOrUrl is null or empty");
            return null;
        }

        // Check if this is an HTTP/HTTPS URL
        if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) {
            return readFromUrl(pathOrUrl);
        } else {
            return readFromFile(pathOrUrl);
        }
    }

    /**
     * Read content from a local file path.
     */
    private String readFromFile(String filename) {
        Path path = Paths.get(filename);
        StringBuffer sb = new StringBuffer();

        // Java 8, default UTF-8
        try (BufferedReader reader = Files.newBufferedReader(path)) {
            String str;
            while ((str = reader.readLine()) != null) {
                sb.append(str);
                sb.append("\n");
            }
        } catch (IOException e) {
            logger.error("Error reading file: " + filename, e);
        }
        return sb.toString();
    }

    /**
     * Read content from an HTTP/HTTPS URL (e.g., Azure Blob Storage).
     */
    private String readFromUrl(String urlString) {
        StringBuffer sb = new StringBuffer();
        HttpURLConnection connection = null;

        try {
            logger.warn("readFromUrl: fetching " + urlString);
            URL url = new URL(urlString);
            connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("GET");
            connection.setConnectTimeout(30000); // 30 seconds
            connection.setReadTimeout(60000);    // 60 seconds

            int responseCode = connection.getResponseCode();
            if (responseCode == HttpURLConnection.HTTP_OK) {
                try (BufferedReader reader = new BufferedReader(
                        new InputStreamReader(connection.getInputStream(), "UTF-8"))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        sb.append(line);
                        sb.append("\n");
                    }
                }
                logger.warn("readFromUrl: successfully fetched " + sb.length() + " characters");
            } else {
                logger.error("readFromUrl: HTTP error " + responseCode + " for " + urlString);
            }
        } catch (Exception e) {
            logger.error("Error reading from URL: " + urlString, e);
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
        return sb.toString();
    }

    public List<String> readLines(String infile) throws IOException {

        List<String> lines = new ArrayList<String>();
        File file = new File(infile);
        Scanner sc = new Scanner(file);
        while (sc.hasNextLine()) {
            lines.add(sc.nextLine().trim());
        }
        return lines;
    }

    public Map<String, Object> readJsonMap(String infile) throws Exception {

        ObjectMapper mapper = new ObjectMapper();
        return mapper.readValue(Paths.get(infile).toFile(), Map.class);
    }

    public ArrayList<Map<String, Object>> readJsonMapArray(String infile) throws Exception {

        ObjectMapper mapper = new ObjectMapper();
        return mapper.readValue(Paths.get(infile).toFile(), ArrayList.class);
    }

    public void writeJson(Object obj, String outfile, boolean pretty, boolean verbose) throws Exception {

        ObjectMapper mapper = new ObjectMapper();
        String json = null;
        if (pretty) {
            json = mapper.writerWithDefaultPrettyPrinter().writeValueAsString(obj);
            String utf8Str = new String(json.getBytes("UTF8"));
            writeTextFile(outfile, utf8Str, verbose);
        } else {
            json = mapper.writeValueAsString(obj);
            String utf8Str = new String(json.getBytes("UTF8"));
            writeTextFile(outfile, utf8Str, verbose);
            if (verbose) {
                logger.warn("file written: " + outfile);
            }
        }
    }

    public void writeTextFile(String outfile, String text, boolean verbose) throws Exception {

        FileWriter fw = null;
        try {
            fw = new FileWriter(outfile);
            fw.write(text);
            if (verbose) {
                logger.warn("file written: " + outfile);
            }
        } catch (IOException e) {
            e.printStackTrace();
            throw e;
        } finally {
            if (fw != null) {
                fw.close();
            }
        }
    }

    public void writeLines(String outfile, ArrayList<String> lines, boolean verbose) throws Exception {

        FileWriter fw = null;
        try {
            fw = new FileWriter(outfile);
            for (int i = 0; i < lines.size(); i++) {
                fw.write(lines.get(i));
                fw.write(System.lineSeparator());
            }

            if (verbose) {
                logger.warn("file written: " + outfile);
            }
        } catch (IOException e) {
            e.printStackTrace();
            throw e;
        } finally {
            if (fw != null) {
                fw.close();
            }
        }
    }

    public String baseName(File f) {

        return f.getName();
    }

    public String baseNameNoSuffix(File f) {

        return baseName(f).split("\\.")[0];
    }

    public String immediateParentDir(File f) {

        return new File(f.getParent()).getName().toString();
    }
}