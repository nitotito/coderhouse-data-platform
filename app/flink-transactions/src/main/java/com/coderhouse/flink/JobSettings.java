package com.coderhouse.flink;

import com.amazonaws.services.kinesisanalytics.runtime.KinesisAnalyticsRuntime;
import java.util.Properties;

final class JobSettings {
    private JobSettings() {}

    static Properties load() throws Exception {
        Properties settings = new Properties();
        // Local runs provide environment variables; Managed Flink provides runtime properties.
        if (System.getenv("KINESIS_STREAM_ARN") == null) {
            Properties managed = KinesisAnalyticsRuntime.getApplicationProperties()
                    .get("ApplicationProperties");
            if (managed != null) settings.putAll(managed);
        }
        for (String key : new String[]{"KINESIS_STREAM_ARN", "ICEBERG_WAREHOUSE",
                "ICEBERG_DATABASE", "ICEBERG_TABLE", "AWS_REGION"}) {
            String value = System.getenv(key);
            if (value != null && !value.isBlank()) settings.setProperty(key, value);
        }
        return settings;
    }

    static String require(Properties settings, String key) {
        String value = settings.getProperty(key);
        if (value == null || value.isBlank()) throw new IllegalArgumentException("Falta " + key);
        return value;
    }
}
