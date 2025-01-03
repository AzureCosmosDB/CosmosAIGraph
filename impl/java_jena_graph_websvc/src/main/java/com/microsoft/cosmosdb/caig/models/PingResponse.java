package com.microsoft.cosmosdb.caig.models;

import com.microsoft.cosmosdb.caig.util.AppConfig;
import lombok.Data;

/**
 * The WebApp returns an instance of this JSON-serialized class in response to
 * a HTTP request to the / endpoint.  It returns various data elements regarding
 * current time, uptime, JVM memory usage, and process ID.
 *
 * Chris Joakim, Microsoft, 2025
 */

@Data
public class PingResponse {

    public static final long MS_PER_SECOND = 1000;
    public static final long MS_PER_MINUTE = MS_PER_SECOND * 60;
    public static final long MS_PER_HOUR = MS_PER_MINUTE * 60;
    public static final long MS_PER_DAY = MS_PER_HOUR * 24;

    public long appStartupEpoch = AppConfig.getInitialzedEpoch();
    public long currentEpoch = System.currentTimeMillis();
    public long uptimeMillis = currentEpoch - appStartupEpoch;
    public double uptimeHours = (double) uptimeMillis / (double) MS_PER_HOUR;
    public double uptimeDays = (double) uptimeMillis / (double) MS_PER_DAY;

    public float totalMemory = Runtime.getRuntime().totalMemory();
    public float freeMemory = Runtime.getRuntime().freeMemory();
    public float maxMemory = Runtime.getRuntime().maxMemory();

    long processId = ProcessHandle.current().pid();
    boolean processAlive = ProcessHandle.current().isAlive();
}