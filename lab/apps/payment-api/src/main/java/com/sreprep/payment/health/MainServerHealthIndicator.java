package com.sreprep.payment.health;

import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.boot.web.embedded.tomcat.TomcatWebServer;
import org.springframework.boot.web.servlet.context.ServletWebServerApplicationContext;
import org.springframework.stereotype.Component;

/**
 * HealthIndicator to guard against the "False-Green" trap:
 * If port 8080's Tomcat connector crashes or halts, this reports DOWN so that
 * /actuator/health on 8081 will not report a false positive.
 */
@Component
public class MainServerHealthIndicator implements HealthIndicator {

    private final ServletWebServerApplicationContext context;

    public MainServerHealthIndicator(ServletWebServerApplicationContext context) {
        this.context = context;
    }

    @Override
    public Health health() {
        if (context.getWebServer() instanceof TomcatWebServer tomcatServer) {
            org.apache.catalina.connector.Connector connector = tomcatServer.getTomcat().getConnector();
            if (connector == null || !connector.getState().isAvailable()) {
                return Health.down()
                    .withDetail("mainServerPort8080", "CONNECTOR_UNAVAILABLE")
                    .build();
            }
        }
        return Health.up()
            .withDetail("mainServerPort8080", "RUNNING")
            .build();
    }
}
