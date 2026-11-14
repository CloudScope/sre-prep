package com.sreprep.payment.health;

import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.boot.web.embedded.tomcat.TomcatWebServer;
import org.springframework.boot.web.servlet.context.ServletWebServerApplicationContext;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Component;

/**
 * HealthIndicator to guard against the "False-Green" trap:
 * If port 8080's Tomcat connector crashes or halts, this reports DOWN so that
 * /actuator/health on 8081 will not report a false positive.
 *
 * Injects ApplicationContext to remain completely safe in both embedded server
 * runtime environments and unit test environments (MOCK).
 */
@Component
public class MainServerHealthIndicator implements HealthIndicator {

    private final ApplicationContext applicationContext;

    public MainServerHealthIndicator(ApplicationContext applicationContext) {
        this.applicationContext = applicationContext;
    }

    @Override
    public Health health() {
        if (applicationContext instanceof ServletWebServerApplicationContext webServerAppCtx) {
            try {
                if (webServerAppCtx.getWebServer() instanceof TomcatWebServer tomcatServer) {
                    org.apache.catalina.connector.Connector connector = tomcatServer.getTomcat().getConnector();
                    if (connector == null || !connector.getState().isAvailable()) {
                        return Health.down()
                            .withDetail("mainServerPort8080", "CONNECTOR_UNAVAILABLE")
                            .build();
                    }
                }
            } catch (Exception e) {
                return Health.down().withException(e).build();
            }
        }
        return Health.up()
            .withDetail("mainServerPort8080", "RUNNING")
            .build();
    }
}
