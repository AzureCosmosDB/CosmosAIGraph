package com.microsoft.cosmosdb.caig.util;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Scanner;

/**
 * Instances of this class are used to perform all local disk IO for this application.
 *
 * Chris Joakim, Microsoft, 2025
 */

public class FileUtil {

    private static Logger logger = LogManager.getLogger(FileUtil.class);


    public FileUtil() {

        super();
    }

    public String readUnicode(String filename) {

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
            e.printStackTrace();
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