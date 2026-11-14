package com.sreprep.payment.controller;

import com.sreprep.payment.dto.PaymentRequest;
import com.sreprep.payment.dto.PaymentResponse;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;

@RestController
@RequestMapping("/payment/api/v1")
public class PaymentController {

    private static final Logger log = LoggerFactory.getLogger(PaymentController.class);

    private final Counter paymentsSuccess;
    private final Counter paymentsFailure;

    public PaymentController(MeterRegistry meterRegistry) {
        this.paymentsSuccess = Counter.builder("payment.processed")
            .description("Payments processed by outcome")
            .tag("outcome", "success")
            .register(meterRegistry);

        this.paymentsFailure = Counter.builder("payment.processed")
            .description("Payments processed by outcome")
            .tag("outcome", "failure")
            .register(meterRegistry);
    }

    @PostMapping("/process")
    public ResponseEntity<PaymentResponse> processPayment(@Valid @RequestBody PaymentRequest request) {
        log.info("Processing payment for orderId: {}, amount: {} {}",
            request.orderId(), request.amount(), request.currency());

        // Failure injection knobs (read dynamically from environment for chaos testing)
        double errorRate = getDoubleEnv("ERROR_RATE", 0.0);
        long extraLatencyMs = getLongEnv("EXTRA_LATENCY_MS", 0);

        if (extraLatencyMs > 0) {
            try {
                Thread.sleep(extraLatencyMs);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }

        if (errorRate > 0 && ThreadLocalRandom.current().nextDouble() < errorRate) {
            paymentsFailure.increment();
            log.warn("Chaos injected: payment failure for orderId: {}", request.orderId());
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Simulated payment gateway failure");
        }

        paymentsSuccess.increment();

        PaymentResponse response = new PaymentResponse(
            "txn-" + UUID.randomUUID().toString().substring(0, 8),
            request.orderId(),
            request.amount(),
            request.currency(),
            "COMPLETED",
            Instant.now()
        );

        return ResponseEntity.ok(response);
    }

    private double getDoubleEnv(String name, double defaultValue) {
        String val = System.getenv(name);
        if (val == null || val.isBlank()) return defaultValue;
        try {
            return Double.parseDouble(val);
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }

    private long getLongEnv(String name, long defaultValue) {
        String val = System.getenv(name);
        if (val == null || val.isBlank()) return defaultValue;
        try {
            return Long.parseLong(val);
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }
}
