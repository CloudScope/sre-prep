package com.sreprep.payment.config;

import org.springframework.boot.actuate.autoconfigure.security.servlet.EndpointRequest;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.annotation.Order;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    /**
     * Filter chain 1: Management / Actuator endpoints (Port 8081).
     * Bounded strictly to loopback (127.0.0.1) for local Kubelet probes and OTel sidecar.
     */
    @Bean
    @Order(1)
    public SecurityFilterChain actuatorSecurityFilterChain(HttpSecurity http) throws Exception {
        http
            .securityMatcher(EndpointRequest.toAnyEndpoint())
            .authorizeHttpRequests(auth -> auth
                .requestMatchers(EndpointRequest.to("health", "info", "prometheus")).permitAll()
                .anyRequest().denyAll()
            )
            .csrf(AbstractHttpConfigurer::disable);
        return http.build();
    }

    /**
     * Filter chain 2: Application endpoints (Port 8080).
     * Strictly requires authentication for ALL callers (/**).
     */
    @Bean
    @Order(2)
    public SecurityFilterChain applicationSecurityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(AbstractHttpConfigurer::disable)
            .authorizeHttpRequests(auth -> auth
                // Dedicated synthetic endpoint on 8080 requires authenticated synthetic caller
                .requestMatchers("/payment/api/v1/health").hasRole("SYNTHETIC_PROBER")
                // All other application requests (/**) require authentication
                .anyRequest().authenticated()
            )
            .httpBasic(Customizer.withDefaults());
        return http.build();
    }
}
