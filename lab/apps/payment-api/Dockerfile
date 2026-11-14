# Multi-stage Dockerfile for payment-api (Spring Boot 3.4.2 / Java 21)

# Build stage
FROM maven:3.9.9-eclipse-temurin-21-alpine AS build
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src ./src
RUN mvn package -DskipTests -B

# Runtime stage
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

# Explicitly create UID/GID 1000 to match Kubernetes runAsUser: 1000
RUN addgroup -g 1000 -S appgroup && adduser -u 1000 -S appuser -G appgroup

COPY --from=build /app/target/payment-api-0.1.0.jar app.jar
RUN chmod 755 /app && chmod 644 /app/app.jar && chown -R appuser:appgroup /app

USER 1000:1000

EXPOSE 8080

ENTRYPOINT ["java", "-Djava.net.preferIPv4Stack=true", "-XX:+UseContainerSupport", "-XX:MaxRAMPercentage=75.0", "-jar", "app.jar"]
