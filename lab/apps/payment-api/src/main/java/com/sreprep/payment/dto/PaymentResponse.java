package com.sreprep.payment.dto;

import java.math.BigDecimal;
import java.time.Instant;

public record PaymentResponse(
    String transactionId,
    String orderId,
    BigDecimal amount,
    String currency,
    String status,
    Instant timestamp
) {}
