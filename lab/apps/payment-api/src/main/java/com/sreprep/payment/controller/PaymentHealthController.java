package com.sreprep.payment.controller;

import org.springframework.boot.actuate.health.HealthComponent;
import org.springframework.boot.actuate.health.HealthEndpoint;
import org.springframework.boot.actuate.health.Status;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * Condition 1 Endpoint:
 * Serves synthetic health monitoring on port 8080 under Spring Security authentication.
 * Delegates in-process to Actuator's HealthEndpoint.
 */
@RestController
@RequestMapping("/payment/api/v1")
public class PaymentHealthController {

    private final HealthEndpoint healthEndpoint;

    public PaymentHealthController(HealthEndpoint healthEndpoint) {
        this.healthEndpoint = healthEndpoint;
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> getHealth() {
        HealthComponent health = healthEndpoint.health();
        boolean isUp = Status.UP.equals(health.getStatus());

        Map<String, Object> response = Map.of(
            "status", health.getStatus().getCode(),
            "service", "payment-api",
            "port", 8080
        );

        return ResponseEntity
            .status(isUp ? HttpStatus.OK : HttpStatus.SERVICE_UNAVAILABLE)
            .body(response);
    }
}
